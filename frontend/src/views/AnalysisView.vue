<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { getDatasets, getDatasetAnalysis, getDatasetInfo, getColumnAnalysis } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'
import * as echarts from 'echarts'

const datasetList = ref<string[]>([])
const selectedDataset = ref('')
const isLoading = ref(false)
const errorMsg = ref('')

// General Analysis
const analysisResult = ref<any>(null)

// Column Analysis
const columns = ref<string[]>([])
const selectedColumn = ref('')
const isColumnLoading = ref(false)
const columnResult = ref<any>(null)
const columnErrorMsg = ref('')
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

// Advanced Analysis Charts
const diffChartRef = ref<HTMLElement | null>(null)
const fftChartRef = ref<HTMLElement | null>(null)
let diffChart: echarts.ECharts | null = null
let fftChart: echarts.ECharts | null = null

onMounted(async () => {
    window.addEventListener('resize', handleResize)
    try {
        const files: any = await getDatasets()
        datasetList.value = files
        if (files.length > 0) {
            selectedDataset.value = files[0]
            handleDatasetChange()
        }
    } catch (e) {
        console.error(e)
    }
})

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    myChart?.dispose()
    diffChart?.dispose()
    fftChart?.dispose()
})

const handleResize = () => {
    myChart?.resize()
    diffChart?.resize()
    fftChart?.resize()
}

const handleDatasetChange = async () => {
    columns.value = []
    selectedColumn.value = ''
    analysisResult.value = null
    columnResult.value = null
    
    if (!selectedDataset.value) return
    
    try {
        const res: any = await getDatasetInfo(selectedDataset.value)
        columns.value = res.columns
        if (res.columns.length > 0) {
             selectedColumn.value = res.columns.length > 1 ? res.columns[res.columns.length - 1] : res.columns[0]
        }
    } catch (e) {
        console.error(e)
    }
}

const handleAnalyze = async () => {
    if (!selectedDataset.value) return
    
    isLoading.value = true
    errorMsg.value = ''
    analysisResult.value = null
    
    try {
        const res: any = await getDatasetAnalysis(selectedDataset.value)
        analysisResult.value = res
    } catch (e: any) {
        console.error(e)
        errorMsg.value = e.message || "分析失败"
    } finally {
        isLoading.value = false
    }
}

const handleColumnAnalyze = async () => {
    if (!selectedDataset.value || !selectedColumn.value) return
    
    isColumnLoading.value = true
    columnErrorMsg.value = ''
    columnResult.value = null
    
    try {
        const res: any = await getColumnAnalysis(selectedDataset.value, selectedColumn.value)
        columnResult.value = res
        
        await nextTick()
        renderChart(res)
        renderDiffChart(res)
        renderFFTChart(res)
    } catch (e: any) {
        console.error(e)
        columnErrorMsg.value = e.message || "列分析失败"
    } finally {
        isColumnLoading.value = false
    }
}


const renderDiffChart = (data: any) => {
    if (!diffChartRef.value) return
    const existing = echarts.getInstanceByDom(diffChartRef.value)
    if (existing) existing.dispose()
    
    diffChart = echarts.init(diffChartRef.value)
    
    const option = {
        title: {
            text: 'First Order Difference (1阶差分)',
            left: 'center',
            textStyle: { fontSize: 13 }
        },
        tooltip: {
            trigger: 'axis'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: data.labels, // Should ideally shift by 1 but visualize align is ok
            show: false 
        },
        yAxis: {
            type: 'value',
            scale: true
        },
        series: [{
            name: 'Difference',
            type: 'line',
            data: data.diff_values,
            showSymbol: false,
            sampling: 'lttb',
            lineStyle: { width: 1, color: '#9a60b4' },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(154, 96, 180, 0.5)' },
                    { offset: 1, color: 'rgba(154, 96, 180, 0.01)' }
                ])
            }
        }]
    }
    
    diffChart.setOption(option)
}

