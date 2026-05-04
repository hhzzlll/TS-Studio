"""
传统时间序列预测模型
支持: ARIMA, Prophet, Exponential Smoothing, Simple LSTM
"""
import os
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

class TraditionalPredictor:
    """传统模型预测器基类"""
    def __init__(self, model_type='arima', model_params=None):
        self.model_type = model_type
        self.model = None
        self.model_params = model_params or {}
        
    def fit_predict(self, data, pred_len=14, seq_len=192):
        """
        训练并预测
        
        Args:
            data: numpy array, shape (N, dims) 数据
            pred_len: int, 预测长度
            seq_len: int, 历史长度
            
        Returns:
            predictions: numpy array, shape (samples, pred_len, dims)
            ground_truth: numpy array, shape (samples, pred_len, dims)
        """
        if self.model_type == 'arima':
            return self._arima_predict(data, pred_len, seq_len)
        elif self.model_type == 'prophet':
            return self._prophet_predict(data, pred_len, seq_len)
        elif self.model_type == 'exponential_smoothing':
            return self._exp_smoothing_predict(data, pred_len, seq_len)
        elif self.model_type == 'moving_average':
            return self._moving_average_predict(data, pred_len, seq_len)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def predict_on_histories(self, histories, pred_len=14):
        """
        基于给定历史窗口进行预测

        Args:
            histories: numpy array, shape (samples, seq_len, dims)
            pred_len: int, 预测长度

        Returns:
            predictions: numpy array, shape (samples, pred_len, dims)
        """
        predictions = []
        for history in histories:
            if self.model_type == 'arima':
                pred = self._arima_predict_single(history, pred_len)
            elif self.model_type == 'prophet':
                pred = self._prophet_predict_single(history, pred_len)
            elif self.model_type == 'exponential_smoothing':
                pred = self._exp_smoothing_predict_single(history, pred_len)
            elif self.model_type == 'moving_average':
                pred = self._moving_average_predict_single(history, pred_len)
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")
            predictions.append(pred)
        return np.array(predictions)
    
    def _arima_predict(self, data, pred_len, seq_len):
        """ARIMA模型预测"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            from statsmodels.tsa.arima_model import ARIMA
            
        n_samples = max(1, len(data) - seq_len - pred_len + 1)
        n_dims = data.shape[1] if len(data.shape) > 1 else 1
        
        predictions = []
        ground_truth = []
        histories = []
        
        # 滚动预测
        for i in range(0, n_samples, pred_len + seq_len):
            if len(predictions) >= 50:  # 限制样本数避免过长时间
                break
            
            # 获取历史数据和真实值
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            # 对每个维度独立建模
            for dim in range(n_dims):
                try:
                    ts = history[:, dim] if n_dims > 1 else history
                    
                    # 获取ARIMA参数，默认为(1,1,1)
                    p = int(self.model_params.get('p', 1))
                    d = int(self.model_params.get('d', 1))
                    q = int(self.model_params.get('q', 1))
                    
                    use_seasonal = self.model_params.get('use_seasonal', False)
                    seasonal_order = (0, 0, 0, 0)
                    if use_seasonal:
                        P = int(self.model_params.get('P', 1))
                        D = int(self.model_params.get('D', 1))
                        Q = int(self.model_params.get('Q', 1))
                        s = int(self.model_params.get('s', 12))
                        seasonal_order = (P, D, Q, s)
                    
                    model = ARIMA(ts, order=(p, d, q), seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
                    model_fit = model.fit()
                    
                    # 预测
                    forecast = model_fit.forecast(steps=pred_len)
                    pred_sample.append(forecast)
                    
                except Exception as e:
                    print(f"[ARIMA Error] {e}")
                    # 如果ARIMA失败，使用最后一个值作为预测
                    last_val = ts[-1]
                    forecast = np.full(pred_len, last_val)
                    pred_sample.append(forecast)
            
            pred_sample = np.array(pred_sample).T  # (pred_len, dims)
            predictions.append(pred_sample)
            ground_truth.append(true_future)
            histories.append(history)
        
        return np.array(predictions), np.array(ground_truth), np.array(histories)

    def _arima_predict_single(self, history, pred_len):
        """ARIMA模型单样本预测"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            from statsmodels.tsa.arima_model import ARIMA

        n_dims = history.shape[1] if len(history.shape) > 1 else 1
        pred_sample = []
        for dim in range(n_dims):
            try:
                ts = history[:, dim] if n_dims > 1 else history
                p = int(self.model_params.get('p', 1))
                d = int(self.model_params.get('d', 1))
                q = int(self.model_params.get('q', 1))

                use_seasonal = self.model_params.get('use_seasonal', False)
                seasonal_order = (0, 0, 0, 0)
                if use_seasonal:
                    P = int(self.model_params.get('P', 1))
                    D = int(self.model_params.get('D', 1))
                    Q = int(self.model_params.get('Q', 1))
                    s = int(self.model_params.get('s', 12))
                    seasonal_order = (P, D, Q, s)

                model = ARIMA(ts, order=(p, d, q), seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
                model_fit = model.fit()
                forecast = model_fit.forecast(steps=pred_len)
                pred_sample.append(forecast)
            except Exception as e:
                print(f"[ARIMA Error] {e}")
                last_val = ts[-1]
                forecast = np.full(pred_len, last_val)
                pred_sample.append(forecast)
        return np.array(pred_sample).T
    
    def _prophet_predict(self, data, pred_len, seq_len):
        """Prophet模型预测"""
        try:
            from prophet import Prophet
        except ImportError:
            # 如果Prophet未安装，降级为移动平均
            print("Prophet not installed, using moving average instead")
            return self._moving_average_predict(data, pred_len, seq_len)
        
        n_samples = max(1, len(data) - seq_len - pred_len + 1)
        n_dims = data.shape[1] if len(data.shape) > 1 else 1
        
        predictions = []
        ground_truth = []
        histories = []
        
        for i in range(0, n_samples, pred_len + seq_len):
            if len(predictions) >= 20:
                break
            
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            for dim in range(n_dims):
                try:
                    ts = history[:, dim] if n_dims > 1 else history.flatten()
                    
                    # 准备Prophet数据格式
                    df = pd.DataFrame({
                        'ds': pd.date_range(start='2020-01-01', periods=len(ts), freq='h'),
                        'y': ts
                    })
                    
                    # 取出Prophet参数
                    seasonality_mode = self.model_params.get('seasonality_mode', 'additive')
                    yearly_seasonality = self.model_params.get('yearly_seasonality', False)
                    weekly_seasonality = self.model_params.get('weekly_seasonality', 'auto')
                    daily_seasonality = self.model_params.get('daily_seasonality', True)
                    
                    # 确保布尔值转换正确
                    if str(yearly_seasonality).lower() in ['true', '1']: yearly_seasonality = True
                    if str(yearly_seasonality).lower() in ['false', '0']: yearly_seasonality = False
                    if str(daily_seasonality).lower() in ['true', '1']: daily_seasonality = True
                    if str(daily_seasonality).lower() in ['false', '0']: daily_seasonality = False
                    
                    # 训练Prophet
                    model = Prophet(
                        seasonality_mode=seasonality_mode,
                        yearly_seasonality=yearly_seasonality,
                        weekly_seasonality=weekly_seasonality,
                        daily_seasonality=daily_seasonality
                    )
                    model.fit(df)
                    
                    # 预测
                    future = model.make_future_dataframe(periods=pred_len, freq='h')
                    forecast = model.predict(future)
                    pred_values = forecast['yhat'].values[-pred_len:]
                    
                    pred_sample.append(pred_values)
                    
                except Exception as e:
                    print(f"[Prophet Error] {e}")
                    # 降级为最后值
                    last_val = ts[-1]
                    forecast = np.full(pred_len, last_val)
                    pred_sample.append(forecast)
            
            pred_sample = np.array(pred_sample).T
            predictions.append(pred_sample)
            ground_truth.append(true_future)
            histories.append(history)
        
        return np.array(predictions), np.array(ground_truth), np.array(histories)

    def _prophet_predict_single(self, history, pred_len):
        """Prophet模型单样本预测"""
        try:
            from prophet import Prophet
        except ImportError:
            print("Prophet not installed, using moving average instead")
            return self._moving_average_predict_single(history, pred_len)

        n_dims = history.shape[1] if len(history.shape) > 1 else 1
        pred_sample = []
        for dim in range(n_dims):
            try:
                ts = history[:, dim] if n_dims > 1 else history.flatten()
                df = pd.DataFrame({
                    'ds': pd.date_range(start='2020-01-01', periods=len(ts), freq='h'),
                    'y': ts
                })

                seasonality_mode = self.model_params.get('seasonality_mode', 'additive')
                yearly_seasonality = self.model_params.get('yearly_seasonality', False)
                weekly_seasonality = self.model_params.get('weekly_seasonality', 'auto')
                daily_seasonality = self.model_params.get('daily_seasonality', True)

                if str(yearly_seasonality).lower() in ['true', '1']:
                    yearly_seasonality = True
                if str(yearly_seasonality).lower() in ['false', '0']:
                    yearly_seasonality = False
                if str(daily_seasonality).lower() in ['true', '1']:
                    daily_seasonality = True
                if str(daily_seasonality).lower() in ['false', '0']:
                    daily_seasonality = False

                model = Prophet(
                    seasonality_mode=seasonality_mode,
                    yearly_seasonality=yearly_seasonality,
                    weekly_seasonality=weekly_seasonality,
                    daily_seasonality=daily_seasonality
                )
                model.fit(df)

                future = model.make_future_dataframe(periods=pred_len, freq='h')
                forecast = model.predict(future)
                pred_values = forecast['yhat'].values[-pred_len:]
                pred_sample.append(pred_values)
            except Exception as e:
                print(f"[Prophet Error] {e}")
                last_val = ts[-1]
                forecast = np.full(pred_len, last_val)
                pred_sample.append(forecast)

        return np.array(pred_sample).T
    
    def _exp_smoothing_predict(self, data, pred_len, seq_len):
        """指数平滑预测"""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        
        n_samples = max(1, len(data) - seq_len - pred_len + 1)
        n_dims = data.shape[1] if len(data.shape) > 1 else 1
        
        predictions = []
        ground_truth = []
        histories = []
        
        for i in range(0, n_samples, pred_len + seq_len):
            if len(predictions) >= 50:
                break
                
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            for dim in range(n_dims):
                try:
                    ts = history[:, dim] if n_dims > 1 else history
                    
                    # 获取指数平滑参数
                    trend = self.model_params.get('trend', 'add')
                    seasonal = self.model_params.get('seasonal', None)
                    seasonal_periods = int(self.model_params.get('seasonal_periods', 24))
                    
                    if str(trend).lower() in ['none', 'null', '']: trend = None
                    if str(seasonal).lower() in ['none', 'null', '']: seasonal = None
                    
                    # 使用指数平滑
                    model = ExponentialSmoothing(ts, seasonal=seasonal, trend=trend, seasonal_periods=seasonal_periods if seasonal else None)
                    model_fit = model.fit()
                    
                    forecast = model_fit.forecast(steps=pred_len)
                    pred_sample.append(forecast)
                    
                except Exception as e:
                    print(f"[Exp Smoothing Error] {e}")
                    # 降级策略
                    last_val = ts[-1]
                    forecast = np.full(pred_len, last_val)
                    pred_sample.append(forecast)
            
            pred_sample = np.array(pred_sample).T
            predictions.append(pred_sample)
            ground_truth.append(true_future)
            histories.append(history)
        
        return np.array(predictions), np.array(ground_truth), np.array(histories)

    def _exp_smoothing_predict_single(self, history, pred_len):
        """指数平滑单样本预测"""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        n_dims = history.shape[1] if len(history.shape) > 1 else 1
        pred_sample = []
        for dim in range(n_dims):
            try:
                ts = history[:, dim] if n_dims > 1 else history
                trend = self.model_params.get('trend', 'add')
                seasonal = self.model_params.get('seasonal', None)
                seasonal_periods = int(self.model_params.get('seasonal_periods', 24))

                if str(trend).lower() in ['none', 'null', '']:
                    trend = None
                if str(seasonal).lower() in ['none', 'null', '']:
                    seasonal = None

                model = ExponentialSmoothing(ts, seasonal=seasonal, trend=trend, seasonal_periods=seasonal_periods if seasonal else None)
                model_fit = model.fit()
                forecast = model_fit.forecast(steps=pred_len)
                pred_sample.append(forecast)
            except Exception as e:
                print(f"[Exp Smoothing Error] {e}")
                last_val = ts[-1]
                forecast = np.full(pred_len, last_val)
                pred_sample.append(forecast)

        return np.array(pred_sample).T
    
    def _moving_average_predict(self, data, pred_len, seq_len):
        """移动平均预测"""
        n_samples = max(1, len(data) - seq_len - pred_len + 1)
        n_dims = data.shape[1] if len(data.shape) > 1 else 1
        
        predictions = []
        ground_truth = []
        histories = []
        
        # 用户指定的窗口大小
        window = int(self.model_params.get('window', min(20, seq_len // 4)))
        window = max(1, window) # 保证至少为1
        
        ma_type = self.model_params.get('ma_type', 'simple')
        weights = np.arange(1, window + 1) if ma_type == 'weighted' else None
        weight_sum = np.sum(weights) if weights is not None else None
        
        for i in range(0, n_samples, pred_len + seq_len):
            if len(predictions) >= 100:
                break
                
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            for dim in range(n_dims):
                ts = history[:, dim] if n_dims > 1 else history.reshape(-1)

                # 递推移动平均：每步预测都更新窗口
                window_values = list(ts[-window:])
                forecast = []
                for _ in range(pred_len):
                    if ma_type == 'weighted':
                        ma_value = float(np.sum(np.array(window_values) * weights) / weight_sum)
                    else:
                        ma_value = float(np.mean(window_values))
                    forecast.append(ma_value)
                    window_values.append(ma_value)
                    if len(window_values) > window:
                        window_values.pop(0)
                pred_sample.append(np.array(forecast))
            
            pred_sample = np.array(pred_sample).T
            predictions.append(pred_sample)
            ground_truth.append(true_future)
            histories.append(history)
        
        return np.array(predictions), np.array(ground_truth), np.array(histories)

    def _moving_average_predict_single(self, history, pred_len):
        """移动平均单样本预测"""
        n_dims = history.shape[1] if len(history.shape) > 1 else 1
        pred_sample = []

        window = int(self.model_params.get('window', min(20, history.shape[0] // 4)))
        window = max(1, window)
        ma_type = self.model_params.get('ma_type', 'simple')
        weights = np.arange(1, window + 1) if ma_type == 'weighted' else None
        weight_sum = np.sum(weights) if weights is not None else None

        for dim in range(n_dims):
            ts = history[:, dim] if n_dims > 1 else history.reshape(-1)
            window_values = list(ts[-window:])
            forecast = []
            for _ in range(pred_len):
                if ma_type == 'weighted':
                    ma_value = float(np.sum(np.array(window_values) * weights) / weight_sum)
                else:
                    ma_value = float(np.mean(window_values))
                forecast.append(ma_value)
                window_values.append(ma_value)
                if len(window_values) > window:
                    window_values.pop(0)
            pred_sample.append(np.array(forecast))

        return np.array(pred_sample).T


def load_and_predict(dataset_path, model_type='arima', pred_len=14, seq_len=192, 
                     target_col=None, features='M', model_params=None):
    """
    加载数据并使用传统模型预测
    
    Args:
        dataset_path: str, 数据集路径
        model_type: str, 模型类型
        pred_len: int, 预测长度
        seq_len: int, 历史长度
        target_col: str, 目标列名 (用于S模式)
        features: str, 'M'表示多变量, 'S'表示单变量
        model_params: dict, 模型相关参数
        
    Returns:
        dict: {
            'preds': predictions array,
            'trues': ground_truth array,
            'shape': tuple,
            'model_type': str
        }
    """
    # 读取数据
    if dataset_path.endswith('.csv'):
        df = pd.read_csv(dataset_path)
    else:
        df = pd.read_excel(dataset_path)
    
    # 数据预处理
    # 假设第一列是时间列
    if 'date' in df.columns.str.lower():
        df = df.drop(df.columns[df.columns.str.lower() == 'date'][0], axis=1)
    elif len(df.columns) > 1 and df.iloc[:, 0].dtype == 'object':
        df = df.iloc[:, 1:]  # 删除第一列（可能是日期）
    
    # 只保留数值列
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df = df[numeric_cols]
    
    # 选择特征
    if features == 'S' and target_col and target_col in df.columns:
        # 单变量预测，只使用目标列
        data = df[[target_col]].values
    elif features == 'S' and not target_col:
        # 默认使用最后一列
        data = df.iloc[:, -1:].values
    else:
        # 多变量预测
        data = df.values
    
    # 数据标准化
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0) + 1e-8
    data = (data - mean) / std
    
    # 创建预测器并传递参数
    predictor = TraditionalPredictor(model_type=model_type, model_params=model_params)
    
    # 预测
    preds, trues, histories = predictor.fit_predict(data, pred_len, seq_len)
    
    # 反标准化
    preds = preds * std + mean
    trues = trues * std + mean
    histories = histories * std + mean
    
    return {
        'preds': preds,
        'trues': trues,
        'history': histories,
        'shape': preds.shape,
        'model_type': model_type
    }


def load_and_predict_aligned(dataset_path, model_type='arima', pred_len=14, seq_len=192,
                             target_col=None, features='M', model_params=None,
                             dataset_name='Exchange', dataset_type='custom',
                             freq='h', label_len=None, limit=50, step=None):
    """
    使用与深度学习一致的测试集窗口进行预测（对齐历史序列）
    """
    from backend.algorithm.data_provider.data_factory import data_provider

    class Args:
        pass

    args = Args()
    args.dataset_name = dataset_name or 'Exchange'
    args.data = dataset_type or 'custom'
    args.seq_len = int(seq_len)
    args.pred_len = int(pred_len)
    args.label_len = int(label_len) if label_len is not None else int(pred_len / 2)
    args.features = features
    args.target = target_col or 'OT'
    args.embed = 'timeF'
    args.freq = freq
    args.batch_size = 64
    args.test_batch_size = 64
    args.num_workers = 0
    args.root_path = os.path.dirname(dataset_path)
    args.data_path = os.path.basename(dataset_path)

    _, data_loader = data_provider(args, flag='test', shuffle_flag_train=False)

    step = int(step) if step is not None else (args.seq_len + args.pred_len)
    predictor = TraditionalPredictor(model_type=model_type, model_params=model_params)

    predictions = []
    ground_truth = []
    histories = []

    global_index = 0
    for batch in data_loader:
        batch_x, batch_y = batch[0], batch[1]
        batch_x = batch_x.detach().cpu().numpy()
        batch_y = batch_y.detach().cpu().numpy()

        for i in range(batch_x.shape[0]):
            if global_index % step == 0:
                history = batch_x[i]
                true_future = batch_y[i][-args.pred_len:]
                pred_sample = predictor.predict_on_histories(np.expand_dims(history, axis=0), pred_len=args.pred_len)[0]

                histories.append(history)
                ground_truth.append(true_future)
                predictions.append(pred_sample)

                if limit is not None and len(predictions) >= int(limit):
                    break
            global_index += 1

        if limit is not None and len(predictions) >= int(limit):
            break

    return {
        'preds': np.array(predictions),
        'trues': np.array(ground_truth),
        'history': np.array(histories),
        'shape': np.array(predictions).shape,
        'model_type': model_type,
        'aligned_with_dl': True
    }
