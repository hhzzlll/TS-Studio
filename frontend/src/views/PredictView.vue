<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { getCompletedModels, getPredictionResult, getTraditionalModels, predictWithTraditionalModel, getDatasetColumns } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'
import * as echarts from 'echarts'

// 深度学习模型相关
const deepModels = ref<any[]>([])
const selectedDeepModelId = ref<string>('')

// 传统模型相关
const traditionalModels = ref<any[]>([])
const datasetColumns = ref<string[]>([])
const selectedColumn = ref<string>('')
const compareWithTraditional = ref(false)
const metricMode = ref<'overall' | 'current'>('overall')

// 传统模型的高级参数
const modelParams = ref<any>({
  // arima
  p: 1, d: 1, q: 1, use_seasonal: false, P: 1, D: 1, Q: 1, s: 12,
  // prophet
  seasonality_mode: 'additive', yearly_seasonality: false, weekly_seasonality: 'auto', daily_seasonality: true,
  // exp smoothing
  trend: 'add', seasonal: 'none', seasonal_periods: 24,
  // moving average
  window: 20, ma_type: 'simple'
})

const loading = ref(false)
const deepResult = ref<any>(null)
const traditionalResultsByModel = ref<Record<string, any>>({})
const sampleIndex = ref(0)
const totalSamples = ref(0)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

const getCurrentDeepModel = () => {
  return deepModels.value.find((m: any) => String(m.id) === String(selectedDeepModelId.value))
}

const getCurrentDatasetFile = () => {
  const deepModel = getCurrentDeepModel()
  if (!deepModel?.config) return ''
  if (deepModel.config.filename) return deepModel.config.filename
  if (deepModel.config.dataset_name) return `${deepModel.config.dataset_name}.csv`
  return ''
}

const getDeepColumnOrder = () => {
  const deepModel = getCurrentDeepModel()
  const datasetType = deepModel?.config?.dataset_type || deepModel?.config?.data || 'custom'
  const target = deepModel?.config?.target
  const cols = [...datasetColumns.value]

  if (datasetType === 'custom' && target && cols.includes(target)) {
    return [...cols.filter((c) => c !== target), target]
  }

  return cols
}

const getDeepDimToShow = () => {
  const cols = getDeepColumnOrder()
  if (!selectedColumn.value || cols.length === 0) return null
  const idx = cols.indexOf(selectedColumn.value)
  return idx >= 0 ? idx : cols.length - 1
}

onMounted(async () => {
  try {
    // 加载深度学习模型
    const res: any = await getCompletedModels()
    deepModels.value = res
    if (deepModels.value.length > 0) {
      selectedDeepModelId.value = deepModels.value[0].id
    }
    
    // 加载传统模型列表
    const traditionalRes: any = await getTraditionalModels()
    traditionalModels.value = traditionalRes
    
    await fetchColumns()
    
  } catch (e) {
    console.error(e)
  }
  
  window.addEventListener('resize', () => {
    myChart?.resize()
  })
})

const fetchColumns = async () => {
  const datasetFile = getCurrentDatasetFile()
  if (!datasetFile) return
  try {
    const res: any = await getDatasetColumns(datasetFile)
    // Filter out date column if possible or let user handle it?
    // Backend usually handles filtering date column for data, but we might want to hide it from selection
    // For now show all columns
    datasetColumns.value = res.columns.filter((c: string) => c.toLowerCase() !== 'date')
    if(datasetColumns.value.length > 0) {
      selectedColumn.value = datasetColumns.value[datasetColumns.value.length - 1] // Default to last column (usually target)
    }
  } catch(e) {
    console.error(e)
    datasetColumns.value = []
    selectedColumn.value = ''
  }
}

watch(selectedDeepModelId, () => {
  fetchColumns()
})

// 运行深度学习模型预测
const handleDeepModelPredict = async () => {
    if (!selectedDeepModelId.value) return
    try {
    const res: any = await getPredictionResult(Number(selectedDeepModelId.value), 50)
    return res
    } catch (e) {
        console.error(e)
    return null
    }
}