const renderFFTChart = (data: any) => {
    if (!fftChartRef.value) return
    const existing = echarts.getInstanceByDom(fftChartRef.value)
    if (existing) existing.dispose()
    
    fftChart = echarts.init(fftChartRef.value)
    
    const option = {
        title: {
            text: 'Frequency Domain Analysis (Spectrum)',
            left: 'center',
            textStyle: { fontSize: 13 }
        },
        tooltip: {
            trigger: 'axis',
            formatter: (params: any) => {
                const p = params[0]
                const freq = p.data[0]
                const mag = p.data[1]
                const period = freq > 0 ? (1/freq).toFixed(2) : 'Inf'
                return `Freq: ${freq.toFixed(4)}<br/>Period (T): ${period}<br/>Amplitude: ${mag.toFixed(4)}`
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            name: 'Frequency',
            nameLocation: 'middle',
            nameGap: 25
        },
        yAxis: {
            type: 'value',
            name: 'Amplitude'
        },
        series: [{
            name: 'Spectrum',
            type: 'line',
            // Zip freq and mag
            data: data.fft_freqs.map((e: any, i: any) => [e, data.fft_mags[i]]),
            showSymbol: false,
            sampling: 'lttb',
            lineStyle: { width: 1.5, color: '#e7bc29' },
            itemStyle: { color: '#e7bc29' },
             markPoint: {
                symbolSize: 20,
                label: { show: false },
                data: [
                    { type: 'max', name: 'Dominant Freq' }
                ]
            }
        }]
    }
    
    fftChart.setOption(option)
}

const renderChart = (data: any) => {
    if (!chartRef.value) return
    
    // 关键修复：确保销毁 DOM 上可能存在的旧实例（包括僵尸实例）
    const existingInstance = echarts.getInstanceByDom(chartRef.value)
    if (existingInstance) {
        existingInstance.dispose()
    }
    // 双重保险：如果有 JS 变量引用，也销毁
    if (myChart) {
        myChart.dispose()
    }

    myChart = echarts.init(chartRef.value)
    
    const option = {
        animation: false,
        title: [
            { text: 'Observed (Original) with Anomalies', left: 'center', top: '2%', textStyle: { fontSize: 12 } },
            { text: 'Trend', left: 'center', top: '27%', textStyle: { fontSize: 12 } },
            { text: 'Seasonal', left: 'center', top: '52%', textStyle: { fontSize: 12 } },
            { text: 'Residual', left: 'center', top: '77%', textStyle: { fontSize: 12 } }
        ],
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        axisPointer: {
            link: { xAxisIndex: 'all' }
        },
        grid: [
            { left: '5%', right: '5%', top: '8%', height: '18%' },
            { left: '5%', right: '5%', top: '33%', height: '18%' },
            { left: '5%', right: '5%', top: '58%', height: '18%' },
            { left: '5%', right: '5%', top: '83%', height: '18%' }
        ],
        xAxis: [
            { type: 'category', data: data.labels, gridIndex: 0, show: false },
            { type: 'category', data: data.labels, gridIndex: 1, show: false },
            { type: 'category', data: data.labels, gridIndex: 2, show: false },
            { type: 'category', data: data.labels, gridIndex: 3 }
        ],
        yAxis: [
             { type: 'value', gridIndex: 0, scale: true, splitNumber: 3 },
             { type: 'value', gridIndex: 1, scale: true, splitNumber: 3 },
             { type: 'value', gridIndex: 2, scale: true, splitNumber: 3 },
             { type: 'value', gridIndex: 3, scale: true, splitNumber: 3 }
        ],
        dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 0, end: 100 },
            { type: 'slider', xAxisIndex: [0, 1, 2, 3], start: 0, end: 100, bottom: 5 }
        ],
        series: [
            {
                name: 'Original',
                type: 'line',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: data.values,
                showSymbol: false,
                sampling: 'lttb',
                lineStyle: { width: 1 },
                itemStyle: { color: '#5470c6' }
            },
            // Anomaly Scatter Series
            {
                name: 'Anomaly',
                type: 'scatter',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: data.anomalies, // [[label_str, value], ...]
                symbol: 'circle',
                symbolSize: 2,
                itemStyle: { color: 'red' },
                z: 10
            },
            {
                name: 'Trend',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: data.trend,
                showSymbol: false,
                sampling: 'lttb',
                itemStyle: { color: '#fac858' },
                lineStyle: { width: 2, color: '#fac858' }
            },
            {
                name: 'Seasonal',
                type: 'line',
                xAxisIndex: 2,
                yAxisIndex: 2,
                data: data.seasonal,
                showSymbol: false,
                sampling: 'lttb',
                itemStyle: { color: '#91cc75' },
                lineStyle: { width: 1, opacity: 0.6, color: '#91cc75' }
            },
             {
                name: 'Residual',
                type: 'scatter',
                xAxisIndex: 3,
                yAxisIndex: 3,
                data: data.resid,
                symbolSize: 2,
                sampling: 'lttb',
                itemStyle: { opacity: 0.5, color: '#ee6666' }
            }
        ]
    }
    
    myChart.setOption(option)
}

