<script setup lang="ts">
import { ref, computed, onUnmounted, onMounted, watch } from 'vue'
import { startTraining, getTrainingStatus, controlTraining, getActiveTraining, getDatasets, getDatasetInfo } from '../api' 
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

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
let pollInterval: any = null

const getStatusColor = (job: any) => {
  const map: Record<string, string> = {
    'pending': 'text-yellow-500',
    'running': 'text-blue-500',
    'paused': 'text-orange-500',
    'completed': 'text-green-500',
    'failed': 'text-red-500',
    'cancelled': 'text-gray-500'
  }
  return map[job.status] || 'text-gray-500'
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
    } catch (e) {
        console.error("Error in onMounted:", e)
    }
})

onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>模型参数配置</CardTitle>
        </CardHeader>
        <CardContent>
          <form class="space-y-4" @submit.prevent>
            <div class="space-y-2">
              <label class="text-sm font-medium">任务名称</label>
              <input v-model="configForm.model_name" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium">数据集 (Backend/Data)</label>
              <select 
                 v-model="configForm.dataset_name" 
                 @change="handleDatasetChange"
                 class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                  <option v-for="name in datasetList" :key="name" :value="name">{{ name }}</option>
              </select>
            </div>

            <div v-if="datasetPreview.length > 0" class="border rounded-md p-2 bg-slate-50 dark:bg-slate-900 overflow-x-auto">
                <div class="text-xs text-muted-foreground mb-2">数据预览 ({{ configForm.dataset_name }})</div>
                <table class="w-full text-xs text-left">
                     <thead>
                        <tr class="border-b">
                            <th v-for="col in datasetColumns" :key="col" class="px-2 py-1 font-medium whitespace-nowrap">{{ col }}</th>
                        </tr>
                     </thead>
                      <tbody>
                        <tr v-for="(row, i) in datasetPreview" :key="i" class="border-b last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800">
                             <td v-for="col in datasetColumns" :key="col" class="px-2 py-1 whitespace-nowrap">{{ row[col] }}</td>
                        </tr>
                     </tbody>
                </table>
            </div>

            <div class="grid grid-cols-2 gap-4">
               <div class="space-y-2">
                <label class="text-sm font-medium">Seq Len</label>
                <input type="number" v-model.number="configForm.seq_len" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium">Pred Len</label>
                <input type="number" v-model.number="configForm.pred_len" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </div>
            </div>
            
            <div class="space-y-2">
                <label class="text-sm font-medium">预测模式</label>
                <select v-model="configForm.features" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option value="M">M (多变量预测多变量)</option>
                    <option value="S">S (单变量预测单变量)</option>
                    <option value="MS">MS (多变量预测单变量)</option>
                </select>
            </div>

            <div class="space-y-2" v-if="configForm.features !== 'M'">
               <label class="text-sm font-medium text-blue-600">预测目标列 (Target)</label>
               <select v-model="configForm.target" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                   <option v-for="col in datasetColumns" :key="col" :value="col">{{ col }}</option>
               </select>
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                    <label class="text-sm font-medium">Epochs</label>
                    <input type="number" v-model.number="configForm.train_epochs" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
                </div>
                 <div class="space-y-2">
                    <label class="text-sm font-medium">Batch Size</label>
                    <input type="number" v-model.number="configForm.batch_size" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
                </div>
            </div>

            <div class="pt-4">
                <Button class="w-full" @click="handleTrain" :disabled="isTraining">
                    <Icon v-if="isTraining" icon="lucide:loader-2" class="mr-2 h-4 w-4 animate-spin" />
                    {{ isTraining ? '训练中...' : '开始训练' }}
                </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
    
    <div class="space-y-6">
      <Card v-for="job in trainingJobs" :key="job.id">
        <CardHeader>
          <CardTitle class="flex items-center justify-between">
              <span>训练状态</span>
              <span :class="getStatusColor(job)" class="uppercase text-sm font-bold">{{ job.status }}</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
           <div class="space-y-4">
               <div class="grid grid-cols-2 gap-4 text-sm">
                    <div class="flex justify-between">
                        <span class="text-muted-foreground">Job ID:</span>
                        <span class="font-mono">{{ job.id }}</span>
                    </div>
                     <div class="flex justify-between">
                        <span class="text-muted-foreground">Name:</span>
                        <span>{{ job.name }}</span>
                    </div>
                     <div class="flex justify-between">
                        <span class="text-muted-foreground">Dataset:</span>
                        <span class="font-mono">{{ job.config.filename || job.config.dataset_name }}</span>
                    </div>
                     <div class="flex justify-between">
                        <span class="text-muted-foreground">Mode:</span>
                        <span class="font-mono">{{ job.config.features }}</span>
                    </div>
                     <div class="flex justify-between">
                        <span class="text-muted-foreground">Seq / Pred:</span>
                        <span class="font-mono">{{ job.config.seq_len }} / {{ job.config.pred_len }}</span>
                    </div>
                     <div class="flex justify-between">
                        <span class="text-muted-foreground">Created At:</span>
                        <span>{{ new Date(job.created_at).toLocaleString() }}</span>
                    </div>
                    <div class="flex justify-between border-t pt-2 col-span-2">
                         <span class="text-muted-foreground">Progress:</span>
                         <span class="font-mono font-bold">{{ getEpochInfo(job) }}</span>
                    </div>
               </div>

                <!-- Simple Progress Bar -->
                <div class="w-full bg-secondary h-2 rounded-full overflow-hidden" v-if="['running', 'paused'].includes(job.status)">
                    <div class="bg-primary h-full transition-all duration-500" :style="{ width: getProgress(job) + '%' }"></div>
                </div>

                <!-- Controls -->
                <div class="flex gap-2 justify-end pt-2" v-if="['running', 'paused'].includes(job.status)">
                    <Button variant="outline" size="sm" @click="handleControl(job, 'pause')" v-if="job.status === 'running'">
                        <Icon icon="lucide:pause" class="mr-2 h-4 w-4" /> 暂停
                    </Button>
                     <Button variant="outline" size="sm" @click="handleControl(job, 'resume')" v-if="job.status === 'paused'">
                        <Icon icon="lucide:play" class="mr-2 h-4 w-4" /> 继续
                    </Button>
                    <Button variant="destructive" size="sm" @click="handleControl(job, 'stop')">
                        <Icon icon="lucide:square" class="mr-2 h-4 w-4" /> 停止
                    </Button>
                </div>
           
                <div v-if="job.log" class="mt-4 p-3 bg-red-50 text-red-600 rounded text-xs font-mono overflow-auto max-h-48 border border-red-100">
                    {{ job.log }}
                </div>
           </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
