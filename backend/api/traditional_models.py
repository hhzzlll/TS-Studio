"""
传统时间序列预测模型
支持: ARIMA, Prophet, Exponential Smoothing, Simple LSTM
"""
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
        for i in range(min(n_samples, 50)):  # 限制样本数避免过长时间
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
                    
                    model = ARIMA(ts, order=(p, d, q), enforce_stationarity=False, enforce_invertibility=False)
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
        
        for i in range(min(n_samples, 20)):
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            for dim in range(n_dims):
                try:
                    ts = history[:, dim] if n_dims > 1 else history
                    
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
    
    def _exp_smoothing_predict(self, data, pred_len, seq_len):
        """指数平滑预测"""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        
        n_samples = max(1, len(data) - seq_len - pred_len + 1)
        n_dims = data.shape[1] if len(data.shape) > 1 else 1
        
        predictions = []
        ground_truth = []
        histories = []
        
        for i in range(min(n_samples, 50)):
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
        
        for i in range(min(n_samples, 100)):
            history = data[i:i+seq_len]
            true_future = data[i+seq_len:i+seq_len+pred_len]
            
            if len(true_future) < pred_len:
                break
                
            pred_sample = []
            
            for dim in range(n_dims):
                ts = history[:, dim] if n_dims > 1 else history
                
                # 使用最后window个值的平均作为预测
                ma_value = np.mean(ts[-window:])
                
                # 简单策略：使用移动平均值作为所有预测点
                forecast = np.full(pred_len, ma_value)
                pred_sample.append(forecast)
            
            pred_sample = np.array(pred_sample).T
            predictions.append(pred_sample)
            ground_truth.append(true_future)
            histories.append(history)
        
        return np.array(predictions), np.array(ground_truth), np.array(histories)


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