const getModelParams = (modelId: string) => {
  if (modelId === 'arima') {
    return {
      p: modelParams.value.p,
      d: modelParams.value.d,
      q: modelParams.value.q,
      use_seasonal: modelParams.value.use_seasonal,
      P: modelParams.value.P,
      D: modelParams.value.D,
      Q: modelParams.value.Q,
      s: modelParams.value.s
    }
  }
  if (modelId === 'prophet') {
    return {
      seasonality_mode: modelParams.value.seasonality_mode,
      yearly_seasonality: modelParams.value.yearly_seasonality,
      weekly_seasonality: modelParams.value.weekly_seasonality,
      daily_seasonality: modelParams.value.daily_seasonality
    }
  }
  if (modelId === 'exponential_smoothing') {
    return {
      trend: modelParams.value.trend,
      seasonal: modelParams.value.seasonal,
      seasonal_periods: modelParams.value.seasonal_periods
    }
  }
  if (modelId === 'moving_average') {
    return {
      window: modelParams.value.window,
      ma_type: modelParams.value.ma_type
    }
  }
  return {}
}

const handleAllTraditionalPredict = async () => {
  const datasetFile = getCurrentDatasetFile()
  if (!datasetFile || !selectedColumn.value) return null
  const deepModel = getCurrentDeepModel()
  const datasetType = deepModel?.config?.dataset_type || 'custom'
  const datasetName = deepModel?.config?.dataset_name || 'Exchange'
  const deepSeqLen = deepModel?.config?.seq_len || 192
  const deepPredLen = deepModel?.config?.pred_len || 14
  const deepLabelLen = deepModel?.config?.label_len || Math.floor(deepPredLen / 2)
  const deepFreq = deepModel?.config?.freq || 'h'

  const requests = traditionalModels.value.map((m: any) => {
    return predictWithTraditionalModel({
      model_type: m.id,
      filename: datasetFile,
      pred_len: deepPredLen,
      seq_len: deepSeqLen,
      features: 'S',
      target_col: selectedColumn.value,
      limit: 50,
      model_params: getModelParams(m.id),
      align_with_dl: true,
      dataset_type: datasetType,
      dataset_name: datasetName,
      label_len: deepLabelLen,
      freq: deepFreq
    }).then((res: any) => ({ id: m.id, name: m.name, result: res }))
  })

  const responses = await Promise.all(requests)
  const resultMap: Record<string, any> = {}
  responses.forEach((r) => {
    resultMap[r.id] = { ...r.result, model_name: r.name }
  })
  return resultMap
}

const calcMaeMse = (preds: any[], trues: any[], dimIndex: number | null) => {
  if (!preds?.length || !trues?.length) {
    return { mae: null, mse: null }
  }

  let absSum = 0
  let sqSum = 0
  let count = 0

  for (let i = 0; i < preds.length; i++) {
    const pred = preds[i]
    const true_ = trues[i]
    for (let t = 0; t < pred.length; t++) {
      const predRow = pred[t]
      const trueRow = true_[t]
      if (Array.isArray(predRow)) {
        if (dimIndex !== null && dimIndex < predRow.length) {
          const diff = predRow[dimIndex] - trueRow[dimIndex]
          absSum += Math.abs(diff)
          sqSum += diff * diff
          count += 1
        } else {
          for (let d = 0; d < predRow.length; d++) {
            const diff = predRow[d] - trueRow[d]
            absSum += Math.abs(diff)
            sqSum += diff * diff
            count += 1
          }
        }
      } else {
        const diff = predRow - trueRow
        absSum += Math.abs(diff)
        sqSum += diff * diff
        count += 1
      }
    }
  }

  if (count === 0) {
    return { mae: null, mse: null }
  }

  return { mae: absSum / count, mse: sqSum / count }
}

const getMetricsForMode = (result: any, dimIndex: number | null) => {
  if (!result?.preds?.length || !result?.trues?.length) {
    return { mae: null, mse: null }
  }

  if (metricMode.value === 'current') {
    const pred = result.preds[sampleIndex.value]
    const true_ = result.trues[sampleIndex.value]
    return calcMaeMse([pred], [true_], dimIndex)
  }

  return calcMaeMse(result.preds, result.trues, dimIndex)
}

