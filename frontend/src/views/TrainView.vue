<script setup lang="ts">
import { ref, computed, onUnmounted, onMounted } from 'vue'
import { startTraining, getTrainingStatus, controlTraining, getActiveTraining } from '../api' 
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

// Define interface for config
interface ConfigForm {
  model_name: string;
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
  seq_len: 192,
  label_len: 7,
  pred_len: 14,
  features: 'M',
  batch_size: 64,
  train_epochs: 30,
  learning_rate: 0.0006
})

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

const handleTrain = async () => {
    isTraining.value = true
    try {
        const filename = localStorage.getItem('dataset_filename')
        const payload: any = { ...configForm.value }
        if (filename) {
            payload.filename = filename 
            payload.dataset_name = 'custom' 
            payload.data_path = filename
        }

        const res: any = await startTraining(payload)
        // Add new job to the top of the list
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
        const activeJobs: any = await getActiveTraining()
        if (Array.isArray(activeJobs) && activeJobs.length > 0) {
            console.log("Found active jobs:", activeJobs.length)
            trainingJobs.value = activeJobs
            startPolling()
        }
    } catch (e) {
        console.log("No active jobs found or error checking")
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
                <label class="text-sm font-medium">特征模式</label>
                <select v-model="configForm.features" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option value="M">M (多变量)</option>
                    <option value="S">S (单变量)</option>
                    <option value="MS">MS (多对单)</option>
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
                        <span class="text-muted-foreground">Created At:</span>
                        <span>{{ new Date(job.created_at).toLocaleString() }}</span>
                    </div>
                    <div class="flex justify-between border-t pt-2">
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
