import os
import json
import threading
import time
import pandas as pd
import numpy as np
import torch
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import TrainingModel
from .serializers import TrainingModelSerializer
import sys
import pathlib

# Ensure the parent directory of 'backend' is in sys.path so 'import backend.algorithm...' works
# settings.BASE_DIR is usually '.../TS-Studio/backend'
# We want to add '.../TS-Studio'
BACKEND_DIR = pathlib.Path(settings.BASE_DIR)
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT)) # Insert at beginning to ensure priority

# Also keep algorithm in path just in case some local imports need it
ALGORITHM_PATH = os.path.join(settings.BASE_DIR, 'algorithm')
if ALGORITHM_PATH not in sys.path:
    sys.path.append(ALGORITHM_PATH)

import_error_message = None
try:
    # Try importing using the package structure the code expects (backend.algorithm...)
    from backend.algorithm.exp.exp_main import Exp_Main
except ImportError as e1:
    try:
        # Fallback: try direct import if backend prefix is stripped in some envs
        from algorithm.exp.exp_main import Exp_Main
    except ImportError as e2:
        Exp_Main = None
        import_error_message = f"Failed to import from both 'backend.algorithm' ({e1}) and 'algorithm' ({e2})"
        print(f"Warning: Could not import Exp_Main. Details: {import_error_message}")
        traceback.print_exc()