const traditionalMetrics = computed(() => {
  if (!compareWithTraditional.value) return []
  const dimIndex = getDeepDimToShow()
  return traditionalModels.value
    .map((m: any) => {
      const result = traditionalResultsByModel.value[m.id]
      if (!result) return null
      const metrics = getMetricsForMode(result, dimIndex)
      return {
        id: m.id,
        name: m.name,
        mae: metrics.mae,
        mse: metrics.mse
      }
    })
    .filter(Boolean)
})

const deepMetrics = computed(() => {
  if (!deepResult.value) return { mae: null, mse: null }
  return getMetricsForMode(deepResult.value, getDeepDimToShow())
})

const handlePredict = async () => {
  if (!selectedDeepModelId.value) return
  if (compareWithTraditional.value && (!getCurrentDatasetFile() || !selectedColumn.value)) return

  loading.value = true
  try {
    const [deepRes, traditionalResAll] = await Promise.all([
      handleDeepModelPredict(),
      compareWithTraditional.value ? handleAllTraditionalPredict() : Promise.resolve(null)
    ])

    deepResult.value = deepRes
    traditionalResultsByModel.value = traditionalResAll || {}

    const deepSamples = deepRes?.preds?.length || 0
    if (compareWithTraditional.value) {
      const tradSamples = Object.values(traditionalResultsByModel.value)
        .map((r: any) => r?.preds?.length || deepSamples)
      const minTrad = tradSamples.length > 0 ? Math.min(...tradSamples) : deepSamples
      totalSamples.value = Math.min(deepSamples, minTrad)
    } else {
      totalSamples.value = deepSamples
    }
    sampleIndex.value = 0
    renderChart()
  } finally {
    loading.value = false
  }
}

const renderChart = async () => {
  if (!deepResult.value) return
    
    await nextTick()
    if (!chartRef.value) return
    
    // 只有当实例不存在，或者绑定的 DOM 节点变了（例如重新发起预测导致了组件重建），才重新初始化
    if (!myChart || myChart.getDom() !== chartRef.value) {
        if (myChart) myChart.dispose()
        myChart = echarts.init(chartRef.value)
    }

    const inputData = deepResult.value
    const pred = inputData.preds[sampleIndex.value]
    const true_ = inputData.trues[sampleIndex.value]
    const history = inputData.history ? inputData.history[sampleIndex.value] : []
    const traditionalSeries = compareWithTraditional.value
      ? Object.values(traditionalResultsByModel.value)
      : []
    
    const predLen = pred.length
    const historyLen = history.length
    const dims = pred[0].length
    const requestedDim = getDeepDimToShow()
    const dimToShow = requestedDim !== null && requestedDim < dims ? requestedDim : dims - 1
    
    // Total length for x-axis
    const totalLen = historyLen + predLen
    const xData = Array.from({length: totalLen}, (_, i) => i + 1)
    
    // Prepare series data with nulls for alignment
    const historyDataFull = new Array(totalLen).fill(null)
    const trueDataFull = new Array(totalLen).fill(null)
    const predDataFull = new Array(totalLen).fill(null)
    const traditionalDataFulls: Record<string, any[]> = {}
    
    for(let i=0; i<historyLen; i++) {
        historyDataFull[i] = history[i][dimToShow]
    }
    
    for(let i=0; i<predLen; i++) {
        trueDataFull[historyLen + i] = true_[i][dimToShow]
        predDataFull[historyLen + i] = pred[i][dimToShow]
      }

      if (traditionalSeries.length > 0) {
        traditionalSeries.forEach((r: any) => {
          const pred = r?.preds?.[sampleIndex.value]
          if (!pred) return
          const seriesKey = r.model_name || r.model_type || 'Traditional'
          const seriesData = new Array(totalLen).fill(null)
          const is2D = Array.isArray(pred?.[0])
          const dim = is2D && pred?.[0]?.length ? pred[0].length - 1 : 0
          const usableLen = Math.min(predLen, pred.length)
          for (let i = 0; i < usableLen; i++) {
            seriesData[historyLen + i] = is2D ? pred[i][dim] : pred[i]
          }
          traditionalDataFulls[seriesKey] = seriesData
        })
      }
    
    const option = {
        title: {
            text: `样本 ${sampleIndex.value + 1} - 目标维度预测`
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
          data: compareWithTraditional.value
            ? ['历史数据', '真实值', '深度学习预测', ...Object.keys(traditionalDataFulls)]
            : ['历史数据', '真实值', '深度学习预测']
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: xData
        },
        yAxis: {
            type: 'value',
            scale: true
        },
        series: [
            {
                name: '历史数据',
                type: 'line',
                data: historyDataFull,
                itemStyle: { color: '#999' },
                showSymbol: false,
                lineStyle: { type: 'dashed' }
            },
            {
                name: '真实值',
                type: 'line',
                data: trueDataFull,
                itemStyle: { color: '#91cc75' },
                showSymbol: false
            },
            {
              name: '深度学习预测',
              type: 'line',
              data: predDataFull,
              itemStyle: { color: '#5470c6' },
              showSymbol: false
            },
            ...Object.entries(traditionalDataFulls).map(([name, data], idx) => ({
              name,
              type: 'line',
              data,
              itemStyle: { color: ['#ee6666', '#73c0de', '#fac858', '#9a60b4'][idx % 4] },
              showSymbol: false
            }))
        ]
    }
    
    myChart.setOption(option)
}

