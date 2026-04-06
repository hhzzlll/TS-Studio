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
from django.http import FileResponse
from .models import TrainingModel
from .serializers import TrainingModelSerializer
import sys
import pathlib
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose

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

class DatasetColumnsView(APIView):
    def get(self, request, filename):
        base_dir = str(settings.BASE_DIR)
        data_dir = os.path.join(base_dir, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, status=404)
            
        try:
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(file_path, nrows=0) 
            elif filename.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path, nrows=0)
            else:
                return Response({'error': 'Unsupported format'}, status=400)
                
            cols = df.columns.tolist()
            return Response({'columns': cols})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def delete(self, request):
        filename = request.query_params.get('filename')
        if not filename:
            return Response({'error': 'Filename required'}, status=status.HTTP_400_BAD_REQUEST)
            
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
             return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            os.remove(file_path)
            # Also try to clean up any cached analysis if exists? (Optional)
            return Response({'status': 'success', 'message': f'{filename} deleted'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DatasetDownloadView(APIView):
    def get(self, request):
        filename = request.query_params.get('filename')
        if not filename:
             return Response({'error': 'Filename required'}, status=status.HTTP_400_BAD_REQUEST)
             
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
             return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
             
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)

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

class StatisticalAnalysisView(APIView):
    def get(self, request):
        filename = request.query_params.get('filename')
        if not filename:
             return Response({'error': 'Filename required'}, status=status.HTTP_400_BAD_REQUEST)
             
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
             return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
             
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Filter only numeric columns for stats and correlation
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                 return Response({'error': 'No numeric columns found for analysis'}, status=status.HTTP_400_BAD_REQUEST)

            # Descriptive Statistics
            # Convert to dict and handle None/NaN for JSON
            stats = numeric_df.describe().to_dict()
            
            # Correlation Matrix
            correlation = numeric_df.corr()
            correlation = correlation.replace({np.nan: None}).to_dict()
            
            # Helper to clean floats for JSON (inf, nan)
            def clean_floats(obj):
                if isinstance(obj, float):
                    if np.isnan(obj): return None
                    if np.isinf(obj): return "Infinity" if obj > 0 else "-Infinity"
                if isinstance(obj, dict):
                    return {k: clean_floats(v) for k, v in obj.items()}
                return obj

            stats = clean_floats(stats)
            correlation = clean_floats(correlation)

            return Response({
                'filename': filename,
                'statistics': stats,
                'correlation': correlation
            })
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ColumnAnalysisView(APIView):
    def get(self, request):
        filename = request.query_params.get('filename')
        column = request.query_params.get('column')
        
        if not filename or not column:
             return Response({'error': 'Filename and column required'}, status=status.HTTP_400_BAD_REQUEST)
             
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
             return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
             
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            if column not in df.columns:
                 return Response({'error': f'Column {column} not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Helper to clean floats
            def clean_floats(obj):
                if isinstance(obj, float):
                    if np.isnan(obj): return None
                    if np.isinf(obj): return "Infinity" if obj > 0 else "-Infinity"
                if isinstance(obj, dict):
                    return {k: clean_floats(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [clean_floats(i) for i in obj]
                return obj

            # Prepare series data
            # Assume first column is time/date if not specified
            date_col = df.columns[0]
            labels = df[date_col].astype(str).tolist()
            values = df[column].tolist()
            
            # Clean data for stats analysis
            clean_series = df[column].dropna()
            if clean_series.empty:
                 return Response({'error': 'Column is empty or all NaN'}, status=status.HTTP_400_BAD_REQUEST)

            # 1. Stats
            stats = clean_series.describe().to_dict()
            
            # 2. Stationarity (ADF)
            stationarity = {}
            try:
                # ADF requires at least some variability
                if clean_series.nunique() > 1:
                    adf_res = adfuller(clean_series.values)
                    stationarity = {
                        'adf_statistic': adf_res[0],
                        'p_value': adf_res[1],
                        'critical_values': adf_res[4],
                        'is_stationary': bool(adf_res[1] < 0.05)
                    }
                else:
                    stationarity = {'error': 'Data is constant, cannot run ADF'}
            except Exception as e:
                stationarity = {'error': str(e)}

            # 3. Decomposition
            trend = []
            seasonal = []
            resid = []
            
            try:
                # Use a default period of 12 (monthly-like) or heuristic
                period = 12 
                if len(clean_series) > period * 2:
                    decomp = seasonal_decompose(clean_series, model='additive', period=period, extrapolate_trend='freq')
                    trend = decomp.trend.tolist()
                    seasonal = decomp.seasonal.tolist()
                    resid = decomp.resid.tolist()
                else:
                    # Too short for 12, try simple rolling mean
                    w = max(2, len(clean_series) // 5)
                    trend = clean_series.rolling(window=w, center=True).mean().bfill().ffill().tolist()
            except Exception as e:
                print(f"Decomposition error: {e}")
                # Fallback Trend
                try:
                     trend = clean_series.rolling(window=12, center=True).mean().fillna(0).tolist()
                except:
                     pass

            # 4. Anomaly Detection (3-Sigma)
            anomalies = []
            try:
                mean_val = clean_series.mean()
                std_val = clean_series.std()
                threshold = 3
                # Find indices where value is outlier
                anomaly_indices = clean_series[np.abs(clean_series - mean_val) > threshold * std_val].index
                # Map to [label, value] format for ECharts
                for idx in anomaly_indices:
                     # Check bounds just in case
                     if idx < len(labels):
                         anomalies.append([labels[idx], float(clean_series[idx])])
            except Exception as e:
                print(f"Anomaly detection error: {e}")

            # 5. Differencing
            diff_values = []
            diff_stationarity = {}
            try:
                diff_series = clean_series.diff()
                # For visualization: fill NaN calculation artifacts with 0 to keep length consistent
                diff_values = diff_series.fillna(0).tolist()
                
                # For Stats (ADF): Drop NaN to get accurate stats
                diff_series_clean = diff_series.dropna()
                if not diff_series_clean.empty and diff_series_clean.nunique() > 1:
                     adf_res_diff = adfuller(diff_series_clean.values)
                     diff_stationarity = {
                        'adf_statistic': adf_res_diff[0],
                        'p_value': adf_res_diff[1],
                        'critical_values': adf_res_diff[4],
                        'is_stationary': bool(adf_res_diff[1] < 0.05)
                    }
                else:
                    diff_stationarity = {'error': 'Data is constant or empty after differencing'}
                    
            except Exception as e:
                print(f"Differencing error: {e}")
                diff_stationarity = {'error': str(e)}

            # 6. FFT (Spectrum)
            fft_freqs = []
            fft_mags = []
            fft_peaks = []
            try:
                n = len(clean_series)
                if n > 0:
                    fft_vals = np.fft.fft(clean_series.values)
                    # Positive frequencies
                    n_half = n // 2
                    freqs = np.fft.fftfreq(n)[:n_half]
                    mags = np.abs(fft_vals)[:n_half] / n # Normalize
                    
                    # Remove DC (idx 0)
                    if len(mags) > 0: 
                        mags[0] = 0
                        
                    # Convert to list
                    fft_freqs = freqs.tolist()
                    fft_mags = mags.tolist()

                    # Identify Top-3 Peaks
                    if len(mags) > 0:
                        # indices of max elements
                        top_indices = np.argsort(mags)[-3:][::-1]
                        for idx in top_indices:
                            f = freqs[idx]
                            m = mags[idx]
                            # Only keep valid peaks
                            if m > 1e-9 and f > 0:
                                fft_peaks.append({
                                    'freq': float(f),
                                    'period': float(1.0/f),
                                    'mag': float(m)
                                })
            except Exception as e:
                print(f"FFT error: {e}")

            return Response(clean_floats({
                'column': column,
                'labels': labels,
                'values': values,
                'stats': stats,
                'stationarity': stationarity,
                'trend': trend,
                'seasonal': seasonal,
                'resid': resid,
                'anomalies': anomalies,
                'diff_values': diff_values,
                'diff_stationarity': diff_stationarity,
                'fft_freqs': fft_freqs,
                'fft_mags': fft_mags,
                'fft_peaks': fft_peaks
            }))

        except Exception as e:
            traceback.print_exc()
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
        args.itr = 1
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

class CompletedModelsView(APIView):
    def get(self, request):
        jobs = TrainingModel.objects.filter(status='completed').order_by('-created_at')
        serializer = TrainingModelSerializer(jobs, many=True)
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
        # This could be used for running inference on NEW data
        return Response({'status': 'Not implemented yet'})

class PredictionResultView(APIView):
    def get(self, request, pk):
        try:
            job = TrainingModel.objects.get(pk=pk)
            config = job.config
            
            # Reconstruct setting string to find folder
            # Needed: model_id, model, data, features, seq_len, label_len, pred_len, ii, stage_mode
            # We assume ii=0 for now or try to find it
            
            # Defaults must match run_training_task defaults if missing
            model = config.get('model', 'DDPM')
            data_type = config.get('dataset_type', 'custom')
            features = config.get('features', 'M')
            seq_len = config.get('seq_len', 192)
            label_len = config.get('label_len', 7) # This might have been auto-calculated in run_training_task but stored in config? 
            # Wait, config stored in DB is request.data. 
            # In run_training_task: args.label_len = int(args.pred_len / 2)
            # So we should recalculate here to match
            pred_len = config.get('pred_len', 14)
            label_len = int(pred_len / 2) # Force recalculate to match logic
            
            dataset_name = config.get('dataset_name', 'Exchange')
            # model_id logic
            model_id = config.get('model_id', "{}_{}_{}".format(dataset_name, seq_len, pred_len))
            stage_mode = config.get('stage_mode', 'TWO')
            
            ii = 0
            setting = '{}_{}_{}_ft{}_sl{}_ll{}_pl{}_dt{}_{}'.format(
                model_id,
                model,
                data_type,
                features,
                seq_len,
                label_len,
                pred_len, 
                ii,
                stage_mode)
            
            # Checkpoints folder
            ckpt_root = './checkpoints/' # Default in args
            folder_path = os.path.join(ckpt_root, setting)
            
            preds_path = os.path.join(folder_path, 'preds.npy')
            trues_path = os.path.join(folder_path, 'trues.npy')
            history_path = os.path.join(folder_path, 'history.npy')
            
            if not os.path.exists(preds_path):
                 # Try absolute path or project root logic
                 base_dir = str(settings.BASE_DIR)
                 # backend/checkpoints/...
                 folder_path = os.path.join(base_dir, 'checkpoints', setting)
                 preds_path = os.path.join(folder_path, 'preds.npy')
                 trues_path = os.path.join(folder_path, 'trues.npy')
                 history_path = os.path.join(folder_path, 'history.npy')

            if not os.path.exists(preds_path):
                return Response({'error': f'Results not found at {folder_path}'}, status=404)
            
            # Load data
            preds = np.load(preds_path)
            trues = np.load(trues_path)
            
            history = []
            if os.path.exists(history_path):
                history = np.load(history_path)
            
            # preds shape: (Samples, PredLen, Dims)
            # Return first N samples
            limit = int(request.query_params.get('limit', 10))
            
            response_data = {
                'preds': preds[:limit].tolist(),
                'trues': trues[:limit].tolist(),
                'shape': preds.shape,
                'setting': setting
            }
            if len(history) > 0:
                response_data['history'] = history[:limit].tolist()
            
            return Response(response_data)

        except TrainingModel.DoesNotExist:
            return Response({'error': 'Job not found'}, status=404)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


class TraditionalModelListView(APIView):
    """获取可用的传统模型列表"""
    def get(self, request):
        models = [
            {
                'id': 'arima',
                'name': 'ARIMA',
                'description': '自回归移动平均模型，适用于线性时间序列'
            },
            {
                'id': 'exponential_smoothing',
                'name': '指数平滑',
                'description': '基于加权平均的预测方法，适用于有趋势的数据'
            },
            {
                'id': 'moving_average',
                'name': '移动平均',
                'description': '基于历史平均值的简单预测方法'
            },
            {
                'id': 'prophet',
                'name': 'Prophet',
                'description': 'Facebook开发的时间序列预测工具，适用于有季节性的数据'
            }
        ]
        return Response(models)


class TraditionalModelPredictView(APIView):
    """使用传统模型进行预测"""
    def post(self, request):
        from .traditional_models import load_and_predict
        
        try:
            # 获取参数
            model_type = request.data.get('model_type', 'arima')
            dataset_name = request.data.get('dataset_name')
            filename = request.data.get('filename')
            pred_len = int(request.data.get('pred_len', 14))
            seq_len = int(request.data.get('seq_len', 192))
            features = request.data.get('features', 'M')
            target_col = request.data.get('target_col', None)
            limit = int(request.data.get('limit', 50))
            
            # 支持动态超参数
            model_params = request.data.get('model_params', {})
            
            # 确定数据集路径
            if filename:
                dataset_path = os.path.join(settings.BASE_DIR, 'data', filename)
            elif dataset_name:
                # 尝试常见文件格式
                for ext in ['.csv', '.xlsx']:
                    path = os.path.join(settings.BASE_DIR, 'data', dataset_name + ext)
                    if os.path.exists(path):
                        dataset_path = path
                        break
                else:
                    return Response({
                        'error': f'Dataset {dataset_name} not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Please provide dataset_name or filename'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not os.path.exists(dataset_path):
                return Response({
                    'error': f'Dataset file not found: {dataset_path}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 运行预测
            result = load_and_predict(
                dataset_path=dataset_path,
                model_type=model_type,
                pred_len=pred_len,
                seq_len=seq_len,
                target_col=target_col,
                features=features,
                model_params=model_params
            )
            
            # 限制返回的样本数
            preds = result['preds'][:limit]
            trues = result['trues'][:limit]
            histories = result['history'][:limit]
            
            return Response({
                'preds': preds.tolist(),
                'trues': trues.tolist(),
                'history': histories.tolist(),
                'shape': list(preds.shape),
                'model_type': model_type,
                'status': 'success'
            })
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
