import axios from 'axios'

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',
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

export const uploadFile = (formData: FormData) => {
    return api.post('/upload/', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

export const getConfig = () => {
    return api.get('/config/')
}

export const startTraining = (config: any) => {
    return api.post('/train/', config)
}

export const getActiveTraining = () => {
    return api.get('/train/active/')
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
