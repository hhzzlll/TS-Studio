<script setup lang="ts">
import { ref } from 'vue'
import { uploadFile } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icon } from '@iconify/vue'

const previewData = ref<any[]>([])
const columns = ref<string[]>([])
const currentFilename = ref('')
const isUploading = ref(false)

const handleFileChange = async (event: any) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  
  isUploading.value = true
  try {
    const res: any = await uploadFile(formData)
    if (res.status === 'success') {
      previewData.value = res.preview
      columns.value = res.columns
      currentFilename.value = res.filename
      
      // Store info to localStorage
      localStorage.setItem('dataset_filename', res.filename)
    }
  } catch (error) {
    console.error(error)
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>数据集上传</CardTitle>
        <CardDescription>支持 .csv / .xlsx 文件，建议使用标准时间序列格式</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="flex items-center justify-center w-full">
          <label for="dropzone-file" class="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-bray-800 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500 dark:hover:bg-gray-600">
              <div class="flex flex-col items-center justify-center pt-5 pb-6">
                  <Icon icon="lucide:cloud-upload" class="w-10 h-10 mb-3 text-gray-400" />
                  <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click to upload</span> or drag and drop</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">CSV, XLSX (MAX. 10MB)</p>
              </div>
              <input id="dropzone-file" type="file" class="hidden" @change="handleFileChange" accept=".csv,.xlsx" />
          </label>
        </div> 
      </CardContent>
    </Card>

    <Card v-if="previewData.length > 0">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
           <Icon icon="lucide:table" />
           数据预览 ({{ currentFilename }})
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
  </div>
</template>
