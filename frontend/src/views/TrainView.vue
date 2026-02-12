<script setup lang="ts">
import { ref, computed, onUnmounted, onMounted, watch, nextTick } from 'vue'
import { startTraining, getTrainingStatus, controlTraining, getActiveTraining, getDatasets, getDatasetInfo } from '../api' 
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'
import * as echarts from 'echarts'

// Define interface for config
interface ConfigForm {
  model_name: string;
  dataset_name: string;
  target: string;
  seq_len: number;
  label_len: number;
  pred_len: number;
  features: string;
  batch_size: number;
  train_epochs: number;
  learning_rate: number;
}

const configForm = ref<ConfigForm>({
  model_name: 'My_Experiment_1',
  dataset_name: '',
  target: 'OT',
  seq_len: 192,
  label_len: 7,
  pred_len: 14,
  features: 'M',
  batch_size: 64,
  train_epochs: 30,
  learning_rate: 0.0006
})

const datasetList = ref<string[]>([])
const datasetColumns = ref<string[]>([])
const datasetPreview = ref<any[]>([])
const isTraining = ref(false)
const trainingJobs = ref<any[]>([])
const activeTab = ref('monitor') // monitor, history
let pollInterval: any = null
let conversionChart: echarts.ECharts | null = null;
const chartRef = ref<HTMLElement | null>(null);

// Mock data for chart visualization (placeholder until backend sends real loss)
const lossData = ref<{epoch: number, loss: number}[]>([])

const initChart = () => {
    if (!chartRef.value) return
    conversionChart = echarts.init(chartRef.value)
    const option = {
        title: { text: 'Training Loss', left: 'center', textStyle: { fontSize: 14, color: '#666' } },
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: [] },
        yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
        series: [{
            name: 'Loss',
            type: 'line',
            smooth: true,
            data: [],
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(59, 130, 246, 0.5)' },
                    { offset: 1, color: 'rgba(59, 130, 246, 0.0)' }
                ])
            },
            itemStyle: { color: '#3b82f6' }
        }]
    }
    conversionChart.setOption(option)
}

const updateChart = () => {
    if (!conversionChart) return
    // In a real scenario, we would parse loss history from job.metrics or job.log
    // For now, we just clear it or show dummy data if running
    conversionChart.setOption({
        xAxis: { data: lossData.value.map(d => d.epoch) },
        series: [{ data: lossData.value.map(d => d.loss) }]
    })
}

// Watch for active tab to resize chart
watch(activeTab, async (val) => {
    if (val === 'monitor') {
        await nextTick()
        if (!conversionChart) initChart()
        else conversionChart.resize()
    }
})

// Window resize handler
window.addEventListener('resize', () => {
    conversionChart?.resize()
})

const getStatusText = (job: any) => {
    if (job.status === 'running' && job.metrics && job.metrics.stage) {
        return job.metrics.stage.toUpperCase()
    }
    return job.status.toUpperCase()
}

const getStatusColor = (job: any) => {
  const map: Record<string, string> = {
    'pending': 'text-amber-500 bg-amber-50 dark:bg-amber-950/30',
    'running': 'text-blue-500 bg-blue-50 dark:bg-blue-950/30',
    'paused': 'text-orange-500 bg-orange-50 dark:bg-orange-950/30',
    'completed': 'text-green-500 bg-green-50 dark:bg-green-950/30',
    'failed': 'text-red-500 bg-red-50 dark:bg-red-950/30',
    'cancelled': 'text-gray-500 bg-gray-50 dark:bg-gray-950/30'
  }
  return map[job.status] || 'text-gray-500 bg-gray-50'
}

const getProgress = (job: any) => {
    if (!job.metrics) return 0
    const { current_epoch, total_epochs } = job.metrics
    if (!total_epochs) return 0
    return Math.round((current_epoch / total_epochs) * 100)
}

const getEpochInfo = (job: any) => {
    if (!job.metrics) return '-'
    const { current_epoch, total_epochs, stage } = job.metrics
    return `${stage || 'Init'} - ${current_epoch || 0} / ${total_epochs || 0}`
}

