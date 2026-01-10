<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { getCompletedModels, getPredictionResult } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'
import * as echarts from 'echarts'

const models = ref<any[]>([])
const selectedModelId = ref<string>('')
const loading = ref(false)
const resultData = ref<any>(null)
const sampleIndex = ref(0)
const totalSamples = ref(0)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

onMounted(async () => {
  try {
    const res: any = await getCompletedModels()
    models.value = res
    if (models.value.length > 0) {
      selectedModelId.value = models.value[0].id
      handleModelChange()
    }
  } catch (e) {
    console.error(e)
  }
  
  window.addEventListener('resize', () => {
    myChart?.resize()
  })
})

const handleModelChange = async () => {
    if (!selectedModelId.value) return
    loading.value = true
    try {
        const res: any = await getPredictionResult(Number(selectedModelId.value), 50) // fetch 50 samples
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

const renderChart = async () => {
    if (!resultData.value || !chartRef.value) return
    
    await nextTick()
    
    if (!myChart) {
        myChart = echarts.init(chartRef.value)
    }

    const inputData = resultData.value
    const pred = inputData.preds[sampleIndex.value] // [PredLen, Dims]
    const true_ = inputData.trues[sampleIndex.value] // [PredLen, Dims]
    
    const predLen = pred.length
    const dims = pred[0].length
    
    // Construct series
    // If multiple dims, we can show multiple lines or just the last dim (usually target) 
    // or provide control. For now, let's show Dim 0 (or Target if we knew which one)
    // Actually, usually the last column is target in 'S' or 'MS' mode.
    // In 'M' mode, all are targets.
    // Let's visualize the LAST dimension by default as it's often the target (OT)
    
    const dimToShow = dims - 1 
    
    const xData = Array.from({length: predLen}, (_, i) => i + 1)
    
    const option = {
        title: {
            text: `Sample ${sampleIndex.value} - Target Dimension`
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: ['Ground Truth', 'Prediction']
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
                name: 'Ground Truth',
                type: 'line',
                data: true_.map((row: any) => row[dimToShow]),
                itemStyle: { color: '#91cc75' }
            },
            {
                name: 'Prediction',
                type: 'line',
                data: pred.map((row: any) => row[dimToShow]),
                itemStyle: { color: '#5470c6' }
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
     <div class="flex gap-4 items-end">
        <div class="w-64 space-y-2">
            <label class="text-sm font-medium">选择已训练模型</label>
            <select v-model="selectedModelId" @change="handleModelChange" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                 <option v-for="m in models" :key="m.id" :value="m.id">
                    【{{ m.config.filename || m.config.dataset_name }}】{{ m.name }} | 模式:{{ m.config.features }} | 长度:{{ m.config.seq_len }}/{{ m.config.pred_len }} (ID: {{ m.id }})
                 </option>
            </select>
        </div>
        <Button variant="outline" @click="handleModelChange" :disabled="loading">
             <Icon v-if="loading" icon="lucide:loader-2" class="animate-spin mr-2" />
             刷新
        </Button>
     </div>

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
     
     <Card v-else-if="!loading && models.length > 0">
         <CardContent class="text-center py-10 text-muted-foreground">
             无法加载预测数据，可能该模型已被删除或未生成结果文件。
         </CardContent>
     </Card>
      <Card v-else-if="!loading && models.length === 0">
         <CardContent class="text-center py-10 text-muted-foreground">
             暂无已完成的训练模型。请先去训练一个模型。
         </CardContent>
     </Card>
  </div>
</template>
