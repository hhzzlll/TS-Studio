<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { getCompletedModels, getPredictionResult, getTraditionalModels, predictWithTraditionalModel, getDatasets, getDatasetColumns } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'
import * as echarts from 'echarts'

// 模型类型：'deep' 深度学习模型, 'traditional' 传统模型
const modelCategory = ref<'deep' | 'traditional'>('deep')

// 深度学习模型相关
const deepModels = ref<any[]>([])
const selectedDeepModelId = ref<string>('')

// 传统模型相关
const traditionalModels = ref<any[]>([])
const selectedTraditionalModel = ref<string>('arima')
const datasets = ref<any[]>([])
const selectedDataset = ref<string>('')
const datasetColumns = ref<string[]>([])
const selectedColumn = ref<string>('')
const predLen = ref<number>(14)
const seqLen = ref<number>(192)

// 传统模型的高级参数
const modelParams = ref<any>({
  // arima
  p: 1, d: 1, q: 1,
  // prophet
  seasonality_mode: 'additive', yearly_seasonality: false, weekly_seasonality: 'auto', daily_seasonality: true,
  // exp smoothing
  trend: 'add', seasonal: 'none', seasonal_periods: 24,
  // moving average
  window: 20
})

const loading = ref(false)
const resultData = ref<any>(null)
const sampleIndex = ref(0)
const totalSamples = ref(0)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

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
    
    // 加载数据集列表
    const datasetsRes: any = await getDatasets()
    datasets.value = datasetsRes
    if (datasets.value.length > 0) {
      selectedDataset.value = datasets.value[0]
      await fetchColumns()
    }
    
  } catch (e) {
    console.error(e)
  }
  
  window.addEventListener('resize', () => {
    myChart?.resize()
  })
})

