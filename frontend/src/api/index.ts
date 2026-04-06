import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    timeout: 50000
})

// Request interceptor
api.interceptors.request.use(
    config => {
        return config
    },
    error => {
        console.error(error)
        return Promise.reject(error)
    }
)

// Response interceptor
api.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        console.error('API Error:', error.message || 'Request Failed')
        return Promise.reject(error)
    }
)

export const uploadFile = (formData: FormData, isPreview: boolean = false) => {
    const url = isPreview ? '/upload/?preview=true' : '/upload/';
    return api.post(url, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

export const getConfig = () => {
    return api.get('/config/')
}

export const getDatasets = () => {
    return api.get('/datasets/')
}

export const getDatasetColumns = (filename: string) => {
    return api.get(`/datasets/${filename}/columns/`)
}

export const getDatasetInfo = (filename: string) => {
    return api.get(`/datasets/info/?filename=${filename}`)
}

export const getDatasetAnalysis = (filename: string) => {
    return api.get(`/datasets/analysis/?filename=${filename}`)
}

export const getColumnAnalysis = (filename: string, column: string) => {
    return api.get(`/datasets/column-analysis/?filename=${filename}&column=${column}`)
}

export const startTraining = (config: any) => {
    return api.post('/train/', config)
}

export const getActiveTraining = () => {
    return api.get('/train/active/')
}
export const getCompletedModels = () => {
    return api.get('/models/completed/')
}

export const getPredictionResult = (id: number, limit: number = 20) => {
    return api.get(`/result/${id}/?limit=${limit}`)
}
export const getTrainingStatus = (jobId: string | number) => {
    return api.get(`/train/status/${jobId}/`)
}

export const controlTraining = (jobId: string | number, action: 'pause' | 'resume' | 'stop') => {
    return api.post(`/train/control/${jobId}/`, { action })
}

export const runPrediction = (params: any) => {
    return api.post('/predict/', params)
}

export const deleteDataset = (filename: string) => {
    return api.delete(`/datasets/?filename=${filename}`)
}

export const getDatasetDownloadUrl = (filename: string) => {
    return `/api/datasets/download/?filename=${filename}`
}

export const getTraditionalModels = () => {
    return api.get('/traditional-models/')
}

export const predictWithTraditionalModel = (params: any) => {
    return api.post('/traditional-models/predict/', params)
}
