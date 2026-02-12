<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { uploadFile, getDatasets, deleteDataset, getDatasetDownloadUrl, getDatasetInfo } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

const datasets = ref<string[]>([])
const previewData = ref<any[]>([])
const columns = ref<string[]>([])
const currentFilename = ref('')
const isUploading = ref(false)
const selectedFile = ref<File | null>(null)
const isConfirmed = ref(false)

// 独立的查看预览状态
const viewPreviewData = ref<any[]>([])
const viewPreviewColumns = ref<string[]>([])
const viewPreviewFilename = ref('')
const isLoadingPreview = ref(false)

const handleFileChange = async (event: any) => {
  const file = event.target.files[0]
  if (!file) return
  await processFile(file)
}

const handleDrop = async (event: DragEvent) => {
  const file = event.dataTransfer?.files[0]
  if (!file) return
  await processFile(file)
}

const processFile = async (file: File) => {
  selectedFile.value = file
  // Initial preview upload
  const formData = new FormData()
  formData.append('file', file)
  
  isUploading.value = true
  isConfirmed.value = false // Reset confirmation state
  
  try {
    // Pass true for preview mode
    const res: any = await uploadFile(formData, true)
    if (res.status === 'success') {
      previewData.value = res.preview
      columns.value = res.columns
      currentFilename.value = res.filename
      // Don't save to localStorage yet
    }
  } catch (error) {
    console.error(error)
    previewData.value = [] // clear on error
    selectedFile.value = null
  } finally {
    isUploading.value = false
  }
}

const confirmUpload = async () => {
  if (!selectedFile.value) return

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  
  isUploading.value = true
  try {
    // Pass false (default) for actual saving
    const res: any = await uploadFile(formData, false)
    if (res.status === 'success') {
      // Update state to confirmed
      isConfirmed.value = true
      // Now save to localStorage
      localStorage.setItem('dataset_filename', res.filename)
      await fetchDatasets()
    }
  } catch (error) {
    console.error(error)
  } finally {
    isUploading.value = false
  }
}

const cancelUpload = () => {
  previewData.value = []
  columns.value = []
  currentFilename.value = ''
  selectedFile.value = null
  isConfirmed.value = false
}

const fetchDatasets = async () => {
    try {
        const res: any = await getDatasets()
        datasets.value = res
    } catch (error) {
        console.error("Failed to fetch datasets", error)
    }
}

const handleDelete = async (filename: string) => {
    if(!confirm(`确定要删除 ${filename} 吗?`)) return
    try {
        await deleteDataset(filename)
        await fetchDatasets()
        if (currentFilename.value === filename) {
             cancelUpload()
        }
    } catch (error) {
        console.error("Failed to delete dataset", error)
    }
}

const handleDownload = (filename: string) => {
    // Open in new tab which will trigger download
    // Use the full URL with base path included via proxy or logic
    // Since we are in SPA, we can just use the url relative to current origin if proxy is set up
    // getDatasetDownloadUrl returns `/api/...`
    window.open(getDatasetDownloadUrl(filename), '_blank')
}

const handlePreview = async (filename: string) => {
    isLoadingPreview.value = true
    try {
        const res: any = await getDatasetInfo(filename)
        viewPreviewData.value = res.preview
        viewPreviewColumns.value = res.columns
        viewPreviewFilename.value = res.filename
    } catch (error) {
        console.error("Failed to load dataset info", error)
    } finally {
        isLoadingPreview.value = false
    }
}

onMounted(() => {
    fetchDatasets()
})
</script>