const statsTable = computed(() => {
    if (!analysisResult.value || !analysisResult.value.statistics) return null
    
    const stats = analysisResult.value.statistics
    const columns = Object.keys(stats)
    if (columns.length === 0) return null
    
    const statNames = Object.keys(stats[columns[0]])
    
    return {
        columns: ['Metric', ...columns],
        rows: statNames.map(statName => {
            const row: any = { Metric: statName }
            columns.forEach(col => {
                let val = stats[col][statName]
                if (typeof val === 'number') {
                    val = val.toFixed(4)
                }
                row[col] = val
            })
            return row
        })
    }
})

const correlationTable = computed(() => {
    if (!analysisResult.value || !analysisResult.value.correlation) return null
    
    const corr = analysisResult.value.correlation
    const columns = Object.keys(corr)
    
    return {
        columns: ['Feature', ...columns],
        rows: columns.map(rowName => {
            const row: any = { Feature: rowName }
            columns.forEach(colName => {
                 let val = corr[colName] ? corr[colName][rowName] : null
                 if (typeof val === 'number') {
                     val = val.toFixed(4)
                 }
                 row[colName] = val
            })
            return row
        })
    }
})

const formatNum = (v: any) => {
    if (v === null || v === undefined) return '-'
    if (typeof v === 'number') return v.toFixed(4)
    return v
}

</script>