class ConfigView(APIView):
    def get(self, request):
        config_path = os.path.join(ALGORITHM_PATH, 'config', 'config_FEA.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return Response(config)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        # In a real app, validation is needed
        config = request.data
        return Response({'status': 'Config received (not saved to file to avoid corruption)'})

class FileUploadView(APIView):
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if this is just a preview request
        is_preview = request.query_params.get('preview') == 'true'
        
        if is_preview:
            try:
                # Read directly from memory/temp file for preview
                # Make sure to handle multiple reads or seek if necessary, 
                # though here we strictly do one read per request.
                if file_obj.name.endswith('.csv'):
                    df = pd.read_csv(file_obj)
                else:
                    df = pd.read_excel(file_obj)
                
                # Replace NaN with None (null in JSON) to avoid JSON serialization errors
                df = df.replace({np.nan: None})
                
                preview = df.head(5).to_dict(orient='records')
                columns = list(df.columns)
                return Response({
                    'status': 'success', 
                    'filename': file_obj.name, 
                    'columns': columns, 
                    'preview': preview,
                    'mode': 'preview'
                })
            except Exception as e:
                return Response({'status': 'error', 'error': f"Failed to preview: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Save to 'data' directory in backend root
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        save_path = os.path.join(data_dir, file_obj.name)
        with open(save_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        # Read preview
        try:
            df = pd.read_csv(save_path) if save_path.endswith('.csv') else pd.read_excel(save_path)
            # Replace NaN with None
            df = df.replace({np.nan: None})
            
            preview = df.head(5).to_dict(orient='records')
            columns = list(df.columns)
            return Response({
                'status': 'success', 
                'filename': file_obj.name, 
                'columns': columns, 
                'preview': preview,
                'mode': 'saved'
            })
        except Exception as e:
            return Response({'status': 'saved but could not read', 'error': str(e)})

class DatasetListView(APIView):
    def get(self, request):
        # Ensure BASE_DIR is a string
        base_dir = str(settings.BASE_DIR)
        data_dir = os.path.join(base_dir, 'data')
        
        print(f"DatasetListView: Searching in {data_dir}")
        
        if not os.path.exists(data_dir):
            print(f"DatasetListView: Data dir does not exist")
            # Try creating it to see if that helps for future
            try:
                os.makedirs(data_dir)
            except:
                pass
            return Response([])
        
        # Case insensitive check for extensions
        files = [f for f in os.listdir(data_dir) if f.lower().endswith(('.csv', '.xlsx'))]
        print(f"DatasetListView: Found files: {files}")
        return Response(files)

class DatasetInfoView(APIView):
    def get(self, request):
        filename = request.query_params.get('filename')
        if not filename:
             return Response({'error': 'Filename required'}, status=status.HTTP_400_BAD_REQUEST)
             
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
             return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
             
        try:
            df = pd.read_csv(file_path) if filename.endswith('.csv') else pd.read_excel(file_path)
            # Replace NaN with None
            df = df.replace({np.nan: None})
            
            preview = df.head(5).to_dict(orient='records')
            columns = list(df.columns)
            return Response({
                'filename': filename,
                'columns': columns,
                'preview': preview
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Args:
    pass

def run_training_task(training_job_id, config_data):
    try:
        job = TrainingModel.objects.get(id=training_job_id)
        job.status = 'running'
        job.save()

        # Construct Args object from config_data
        args = Args()
        # Defaults matching main_ddpm.py
        args.ii = 0
        args.use_window_normalization = True
        args.stage_mode = "TWO"
        args.is_training = 1
        args.out_figures = 1
        args.vis_ar_part = 0
        args.vis_MTS_analysis = 1
        args.model = 'DDPM'
        args.train_epochs = 30
        args.pretrain_epochs = 5
        args.sample_times = 1
        args.beta_dist_alpha = -1
        args.our_ddpm_clip = 100
        args.seq_len = 192
        args.label_len = 7
        args.pred_len = 14
        args.dataset_name = 'Exchange'
        args.weather_type = 'mintemp'
        args.features = 'M'
        args.target = 'OT'
        args.num_vars = 8
        args.checkpoints = './checkpoints/'
        args.freq = 'h'
        args.interval = 1000
        args.ot_ode = True
        args.beta_max = 0.3
        args.t0 = 1e-4
        args.T = 1.
        args.model_channels = 256
        args.nfe = 100
        args.dim_LSTM = 64
        args.diff_steps = 100
        args.UNet_Type = 'CNN'
        args.D3PM_kernel_size = 5
        args.use_freq_enhance = 0
        args.type_sampler = 'none'
        args.parameterization = 'x_start'
        args.ddpm_inp_embed = 256
        args.ddpm_dim_diff_steps = 256
        args.ddpm_channels_conv = 256
        args.ddpm_channels_fusion_I = 256
        args.ddpm_layers_inp = 5
        args.ddpm_layers_I = 5
        args.ddpm_layers_II = 5
        args.cond_ddpm_num_layers = 5
        args.cond_ddpm_channels_conv = 64
        args.ablation_study_case = "none"
        args.weight_pred_loss = 0.0
        args.ablation_study_F_type = "CNN"
        args.ablation_study_masking_type = "none"
        args.ablation_study_masking_tau = 0.9
        args.learning_rate = 0.0006
        args.embed = 'timeF'
        args.use_gpu = True
        args.gpu = 0
        args.use_multi_gpu = False
        args.devices = '0,1,2,3'
        args.seed = 2024
        # num_workers=0 ensures data loading happens in the main process
        # This prevents 'Apps not loaded' errors on Windows caused by multiprocessing importing Django models
        args.num_workers = 0 
        args.itr = 10
        args.batch_size = 64
        args.test_batch_size = 64
        args.use_valset = True  # Default to using validation set
        args.use_amp = False  # Automatic Mixed Precision
        
        # Path configuration
        args.root_path = os.path.join(settings.BASE_DIR, 'data') # Point to uploaded files directory
        args.data_path = config_data.get('filename', 'Exchange.csv') # Default file
        args.data = config_data.get('dataset_type', 'custom') # Default type

        # Override with user config
        for k, v in config_data.items():
            setattr(args, k, v)
        
        # 1. Update label_len defaults to pred_len / 2
        args.label_len = int(args.pred_len / 2)

        # 2. Update num_vars from dataset
        try:
             full_data_path = os.path.join(args.root_path, args.data_path)
             if os.path.exists(full_data_path):
                 if full_data_path.endswith('.csv'):
                     df = pd.read_csv(full_data_path)
                 else:
                     df = pd.read_excel(full_data_path)
                 # args.num_vars = cols - 1 (assuming 1 date column)
                 args.num_vars = len(df.columns) - 1
                 print(f"Updated args.num_vars to {args.num_vars} based on dataset columns")
             else:
                 print(f"Warning: Data file not found at {full_data_path}, skipping num_vars update")
        except Exception as e:
            print(f"Error reading dataset for num_vars: {e}")

        # 3. Update config_FEA.json
        try:
            config_fea_path = os.path.join(ALGORITHM_PATH, 'config', 'config_FEA.json')
            if os.path.exists(config_fea_path):
                with open(config_fea_path, 'r') as f:
                    fea_config = json.load(f)
                
                if 'FEA_config' in fea_config:
                    c = fea_config['FEA_config']
                    c['pred_len'] = args.pred_len
                    c['y_len'] = args.seq_len + args.pred_len
                    c['in_channels'] = args.num_vars
                    c['out_channels'] = args.num_vars
                
                with open(config_fea_path, 'w') as f:
                    json.dump(fea_config, f, indent=4)
                print(f"Updated config_FEA.json with pred_len={args.pred_len}, y_len={args.seq_len + args.pred_len}, channels={args.num_vars}")
        except Exception as e:
            print(f"Error updating config_FEA.json: {e}")
        
        args.use_gpu = True if torch.cuda.is_available() and args.use_gpu else False
        
        # Initialize Exp
        if Exp_Main is None:
            raise ImportError(f"算法模块(Exp_Main)加载失败。具体错误: {import_error_message}。请检查依赖包或路径配置。")

        # Set model_id if not present
        if not hasattr(args, 'model_id'):
            args.model_id = "{}_{}_{}".format(args.dataset_name, args.seq_len, args.pred_len)

        if not hasattr(args, 'tag'):
            args.tag = ''

        # Callback function for monitoring and control
        def training_callback(stage, current_epoch, total_epochs, logs):
            # 1. Update DB with progress
            try:
                # Refresh job to check for status changes (pause/cancel)
                job.refresh_from_db()

                # Handle Pause
                while job.status == 'paused':
                    print(f"Job {job.id} is paused. Waiting...")
                    time.sleep(2)
                    job.refresh_from_db()
                    if job.status == 'cancelled':
                        raise RuntimeError("Training cancelled by user.")

                # Handle Cancellation
                if job.status == 'cancelled':
                     raise RuntimeError("Training cancelled by user.")
                
                # Update metrics
                metrics = job.metrics if job.metrics else {}
                metrics.update({
                    'stage': stage,
                    'current_epoch': current_epoch,
                    'total_epochs': total_epochs,
                    'last_update': time.time()
                })
                
                # If we have logs, we can optionally save them
                # Be careful with JSON serialization of numpy types
                if logs:
                    # quick fix for json serialization if needed, currently Exp_Main stores lists of floats
                    pass

                job.metrics = metrics
                # Don't save 'status' here effectively, just 'metrics' (and implicitly other fields)
                # But we must avoid overwriting 'paused' status if it changed in between refresh and save?
                # Actually job.save() saves all fields.
                # If user sets 'paused' *while* we are processing this line, we might overwrite it with 'running'?
                # No, because we checked job.status != paused.
                # But parallel modification is a risk. `job.save(update_fields=['metrics'])` is safer.
                job.save(update_fields=['metrics'])
                
                print(f"Training Progress: {stage} - Epoch {current_epoch}/{total_epochs}")

            except Exception as e:
                # Propagate cancellation
                if "cancelled" in str(e):
                    raise e
                print(f"Error in training callback: {e}")

        mae_, mse_, rmse_, mape_, mspe_, corr_ = [], [], [], [], [], []

        for ii in range(args.itr):
            setting = '{}_{}_{}_ft{}_sl{}_ll{}_pl{}_dt{}_{}'.format(
                args.model_id,
                args.model,
                args.data,
                args.features,
                args.seq_len,
                args.label_len,
                args.pred_len, 
                ii,
                args.stage_mode)

            if args.tag != '':
                setting += '_' + str(args.tag)

            if args.ablation_study_case != "none":
                setting += '_' + str(args.tag)

            # Pass callback to Exp_Main
            exp = Exp_Main(args, callback=training_callback)

            print(f"Starting training for job {job.id}, iteration {ii+1}/{args.itr}...")
            print('>>>>>>>start pretraining : {}>>>>>>>>>>>>>>>>>>>>>>>>>>'.format(setting))
            
            # Pretraining
            if args.stage_mode == 'TWO':
                if args.model in ["MATS", "MATS2"]:
                    # exp.mats_pretrain(setting)
                    pass
                else:
                    exp.pretrain(setting)

            # Training
            print('>>>>>>>start training : {}>>>>>>>>>>>>>>>>>>>>>>>>>>'.format(setting))
            if args.model == "D3VAE":
                if hasattr(exp, 'D3VAE_train'):
                    exp.D3VAE_train(setting)
                else:
                     exp.train(setting)
            else:
                exp.train(setting)

            # Testing
            print('>>>>>>>testing : {}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'.format(setting))
            mae, mse, rmse, mape, mspe, corr = exp.test(setting, mode="test")
            mae_.append(mae)
            mse_.append(mse)
            rmse_.append(rmse)
            mape_.append(mape)
            mspe_.append(mspe)
            corr_.append(corr)

            torch.cuda.empty_cache()

        # Final logging
        print('Final mean normed: ')
        print('> mae:{:.4f}, std:{:.4f}'.format(np.mean(mae_), np.std(mae_)))
        print('> mse:{:.4f}, std:{:.4f}'.format(np.mean(mse_), np.std(mse_)))
        print('> rmse:{:.4f}, std:{:.4f}'.format(np.mean(rmse_), np.std(rmse_)))
        print('> mape:{:.4f}, std:{:.4f}'.format(np.mean(mape_), np.std(mape_)))
        print('> mspe:{:.4f}, std:{:.4f}'.format(np.mean(mspe_), np.std(mspe_)))
        print('> corr:{:.4f}, std:{:.4f}'.format(np.mean(corr_), np.std(corr_)))
        
        job.status = 'completed'
        job.save()
        
    except Exception as e:
        traceback.print_exc()
        job = TrainingModel.objects.get(id=training_job_id)
        job.status = 'failed'
        job.log = str(e)
        job.save()

class TrainingView(APIView):
    def post(self, request):
        config_data = request.data
        
        # Create Job
        job = TrainingModel.objects.create(
            name=config_data.get('model_name', 'Untitled Model'),
            config=config_data,
            status='pending'
        )
        
        # Start thread
        thread = threading.Thread(target=run_training_task, args=(job.id, config_data))
        thread.start()
        
        serializer = TrainingModelSerializer(job)
        return Response(serializer.data)

class ActiveTrainingView(APIView):
    def get(self, request):
        # Find all active jobs
        active_jobs = TrainingModel.objects.filter(
            status__in=['pending', 'running', 'paused']
        ).order_by('-created_at')
        
        serializer = TrainingModelSerializer(active_jobs, many=True)
        return Response(serializer.data)

class TrainingStatusView(APIView):
    def get(self, request, pk):
        try:
            job = TrainingModel.objects.get(pk=pk)
            serializer = TrainingModelSerializer(job)
            return Response(serializer.data)
        except TrainingModel.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

class PredictView(APIView):
    def post(self, request):
        # Implementation for prediction would go here
        # It would load the model from the specified checkpoint and run inference
        return Response({'status': 'Not implemented yet, requires model loading logic'})

class PredictionResultView(APIView):
    def get(self, request, filename):
        # Return saved result file
        path = os.path.join(settings.BASE_DIR, 'results', filename) 
        if os.path.exists(path):
            # Return file content
            pass
        return Response({'status': 'todo'})