const handleDatasetChange = async () => {
    if (!configForm.value.dataset_name) return
    
    try {
        const res: any = await getDatasetInfo(configForm.value.dataset_name)
        datasetColumns.value = res.columns
        datasetPreview.value = res.preview
        
        // Auto-select OT if available, otherwise first column
        if (!datasetColumns.value.includes(configForm.value.target)) {
             configForm.value.target = datasetColumns.value.includes('OT') ? 'OT' : datasetColumns.value[datasetColumns.value.length - 1]
        }
    } catch (e) {
        console.error(e)
    }
}

const handleTrain = async () => {
    if (!configForm.value.dataset_name) {
        alert("请选择数据集")
        return
    }

    isTraining.value = true
    try {
        const payload: any = { ...configForm.value }
        // For custom uploaded datasets
        payload.filename = configForm.value.dataset_name 
        payload.data_path = configForm.value.dataset_name
        
        // Remove file extension for dataset_name (e.g. Exchange.csv -> Exchange)
        // This ensures it matches the keys in data_factory.py if it's a standard dataset
        payload.dataset_name = configForm.value.dataset_name.replace(/\.[^/.]+$/, "")

        // Ensure MS/S mode has target
        if (payload.features !== 'M' && !payload.target) {
            alert("请选择预测目标列 (Target)")
            isTraining.value = false
            return
        }

        const res: any = await startTraining(payload)
        trainingJobs.value.unshift(res)
        // Reset loss data for new job
        lossData.value = [] 
        activeTab.value = 'monitor'
        startPolling()
    } catch (e) {
        console.error(e)
    } finally {
        isTraining.value = false
    }
}

const handleControl = async (job: any, action: 'pause' | 'resume' | 'stop') => {
    try {
        await controlTraining(job.id, action)
        // Force refresh just this job
        const res: any = await getTrainingStatus(job.id)
        updateJobInList(res)
    } catch (e) {
        console.error(e)
    }
}

const updateJobInList = (updatedJob: any) => {
    const index = trainingJobs.value.findIndex(j => j.id === updatedJob.id)
    if (index !== -1) {
        trainingJobs.value[index] = updatedJob
    } else {
        trainingJobs.value.unshift(updatedJob)
    }
}

const startPolling = () => {
    if (pollInterval) clearInterval(pollInterval)
    
    const poll = async () => {
        // Only poll jobs that are not in final state
        const activeJobIds = trainingJobs.value
            .filter(j => ['pending', 'running', 'paused'].includes(j.status))
            .map(j => j.id)

        if (activeJobIds.length === 0) return

        for (const id of activeJobIds) {
             try {
                const res: any = await getTrainingStatus(id)
                updateJobInList(res)
            } catch(e) {}
        }
    }

    poll() // Run once immediately
    pollInterval = setInterval(poll, 2000)
}

onMounted(async () => {
    try {
        console.log("Fetching datasets...")
        // Load datasets
        const files: any = await getDatasets()
        console.log("Datasets fetched:", files)
        
        if (Array.isArray(files)) {
            datasetList.value = files
        } else {
            console.error("Expected array of datasets, got:", files)
            datasetList.value = []
        }
        
        // Pre-select if local storage has one, or default to first
        const lastFile = localStorage.getItem('dataset_filename')
        if (lastFile && datasetList.value.includes(lastFile)) {
            configForm.value.dataset_name = lastFile
        } else if (datasetList.value.length > 0) {
            configForm.value.dataset_name = datasetList.value[0]
        }
        
        if (configForm.value.dataset_name) {
            handleDatasetChange()
        }

        const activeJobs: any = await getActiveTraining()
        if (Array.isArray(activeJobs) && activeJobs.length > 0) {
            console.log("Found active jobs:", activeJobs.length)
            trainingJobs.value = activeJobs
            startPolling()
        }
        
        // Initialize chart
        initChart()
    } catch (e) {
        console.error("Error in onMounted:", e)
    }
})

onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval)
    conversionChart?.dispose()
})
</script>

<template>
  <div class="h-full flex flex-col gap-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">模型训练</h2>
        <p class="text-muted-foreground">配置并启动 Diffusion 时序预测模型的训练任务。</p>
      </div>
      <div class="flex items-center gap-2">
         <Button variant="outline">
            <Icon icon="lucide:book-open" class="mr-2 h-4 w-4" /> 算法文档
         </Button>
      </div>
    </div>

    <div class="flex flex-col gap-6 h-full overflow-y-auto pb-6 pr-2">
      
      <!-- Top Panel: Configuration -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 shrink-0">
        
        <!-- Task & Data Card -->
        <Card class="h-full">
            <CardHeader class="pb-3">
                <CardTitle class="text-lg flex items-center gap-2">
                    <Icon icon="lucide:database" class="text-primary" /> 数据任务
                </CardTitle>
            </CardHeader>
            <CardContent>
               <div class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-sm font-medium">任务名称</label>
                    <input v-model="configForm.model_name" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring" placeholder="实验名称..." />
                  </div>
                  <div class="space-y-2">
                    <label class="text-sm font-medium">数据集</label>
                    <select 
                       v-model="configForm.dataset_name" 
                       @change="handleDatasetChange"
                       class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                        <option v-for="name in datasetList" :key="name" :value="name">{{ name }}</option>
                    </select>
                  </div>
                  
                  <div v-if="datasetPreview.length > 0" class="rounded-md border bg-muted/40 p-2">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-semibold text-muted-foreground">数据预览 top-5</span>
                            <span class="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{{ configForm.dataset_name }}</span>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-xs text-left">
                                <thead>
                                    <tr class="border-b border-border/50">
                                        <th v-for="col in datasetColumns.slice(0, 4)" :key="col" class="px-2 py-1 whitespace-nowrap text-muted-foreground font-normal">{{ col }}</th>
                                        <th v-if="datasetColumns.length > 4" class="px-2 py-1 text-muted-foreground">...</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(row, i) in datasetPreview" :key="i" class="border-b border-border/50 last:border-0 hover:bg-muted/50">
                                        <td v-for="col in datasetColumns.slice(0, 4)" :key="col" class="px-2 py-1 whitespace-nowrap font-mono">{{ typeof row[col] === 'number' ? row[col].toFixed(2) : row[col] }}</td>
                                        <td v-if="datasetColumns.length > 4" class="px-2 py-1">...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                  </div>
               </div>
            </CardContent>
        </Card>

        <!-- Model Params -->
         <Card class="h-full">
            <CardHeader class="pb-3">
                <CardTitle class="text-lg flex items-center gap-2">
                    <Icon icon="lucide:sliders-horizontal" class="text-primary" /> 参数配置
                </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-6">
                  
                  <div class="space-y-4">
                      <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b pb-1">模型结构</div>
                      <div class="grid grid-cols-2 gap-4">
                          <div class="space-y-2">
                            <label class="text-xs font-medium text-muted-foreground">Seq Length (输入)</label>
                            <input type="number" v-model.number="configForm.seq_len" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                          </div>
                          <div class="space-y-2">
                            <label class="text-xs font-medium text-muted-foreground">Pred Length (输出)</label>
                            <input type="number" v-model.number="configForm.pred_len" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                          </div>
                      </div>
                      
                      <div class="grid grid-cols-2 gap-4">
                          <div class="space-y-2">
                              <label class="text-xs font-medium text-muted-foreground">Label Len</label>
                              <input type="number" v-model.number="configForm.label_len" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                          </div>
                          <div class="space-y-2">
                              <label class="text-xs font-medium text-muted-foreground">Features</label>
                              <select v-model="configForm.features" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                                  <option value="M">M (多对多)</option>
                                  <option value="S">S (单对单)</option>
                                  <option value="MS">MS (多对单)</option>
                              </select>
                          </div>
                      </div>

                      <div class="space-y-2" v-if="configForm.features !== 'M'">
                         <label class="text-xs font-medium text-blue-600">Target Column</label>
                         <select v-model="configForm.target" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                             <option v-for="col in datasetColumns" :key="col" :value="col">{{ col }}</option>
                         </select>
                      </div>
                  </div>

                  <div class="space-y-4">
                      <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b pb-1">训练超参</div>
                      <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-2">
                            <label class="text-xs font-medium text-muted-foreground">Total Epochs</label>
                            <input type="number" v-model.number="configForm.train_epochs" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                        </div>
                         <div class="space-y-2">
                            <label class="text-xs font-medium text-muted-foreground">Batch Size</label>
                            <input type="number" v-model.number="configForm.batch_size" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                        </div>
                        <div class="space-y-2 col-span-2">
                            <label class="text-xs font-medium text-muted-foreground">Learning Rate</label>
                            <input type="number" step="0.0001" v-model.number="configForm.learning_rate" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm" />
                        </div>
                      </div>
                  </div>
              
                  <div class="pt-4">
                    <Button class="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg transition-all" @click="handleTrain" :disabled="isTraining">
                        <Icon v-if="isTraining" icon="lucide:loader-2" class="mr-2 h-4 w-4 animate-spin" />
                        {{ isTraining ? '初始化并开始训练' : '开始训练任务' }}
                    </Button>
                  </div>
              </div>
            </CardContent>
        </Card>

      </div>
      
      <!-- Bottom Panel: Monitoring & History -->
      <div class="flex flex-col gap-6">
        
        <!-- Tabs -->
        <div class="flex items-center space-x-1 border-b">
            <button 
                @click="activeTab = 'monitor'" 
                :class="['px-4 py-2 text-sm font-medium border-b-2 transition-colors', activeTab === 'monitor' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
            >
                实时监控
            </button>
            <button 
                @click="activeTab = 'history'" 
                :class="['px-4 py-2 text-sm font-medium border-b-2 transition-colors', activeTab === 'history' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
            >
                历史任务
            </button>
        </div>

        <!-- Monitor View -->
        <div v-show="activeTab === 'monitor'" class="space-y-6">
            <template v-if="trainingJobs.length > 0">
                <!-- Active Job Status Card -->
                <Card class="border-l-4 border-l-primary shadow-sm bg-gradient-to-r from-background to-muted/20">
                    <CardContent class="p-6">
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <h3 class="text-xl font-bold flex items-center gap-2">
                                    {{ trainingJobs[0].name }}
                                </h3>
                                <div class="text-sm text-muted-foreground mt-1 font-mono text-xs">ID: {{ trainingJobs[0].id }}</div>
                            </div>
                            <span :class="getStatusColor(trainingJobs[0])" class="px-3 py-1 rounded-full text-xs font-bold border">
                                {{ getStatusText(trainingJobs[0]) }}
                            </span>
                        </div>
                        
                        <!-- Progress Metrics -->
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                             <div class="bg-background rounded-lg p-3 border shadow-sm">
                                 <div class="text-xs text-muted-foreground">Dataset</div>
                                 <div class="font-semibold text-sm truncate" :title="trainingJobs[0].config.filename">{{ trainingJobs[0].config.filename }}</div>
                             </div>
                             <div class="bg-background rounded-lg p-3 border shadow-sm">
                                 <div class="text-xs text-muted-foreground">Epochs</div>
                                 <div class="font-semibold text-sm">{{ getEpochInfo(trainingJobs[0]) }}</div>
                             </div>
                             <div class="bg-background rounded-lg p-3 border shadow-sm">
                                 <div class="text-xs text-muted-foreground">Batch Size</div>
                                 <div class="font-semibold text-sm">{{ trainingJobs[0].config.batch_size }}</div>
                             </div>
                             <div class="bg-background rounded-lg p-3 border shadow-sm">
                                 <div class="text-xs text-muted-foreground">Process</div>
                                 <div class="font-semibold text-sm">{{ trainingJobs[0].status }}</div>
                             </div>
                        </div>

                        <!-- Progress Bar -->
                        <div class="space-y-1.5">
                            <div class="flex justify-between text-xs">
                                <span class="text-muted-foreground">Overall Progress</span>
                                <span class="font-medium">{{ getProgress(trainingJobs[0]) }}%</span>
                            </div>
                            <div class="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                <div class="h-full bg-primary transition-all duration-1000 ease-out" :style="{ width: getProgress(trainingJobs[0]) + '%' }"></div>
                            </div>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="flex gap-2 justify-end mt-4">
                            <Button variant="outline" size="sm" @click="handleControl(trainingJobs[0], 'pause')" v-if="trainingJobs[0].status === 'running'">
                                <Icon icon="lucide:pause" class="mr-2 h-4 w-4" /> 暂停训练
                            </Button>
                             <Button variant="outline" size="sm" @click="handleControl(trainingJobs[0], 'resume')" v-if="trainingJobs[0].status === 'paused'">
                                <Icon icon="lucide:play" class="mr-2 h-4 w-4" /> 继续训练
                            </Button>
                            <Button variant="destructive" size="sm" @click="handleControl(trainingJobs[0], 'stop')" v-if="['running', 'paused'].includes(trainingJobs[0].status)">
                                <Icon icon="lucide:square" class="mr-2 h-4 w-4" /> 终止任务
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                <!-- Chart & Logs -->
                <div class="grid grid-cols-1 gap-6">
                    <Card class="col-span-1">
                         <CardHeader class="pb-2">
                            <CardTitle class="text-base font-medium">Loss 趋势监控</CardTitle>
                        </CardHeader>
                        <CardContent>
                             <div ref="chartRef" class="w-full h-64 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-dashed flex items-center justify-center relative">
                                <!-- Chart will be rendered here -->
                             </div>
                        </CardContent>
                    </Card>

                    <Card class="flex-1 flex flex-col min-h-[200px]">
                        <CardHeader class="pb-2 bg-slate-950 text-slate-100 rounded-t-lg">
                            <CardTitle class="text-base font-mono flex items-center gap-2 text-xs">
                                <Icon icon="lucide:terminal" /> Terminal Output
                            </CardTitle>
                        </CardHeader>
                        <CardContent class="flex-1 p-0">
                            <div class="bg-slate-950 text-slate-300 font-mono text-xs p-4 h-full min-h-[200px] max-h-[300px] overflow-auto whitespace-pre-wrap rounded-b-lg">
                                <div v-if="trainingJobs[0].log">{{ trainingJobs[0].log }}</div>
                                <div v-else class="opacity-50 italic">Waiting for logs...</div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

            </template>
            <div v-else class="h-64 flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg bg-muted/20">
                <Icon icon="lucide:activity" class="h-12 w-12 mb-4 opacity-20" />
                <p>暂无正在进行的训练任务</p>
                <p class="text-sm">请在左侧配置并启动一个新的实验</p>
            </div>
        </div>

        <!-- History View -->
        <div v-show="activeTab === 'history'" class="space-y-4">
             <div v-if="trainingJobs.length === 0" class="text-center py-10 text-muted-foreground">无需历史记录</div>
             <Card v-for="job in trainingJobs.slice(1)" :key="job.id" class="hover:bg-muted/30 transition-colors">
                <CardContent class="p-4 flex items-center justify-between">
                    <div>
                        <div class="font-medium">{{ job.name }}</div>
                        <div class="text-xs text-muted-foreground flex gap-3 mt-1">
                            <span class="font-mono">{{ job.id.substring(0,8) }}...</span>
                            <span>{{ new Date(job.created_at).toLocaleString() }}</span>
                            <span class="font-mono border px-1 rounded">{{ job.config.dataset_name }}</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <span :class="getStatusColor(job)" class="px-2 py-0.5 rounded text-xs font-bold">{{ getStatusText(job) }}</span>
                        <Button variant="ghost" size="icon">
                             <Icon icon="lucide:chevron-right" class="h-4 w-4" />
                        </Button>
                    </div>
                </CardContent>
             </Card>
        </div>

      </div>
    </div>
  </div>
</template>