<template>
    <div class="space-y-6 pb-12">
        <Card>
            <CardHeader class="pb-3">
                <CardTitle>数据分析控制台</CardTitle>
                <CardDescription>选择数据集并配置分析类型</CardDescription>
            </CardHeader>
            <CardContent>
                <div class="flex flex-col md:flex-row gap-4 items-end bg-muted/20 p-4 rounded-lg">
                    <div class="space-y-2 w-full md:w-1/3">
                        <label class="text-sm font-medium">1. 选择数据集</label>
                        <select 
                            v-model="selectedDataset" 
                            @change="handleDatasetChange"
                            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <option v-for="name in datasetList" :key="name" :value="name">{{ name }}</option>
                        </select>
                    </div>
                    
                    <div class="space-y-2 w-full md:w-1/3">
                        <label class="text-sm font-medium">2. 选择分析列 (单列详细分析)</label>
                        <select 
                            v-model="selectedColumn" 
                            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
                        </select>
                    </div>

                    <div class="flex gap-2 flex-wrap">
                         <Button @click="handleColumnAnalyze" :disabled="isColumnLoading || !selectedColumn" variant="default">
                            <Icon icon="lucide:line-chart" class="mr-2 h-4 w-4" />
                            {{ isColumnLoading ? '分析中...' : '单列详细分析' }}
                        </Button>
                        <Button @click="handleAnalyze" :disabled="isLoading || !selectedDataset" variant="secondary">
                            <Icon icon="lucide:table" class="mr-2 h-4 w-4" />
                            {{ isLoading ? '计算中...' : '全量统计概览' }}
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>

        <!-- Error Messages -->
        <div v-if="columnErrorMsg || errorMsg" class="space-y-2">
            <div v-if="columnErrorMsg" class="text-red-500 text-sm p-3 border border-red-200 rounded-md bg-red-50">
                列分析错误: {{ columnErrorMsg }}
            </div>
            <div v-if="errorMsg" class="text-red-500 text-sm p-3 border border-red-200 rounded-md bg-red-50">
                全量分析错误: {{ errorMsg }}
            </div>
        </div>

        <!-- Column Analysis Result -->
        <div v-if="columnResult" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
             <Card>
                <CardHeader>
                    <CardTitle class="flex items-center gap-2">
                        <Icon icon="lucide:activity" class="h-5 w-5 text-primary" />
                        趋势与季节性分析: {{ columnResult.column }}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div ref="chartRef" class="w-full h-[600px]"></div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mt-6 pt-6 border-t text-sm">
                        <div class="space-y-1">
                            <div class="font-medium flex items-center gap-2">
                                <span class="block w-3 h-3 rounded-full bg-[#5470c6]"></span>
                                Observed (原始值)
                            </div>
                            <p class="text-muted-foreground text-xs leading-relaxed">
                                原始的时间序列数据，展示了变量随时间变化的真实观测轨迹。
                            </p>
                        </div>
                        <div class="space-y-1">
                            <div class="font-medium flex items-center gap-2">
                                <span class="block w-3 h-3 rounded-full bg-red-600"></span>
                                Anomaly (异常值)
                            </div>
                            <p class="text-muted-foreground text-xs leading-relaxed">
                                基于3σ原则检测出的异常数据点（显著偏离均值的数据）。
                            </p>
                        </div>
                        <div class="space-y-1">
                             <div class="font-medium flex items-center gap-2">
                                <span class="block w-3 h-3 rounded-full bg-[#fac858]"></span>
                                Trend (趋势项)
                            </div>
                            <p class="text-muted-foreground text-xs leading-relaxed">
                                反映数据的长期走向（上升、下降或平稳），剔除了短期波动和噪声干扰。
                            </p>
                        </div>
                        <div class="space-y-1">
                             <div class="font-medium flex items-center gap-2">
                                <span class="block w-3 h-3 rounded-full bg-[#91cc75]"></span>
                                Seasonal (季节项)
                            </div>
                            <p class="text-muted-foreground text-xs leading-relaxed">
                                数据中以固定频率重复出现的周期性波动（如日、周、月度模式）。
                            </p>
                        </div>
                        <div class="space-y-1">
                             <div class="font-medium flex items-center gap-2">
                                <span class="block w-3 h-3 rounded-full bg-[#ee6666]"></span>
                                Residual (残差项)
                            </div>
                            <p class="text-muted-foreground text-xs leading-relaxed">
                                剔除趋势和季节性成分后剩余的随机波动和异常干扰。
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <!-- Advanced Analysis: Difference & FFT -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <Card>
                    <CardHeader>
                         <CardTitle class="flex items-center gap-2">
                             <Icon icon="lucide:arrow-right-left" class="h-5 w-5 text-purple-600" />
                             一阶差分 (Differencing)
                         </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div ref="diffChartRef" class="w-full h-[300px]"></div>
                        <p class="text-xs text-muted-foreground mt-4 leading-relaxed">
                            <span class="font-medium">一阶差分</span>：展示序列当前值与前一个值的差 ($y_t - y_{t-1}$)。
                            <br/>
                            <span class="text-muted-foreground/80">作用：消除线性趋势，将非平稳序列转化为平稳序列，有助于ARIMA等模型建模。</span>
                        </p>
                        
                        <div v-if="columnResult.diff_stationarity" class="mt-4 pt-4 border-t text-sm h-[130px]">
                            <!-- Show Error if any -->
                            <div v-if="columnResult.diff_stationarity.error" class="text-amber-600 text-xs flex items-center gap-2">
                                <Icon icon="lucide:alert-circle" class="w-4 h-4" />
                                <span>平稳性检测不可用: {{ columnResult.diff_stationarity.error }}</span>
                            </div>
                            
                            <!-- Show Results -->
                            <div v-else class="h-full flex flex-col justify-center">
                                <div class="flex justify-between items-center mb-4">
                                    <span class="font-medium text-muted-foreground">差分后平稳性 (ADF):</span>
                                    <span class="font-bold text-base" :class="columnResult.diff_stationarity.is_stationary ? 'text-green-600' : 'text-red-600'">
                                        {{ columnResult.diff_stationarity.is_stationary ? '✅ 平稳 (Stationary)' : '❌ 不平稳 (Non-Stationary)' }}
                                    </span>
                                </div>
                                <div class="flex flex-col gap-2 text-xs text-muted-foreground bg-muted/30 p-3 rounded">
                                    <div class="flex justify-between">
                                        <span>ADF Statistic:</span>
                                        <span class="font-mono text-foreground font-medium">{{ formatNum(columnResult.diff_stationarity.adf_statistic) }}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span>p-value:</span>
                                        <span class="font-mono text-foreground font-medium" :class="{'text-green-600': columnResult.diff_stationarity.p_value < 0.05}">{{ formatNum(columnResult.diff_stationarity.p_value) }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                 </Card>

                 <Card>
                    <CardHeader>
                         <CardTitle class="flex items-center gap-2">
                             <Icon icon="lucide:waves" class="h-5 w-5 text-yellow-600" />
                             频域分析 (FFT Spectrum)
                         </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div ref="fftChartRef" class="w-full h-[300px]"></div>
                        <p class="text-xs text-muted-foreground mt-4 leading-relaxed">
                             <span class="font-medium">频谱分析</span>：通过快速傅里叶变换(FFT)识别数据中隐含的周期性。
                            <br/>
                            <span class="text-muted-foreground/80">作用：峰值对应的频率 ($f$) 换算为周期 ($T=1/f$) 即为数据的主要循环周期。</span>
                        </p>

                        <div v-if="columnResult.fft_peaks && columnResult.fft_peaks.length > 0" class="mt-4 pt-4 border-t text-sm h-[130px] overflow-auto">
                            <div class="text-xs font-medium mb-2 text-muted-foreground">Top 3 Dominant Periods (主要周期):</div>
                            <div class="space-y-2">
                                <div v-for="(peak, idx) in columnResult.fft_peaks" :key="idx" class="flex justify-between items-center bg-muted/30 p-2 rounded">
                                    <div class="flex flex-col">
                                        <span class="font-bold text-foreground">T = {{ formatNum(peak.period) }}</span>
                                        <span class="text-[10px] text-muted-foreground">Freq: {{ formatNum(peak.freq) }}</span>
                                    </div>
                                    <div class="text-xs font-mono text-muted-foreground">
                                        Amp: {{ formatNum(peak.mag) }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                 </Card>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <Card>
                    <CardHeader>
                        <CardTitle>基础统计 (Basic Statistics)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div class="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                            <div v-for="(val, key) in columnResult.stats" :key="key" class="flex justify-between border-b py-2 items-center">
                                <span class="font-medium text-muted-foreground">{{ key }}</span>
                                <span class="font-mono bg-muted px-2 py-0.5 rounded">{{ formatNum(val) }}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>平稳性分析 (ADF Test)</CardTitle>
                        <CardDescription>用于判断序列是否具有单位根 (Unit Root)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div v-if="columnResult.stationarity.error" class="text-red-500">{{ columnResult.stationarity.error }}</div>
                        <div v-else class="space-y-4 text-sm">
                             <div class="flex justify-between items-center bg-muted/50 p-3 rounded-md">
                                <span class="font-medium">结论 (Stationary?):</span>
                                <span class="text-base" :class="{'text-green-600 font-bold': columnResult.stationarity.is_stationary, 'text-red-600 font-bold': !columnResult.stationarity.is_stationary}">
                                    {{ columnResult.stationarity.is_stationary ? '✅ 平稳 (Statinary)' : '❌ 不平稳 (Non-Stationary)' }}
                                </span>
                             </div>
                             
                             <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span class="text-muted-foreground">ADF Statistic:</span>
                                    <span class="font-mono">{{ formatNum(columnResult.stationarity.adf_statistic) }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-muted-foreground">p-value:</span>
                                    <span class="font-mono" :class="{'text-green-600 font-bold': columnResult.stationarity.p_value < 0.05}">
                                        {{ formatNum(columnResult.stationarity.p_value) }}
                                    </span>
                                </div>
                             </div>
                             
                             <div class="pt-2 border-t mt-2">
                                <div class="text-xs font-medium mb-2 text-muted-foreground">Critical Values (阈值):</div>
                                <div v-for="(val, key) in columnResult.stationarity.critical_values" :key="key" class="flex justify-between text-xs py-1">
                                    <span>{{ key }}</span>
                                    <span class="font-mono">{{ formatNum(val) }}</span>
                                </div>
                             </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>

        <!-- General Analysis Results -->
        <div v-if="analysisResult" class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pt-8 border-t">
            <div class="text-lg font-bold">全量统计详情</div>
            <!-- Statistics Card -->
            <Card>
                <CardHeader>
                    <CardTitle>全表描述性统计</CardTitle>
                </CardHeader>
                <CardContent>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm text-left border-collapse">
                            <thead>
                                <tr class="border-b bg-muted/50">
                                    <th class="p-2 font-medium sticky left-0 bg-background md:bg-muted/50">Metric</th>
                                    <th v-for="col in statsTable?.columns.slice(1)" :key="col" class="p-2 font-medium min-w-[100px]">{{ col }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in statsTable?.rows" :key="row.Metric" class="border-b last:border-0 hover:bg-muted/50">
                                    <td class="p-2 font-medium sticky left-0 bg-background">{{ row.Metric }}</td>
                                    <td v-for="col in statsTable?.columns.slice(1)" :key="col" class="p-2 font-mono text-xs">
                                        {{ formatNum(row[col]) }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            <!-- Correlation Card -->
            <Card>
                <CardHeader>
                    <CardTitle>相关性矩阵</CardTitle>
                </CardHeader>
                <CardContent>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm text-left border-collapse">
                            <thead>
                                <tr class="border-b bg-muted/50">
                                    <th class="p-2 font-medium sticky left-0 bg-background md:bg-muted/50">Feature</th>
                                    <th v-for="col in correlationTable?.columns.slice(1)" :key="col" class="p-2 font-medium min-w-[100px]">{{ col }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in correlationTable?.rows" :key="row.Feature" class="border-b last:border-0 hover:bg-muted/50">
                                    <td class="p-2 font-medium sticky left-0 bg-background">{{ row.Feature }}</td>
                                    <td v-for="col in correlationTable?.columns.slice(1)" :key="col" class="p-2 font-mono text-xs"
                                        :style="{ color: Math.abs(parseFloat(row[col])) > 0.7 ? (parseFloat(row[col]) > 0 ? 'green' : 'red') : 'inherit' }"
                                    >
                                        {{ formatNum(row[col]) }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    </div>
</template>