<template>
  <div class="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>数据集上传</CardTitle>
        <CardDescription>支持 .csv / .xlsx 文件，建议使用标准时间序列格式</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="!previewData.length" class="flex items-center justify-center w-full">
          <label 
            for="dropzone-file" 
            class="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-bray-800 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500 dark:hover:bg-gray-600"
            @dragover.prevent
            @drop.prevent="handleDrop"
          >
              <div class="flex flex-col items-center justify-center pt-5 pb-6">
                  <Icon icon="lucide:cloud-upload" class="w-10 h-10 mb-3 text-gray-400" />
                  <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click to upload</span> or drag and drop</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">CSV, XLSX (MAX. 10MB)</p>
              </div>
              <input id="dropzone-file" type="file" class="hidden" @change="handleFileChange" accept=".csv,.xlsx" />
          </label>
        </div> 
        
        <div v-else class="flex flex-col items-center justify-center w-full py-8 text-center space-y-4">
             <div class="text-lg font-medium">{{ currentFilename }}</div>
             <div class="flex gap-4">
                 <Button v-if="!isConfirmed" @click="confirmUpload" :disabled="isUploading">
                    <Icon v-if="isUploading" icon="lucide:loader-2" class="animate-spin mr-2" />
                    确认上传
                 </Button>
                 <Button v-if="!isConfirmed" variant="outline" @click="cancelUpload" :disabled="isUploading">
                    取消
                 </Button>
                 <div v-if="isConfirmed" class="flex items-center text-green-600 font-semibold gap-2">
                    <Icon icon="lucide:check-circle" /> 上传成功
                    <Button variant="ghost" size="sm" class="ml-4" @click="cancelUpload">上传新文件</Button>
                 </div>
             </div>
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>已上传数据集</CardTitle>
        <CardDescription>管理已上传到服务器的数据集文件</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="datasets.length === 0" class="text-center text-gray-500 py-8">
            暂无数据集，请上传
        </div>
        <div v-else class="relative overflow-x-auto rounded-md border">
            <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <th scope="col" class="px-6 py-3">文件名</th>
                        <th scope="col" class="px-6 py-3 text-right">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="file in datasets" :key="file" class="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white">
                            {{ file }}
                        </td>
                        <td class="px-6 py-4 text-right flex justify-end gap-2">
                             <Button variant="outline" size="sm" @click="handlePreview(file)">
                                <Icon icon="lucide:eye" class="w-4 h-4 mr-1" /> 预览
                             </Button>
                             <Button variant="outline" size="sm" @click="handleDownload(file)">
                                <Icon icon="lucide:download" class="w-4 h-4 mr-1" /> 下载
                             </Button>
                             <Button variant="destructive" size="sm" @click="handleDelete(file)">
                                <Icon icon="lucide:trash-2" class="w-4 h-4 mr-1" /> 删除
                             </Button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
      </CardContent>
    </Card>

    <!-- 上传文件的预览卡片 -->
    <Card v-if="previewData.length > 0">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
           <Icon icon="lucide:upload" />
           上传文件预览 ({{ currentFilename }})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="relative overflow-x-auto rounded-md border">
            <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <th v-for="col in columns" :key="col" scope="col" class="px-6 py-3 whitespace-nowrap">
                            {{ col }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, idx) in previewData" :key="idx" class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                        <td v-for="col in columns" :key="col" class="px-6 py-4 whitespace-nowrap">
                            {{ row[col] }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
      </CardContent>
    </Card>

    <!-- 查看已存在文件的预览卡片 -->
    <Card v-if="viewPreviewData.length > 0">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
           <Icon icon="lucide:table" />
           数据预览 ({{ viewPreviewFilename }})
        </CardTitle>
        <CardDescription>
          <Button variant="ghost" size="sm" @click="viewPreviewData = []; viewPreviewColumns = []; viewPreviewFilename = ''">
            <Icon icon="lucide:x" class="w-4 h-4 mr-1" /> 关闭预览
          </Button>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="isLoadingPreview" class="flex justify-center items-center py-8">
          <Icon icon="lucide:loader-2" class="w-8 h-8 animate-spin text-gray-400" />
        </div>
        <div v-else class="relative overflow-x-auto rounded-md border">
            <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <th v-for="col in viewPreviewColumns" :key="col" scope="col" class="px-6 py-3 whitespace-nowrap">
                            {{ col }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, idx) in viewPreviewData" :key="idx" class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                        <td v-for="col in viewPreviewColumns" :key="col" class="px-6 py-4 whitespace-nowrap">
                            {{ row[col] }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