const fetchColumns = async () => {
  if(!selectedDataset.value) return
  try {
    const res: any = await getDatasetColumns(selectedDataset.value)
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

watch(selectedDataset, () => {
    fetchColumns()
})

// 切换模型类型
const handleCategoryChange = () => {
  resultData.value = null
  sampleIndex.value = 0
  totalSamples.value = 0
}

// 运行深度学习模型预测
const handleDeepModelPredict = async () => {
    if (!selectedDeepModelId.value) return
    loading.value = true
    try {
        const res: any = await getPredictionResult(Number(selectedDeepModelId.value), 50)
        resultData.value = res
        totalSamples.value = res.preds.length
        sampleIndex.value = 0
        renderChart()
    } catch (e) {
        console.error(e)
        resultData.value = null
    } finally {
        loading.value = false
    }
}

// 运行传统模型预测
const handleTraditionalModelPredict = async () => {
    if (!selectedDataset.value || !selectedTraditionalModel.value || !selectedColumn.value) return
    loading.value = true
    try {
        const res: any = await predictWithTraditionalModel({
            model_type: selectedTraditionalModel.value,
            filename: selectedDataset.value,
            pred_len: predLen.value,
            seq_len: seqLen.value,
            features: 'S',
            target_col: selectedColumn.value,
            limit: 50,
            model_params: modelParams.value
        })
        
        resultData.value = res
        totalSamples.value = res.preds.length
        sampleIndex.value = 0
        renderChart()
    } catch (e) {
        console.error(e)
        resultData.value = null
    } finally {
        loading.value = false
    }
}

// 统一的预测处理
const handlePredict = () => {
  if (modelCategory.value === 'deep') {
    handleDeepModelPredict()
  } else {
    handleTraditionalModelPredict()
  }
}

const renderChart = async () => {
    if (!resultData.value || !chartRef.value) return
    
    await nextTick()
    
    if (!myChart) {
        myChart = echarts.init(chartRef.value)
    }

    const inputData = resultData.value
    const pred = inputData.preds[sampleIndex.value]
    const true_ = inputData.trues[sampleIndex.value]
    // Check if history exists
    const history = inputData.history ? inputData.history[sampleIndex.value] : []
    
    const predLen = pred.length
    const historyLen = history.length
    const dims = pred[0].length
    const dimToShow = dims - 1 
    
    // Total length for x-axis
    const totalLen = historyLen + predLen
    const xData = Array.from({length: totalLen}, (_, i) => i + 1)
    
    // Prepare series data with nulls for alignment
    const historyDataFull = new Array(totalLen).fill(null)
    const trueDataFull = new Array(totalLen).fill(null)
    const predDataFull = new Array(totalLen).fill(null)
    
    for(let i=0; i<historyLen; i++) {
        historyDataFull[i] = history[i][dimToShow]
    }
    
    for(let i=0; i<predLen; i++) {
        trueDataFull[historyLen + i] = true_[i][dimToShow]
        predDataFull[historyLen + i] = pred[i][dimToShow]
        
        // Connect lines visually if history exists
        if (i === 0 && historyLen > 0) {
            // Optional: add last point of history to start of future to connect them?
            // ECharts handles nulls by breaking the line.
            // If we want connected lines, we should duplicate the connection point.
            // But let's keeping it separated is often clearer for "history vs future".
        }
    }
    
    const option = {
        title: {
            text: `样本 ${sampleIndex.value} - 目标维度预测`
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: ['历史数据', '真实值', '预测值']
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
                name: '预测值',
                type: 'line',
                data: predDataFull,
                itemStyle: { color: '#5470c6' },
                showSymbol: false
            }
        ]
    }
    
    myChart.setOption(option)
}

watch(sampleIndex, () => {
    renderChart()
})

</script>

<template>
  <div class="space-y-6">
    <!-- 模型类型选择 -->
    <Card>
      <CardHeader>
        <CardTitle>选择预测模型类型</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="flex gap-4">
          <Button 
            :variant="modelCategory === 'deep' ? 'default' : 'outline'"
            @click="modelCategory = 'deep'; handleCategoryChange()"
            class="flex-1"
          >
            <Icon icon="lucide:brain-circuit" class="mr-2" />
            深度学习模型
          </Button>
          <Button 
            :variant="modelCategory === 'traditional' ? 'default' : 'outline'"
            @click="modelCategory = 'traditional'; handleCategoryChange()"
            class="flex-1"
          >
            <Icon icon="lucide:trending-up" class="mr-2" />
            传统模型
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- 深度学习模型选项 -->
    <Card v-if="modelCategory === 'deep'">
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
              <option v-for="m in deepModels" :key="m.id" :value="m.id">
                【{{ m.config.filename || m.config.dataset_name }}】{{ m.name }} | 模式:{{ m.config.features }} | 长度:{{ m.config.seq_len }}/{{ m.config.pred_len }} (ID: {{ m.id }})
              </option>
            </select>
          </div>
          <Button @click="handlePredict" :disabled="loading || !selectedDeepModelId">
            <Icon v-if="loading" icon="lucide:loader-2" class="animate-spin mr-2" />
            <Icon v-else icon="lucide:play" class="mr-2" />
            开始预测
          </Button>
        </div>
        <div v-if="deepModels.length === 0" class="text-center py-4 text-muted-foreground">
          暂无已完成的训练模型。请先去训练一个模型。
        </div>
      </CardContent>
    </Card>

    <!-- 传统模型选项 -->
    <Card v-if="modelCategory === 'traditional'">
      <CardHeader>
        <CardTitle>传统模型预测</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">选择模型</label>
            <select 
              v-model="selectedTraditionalModel" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-for="m in traditionalModels" :key="m.id" :value="m.id">
                {{ m.name }} - {{ m.description }}
              </option>
            </select>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium">选择数据集</label>
            <select 
              v-model="selectedDataset" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-for="d in datasets" :key="d" :value="d">
                {{ d }}
              </option>
            </select>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium">历史长度</label>
            <input 
              v-model.number="seqLen" 
              type="number" 
              min="24" 
              max="1000"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium">预测长度</label>
            <input 
              v-model.number="predLen" 
              type="number" 
              min="1" 
              max="100"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium">预测变量</label>
            <select 
              v-model="selectedColumn" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option v-for="col in datasetColumns" :key="col" :value="col">
                {{ col }}
              </option>
            </select>
          </div>
        </div>

        <!-- 针对不同传统模型的高级参数设置 -->
        <div class="p-4 mt-4 bg-muted/50 rounded-lg">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold">模型高级参数</h4>
            <span class="text-xs text-muted-foreground flex items-center">
              <Icon icon="lucide:info" class="mr-1" />
              调整以下参数可改变预测曲线的形状
            </span>
          </div>
          
          <!-- ARIMA 参数 -->
          <div v-if="selectedTraditionalModel === 'arima'" class="space-y-4">
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
          </div>

          <!-- Prophet 参数 -->
          <div v-else-if="selectedTraditionalModel === 'prophet'" class="space-y-4">
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
          <div v-else-if="selectedTraditionalModel === 'exponential_smoothing'" class="space-y-4">
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
          <div v-else-if="selectedTraditionalModel === 'moving_average'" class="space-y-4">
            <div class="text-xs text-muted-foreground mb-2">
              提示: Time Window 指的是取过去多少步的数据来求平均值。均值算法通常生成平稳的一条水平直线。
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="space-y-2">
                <label class="text-xs">Time Window (窗口长度)</label>
                <input v-model.number="modelParams.window" type="number" min="1" class="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm" />
              </div>
            </div>
          </div>
        </div>
          
        <div class="flex items-end mt-4">
          <Button @click="handlePredict" :disabled="loading || !selectedDataset || !selectedColumn" class="w-full">
            <Icon v-if="loading" icon="lucide:loader-2" class="animate-spin mr-2" />
            <Icon v-else icon="lucide:play" class="mr-2" />
            开始预测
          </Button>
        </div>
        
        <div v-if="datasets.length === 0" class="text-center py-4 text-muted-foreground">
          暂无可用数据集。请先上传数据。
        </div>
      </CardContent>
    </Card>

    <!-- 预测结果展示 -->
    <Card v-if="resultData">
      <CardHeader>
        <CardTitle class="flex justify-between items-center">
          <span>预测结果对比</span>
          <div class="flex items-center gap-4 text-sm font-normal">
            <span>样本: {{ sampleIndex }} / {{ totalSamples - 1 }}</span>
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
      </CardContent>
    </Card>
    
    <Card v-else-if="!loading && modelCategory === 'deep' && deepModels.length > 0">
      <CardContent class="text-center py-10 text-muted-foreground">
        请选择模型并点击"开始预测"按钮。
      </CardContent>
    </Card>
    
    <Card v-else-if="!loading && modelCategory === 'traditional' && datasets.length > 0">
      <CardContent class="text-center py-10 text-muted-foreground">
        请选择模型和数据集，配置参数后点击"开始预测"按钮。
      </CardContent>
    </Card>
  </div>
</template>