watch(sampleIndex, () => {
    renderChart()
})

watch(compareWithTraditional, () => {
  if (!deepResult.value) return
  if (compareWithTraditional.value) {
    const tradSamples = Object.values(traditionalResultsByModel.value)
      .map((r: any) => r?.preds?.length || deepResult.value.preds.length)
    const minTrad = tradSamples.length > 0 ? Math.min(...tradSamples) : deepResult.value.preds.length
    totalSamples.value = Math.min(deepResult.value.preds.length, minTrad)
  } else {
    totalSamples.value = deepResult.value.preds.length
  }
  sampleIndex.value = Math.min(sampleIndex.value, Math.max(0, totalSamples.value - 1))
  renderChart()
})

</script>

<template>
  <div class="space-y-6">
    <!-- 模型类型选择 -->
    <!-- 深度学习模型选项 -->
    <Card>
      <CardHeader>
        <CardTitle>深度学习模型预测</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="flex gap-4 items-end">
          <div class="flex-1 space-y-2">
            <label class="text-sm font-medium">选择已训练模型</label>
            <select 
              v-model="selectedDeepModelId" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-if="!deepModels || deepModels.length === 0" value="" disabled>无</option>
              <option v-for="m in deepModels" :key="m.id" :value="m.id">
                【{{ m.config.filename || m.config.dataset_name }}】{{ m.name }} | 模式:{{ m.config.features }} | 长度:{{ m.config.seq_len }}/{{ m.config.pred_len }} (ID: {{ m.id }})
              </option>
            </select>
          </div>
          <Button
            @click="handlePredict"
            :disabled="loading || !selectedDeepModelId || (compareWithTraditional && (!getCurrentDatasetFile() || !selectedColumn))"
          >
            <Icon v-if="loading" icon="lucide:loader-2" class="animate-spin mr-2" />
            <Icon v-else icon="lucide:play" class="mr-2" />
            开始预测
          </Button>
        </div>
        <div class="mt-4 flex items-center gap-2 text-sm">
          <input v-model="compareWithTraditional" id="compare_traditional" type="checkbox" />
          <label for="compare_traditional" class="font-medium">与传统模型对比</label>
          <span class="text-muted-foreground">开启后可设置传统模型参数并在同一张图中对比</span>
        </div>
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">预测变量</label>
            <select 
              v-model="selectedColumn" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-if="!datasetColumns || datasetColumns.length === 0" value="" disabled>无</option>
              <option v-for="col in datasetColumns" :key="col" :value="col">
                {{ col }}
              </option>
            </select>
          </div>
        </div>
        <div v-if="deepModels.length === 0" class="text-center py-4 text-muted-foreground">
          暂无已完成的训练模型。请先去训练一个模型。
        </div>
      </CardContent>
    </Card>

    <!-- 传统模型选项 -->
    <Card v-if="compareWithTraditional">
      <CardHeader>
        <CardTitle>传统模型配置</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">

        <!-- 针对所有传统模型的高级参数设置 -->
        <div class="p-4 mt-4 bg-muted/50 rounded-lg">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold">模型高级参数</h4>
            <span class="text-xs text-muted-foreground flex items-center">
              <Icon icon="lucide:info" class="mr-1" />
              调整以下参数可改变预测曲线的形状
            </span>
          </div>
          
          <!-- ARIMA 参数 -->
          <div class="space-y-4">
            <div class="text-xs font-semibold">ARIMA</div>
            <div class="text-xs text-muted-foreground mb-2">
              提示: p代表自回归阶数(看近期走势)；d为差分阶数(让数据变平稳)；q为移动平均阶数(消除误差)。若预测是平的，可尝试增大或改变参数。
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="space-y-2">
                <label class="text-xs">AR (p)</label>
                <input v-model.number="modelParams.p" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">Diff (d)</label>
                <input v-model.number="modelParams.d" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">MA (q)</label>
                <input v-model.number="modelParams.q" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
            </div>            
            <div class="space-y-2 mt-4 flex items-center gap-2">
              <input v-model="modelParams.use_seasonal" type="checkbox" id="use_seasonal_arima" />
              <label for="use_seasonal_arima" class="text-xs font-semibold">启用季节性选项 (SARIMA)</label>
            </div>

            <div v-if="modelParams.use_seasonal" class="grid grid-cols-4 gap-4 mt-2 p-3 border rounded-md bg-muted/20">
              <div class="space-y-2">
                <label class="text-xs">P (季节AR)</label>
                <input v-model.number="modelParams.P" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">D (季节I)</label>
                <input v-model.number="modelParams.D" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">Q (季节MA)</label>
                <input v-model.number="modelParams.Q" type="number" min="0" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">s (周期长度)</label>
                <input v-model.number="modelParams.s" type="number" min="2" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
            </div>          </div>

          <!-- Prophet 参数 -->
          <div class="space-y-4 mt-6">
            <div class="text-xs font-semibold">Prophet</div>
             <div class="text-xs text-muted-foreground mb-2">
              提示: 如果数据呈现周期性波动，请勾选对应周期的开关。Additive适合波动幅度稳定的数据，Multiplicative适合波动幅度随数值增大的数据。
            </div>
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div class="space-y-2">
                <label class="text-xs">Seasonality</label>
                <select v-model="modelParams.seasonality_mode" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                  <option value="additive">Additive (加法)</option>
                  <option value="multiplicative">Multiplicative (乘法)</option>
                </select>
              </div>
              <div class="space-y-2 flex items-center pt-6 gap-2">
                <input v-model="modelParams.yearly_seasonality" type="checkbox" id="yearly" />
                <label for="yearly" class="text-xs">Yearly (年度周期)</label>
              </div>
              <div class="space-y-2 flex items-center pt-6 gap-2">
                <input v-model="modelParams.daily_seasonality" type="checkbox" id="daily" />
                <label for="daily" class="text-xs">Daily (日周期)</label>
              </div>
            </div>
          </div>

          <!-- Exponential Smoothing 参数 -->
          <div class="space-y-4 mt-6">
            <div class="text-xs font-semibold">指数平滑</div>
            <div class="text-xs text-muted-foreground mb-2">
              提示: 想要曲线呈现周期性波动，必须设置「Seasonal」为 Add/Mul，并将「Seasonal Periods」设置为数据的循环步长 (例如按小时采样的自然日周期可设为24)。
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="space-y-2">
                <label class="text-xs">Trend (趋势)</label>
                <select v-model="modelParams.trend" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                  <option value="add">Additive (加法)</option>
                  <option value="mul">Multiplicative (乘法)</option>
                  <option value="none">None (无)</option>
                </select>
              </div>
              <div class="space-y-2">
                <label class="text-xs">Seasonal (季节性)</label>
                <select v-model="modelParams.seasonal" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                  <option value="none">None (无季节性)</option>
                  <option value="add">Additive (加法)</option>
                  <option value="mul">Multiplicative (乘法)</option>
                </select>
              </div>
              <div class="space-y-2" v-if="modelParams.seasonal !== 'none'">
                <label class="text-xs">Seasonal Periods (周期长度)</label>
                <input v-model.number="modelParams.seasonal_periods" type="number" min="2" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
            </div>
          </div>

          <!-- Moving Average 参数 -->
          <div class="space-y-4 mt-6">
            <div class="text-xs font-semibold">移动平均</div>
            <div class="text-xs text-muted-foreground mb-2">
              提示: Time Window 指的是取过去多少步的数据来求平均。加权移动平均(Weighted)会赋予距离预测点更近的数据更大的权重。
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="space-y-2">
                <label class="text-xs">Time Window (窗口长度)</label>
                <input v-model.number="modelParams.window" type="number" min="1" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
              <div class="space-y-2">
                <label class="text-xs">MA Type (平均类型)</label>
                <select v-model="modelParams.ma_type" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                  <option value="simple">Simple (简单平均)</option>
                  <option value="weighted">Weighted (加权平均)</option>
                </select>
              </div>
            </div>
          </div>
        </div>
          
        <div v-if="datasetColumns.length === 0" class="text-center py-4 text-muted-foreground">
          未找到可用字段，请确认当前模型的数据集是否存在。
        </div>
      </CardContent>
    </Card>

    <!-- 预测结果展示 -->
    <Card v-if="deepResult">
      <CardHeader>
        <CardTitle class="flex justify-between items-center">
          <span>预测结果对比</span>
          <div class="flex items-center gap-4 text-sm font-normal">
            <span>样本: {{ sampleIndex + 1 }} / {{ totalSamples }}</span>
            <input 
              type="range" 
              min="0" 
              :max="Math.max(0, totalSamples - 1)" 
              v-model.number="sampleIndex"
              class="w-32"
            />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div ref="chartRef" class="w-full h-[400px]"></div>
        <div class="mt-4 space-y-3">
          <div class="flex items-center gap-4 text-sm">
            <span class="font-medium">MAE/MSE 统计范围</span>
            <label class="flex items-center gap-1">
              <input type="radio" value="overall" v-model="metricMode" />
              全部样本
            </label>
            <label class="flex items-center gap-1">
              <input type="radio" value="current" v-model="metricMode" />
              当前样本
            </label>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-sm border-collapse">
              <thead>
                <tr class="text-left border-b">
                  <th class="py-2 pr-4">模型</th>
                  <th class="py-2 pr-4">MAE</th>
                  <th class="py-2 pr-4">MSE</th>
                </tr>
              </thead>
              <tbody>
                <tr class="border-b">
                  <td class="py-2 pr-4">深度学习模型</td>
                  <td class="py-2 pr-4">{{ deepMetrics.mae !== null ? deepMetrics.mae.toFixed(6) : '-' }}</td>
                  <td class="py-2 pr-4">{{ deepMetrics.mse !== null ? deepMetrics.mse.toFixed(6) : '-' }}</td>
                </tr>
                <tr v-if="compareWithTraditional" v-for="m in traditionalMetrics" :key="m.id" class="border-b">
                  <td class="py-2 pr-4">{{ m.name }}</td>
                  <td class="py-2 pr-4">{{ m.mae !== null ? m.mae.toFixed(6) : '-' }}</td>
                  <td class="py-2 pr-4">{{ m.mse !== null ? m.mse.toFixed(6) : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
    
    <Card v-else-if="!loading && deepModels.length > 0">
      <CardContent class="text-center py-10 text-muted-foreground">
        请选择模型并点击"开始预测"按钮。
      </CardContent>
    </Card>
  </div>
</template>
