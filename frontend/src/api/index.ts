import axios from 'axios'

const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USERNAME_KEY = 'auth_username'

const api = axios.create({
    baseURL: '/api',
    timeout: 50000
})

// Request interceptor
api.interceptors.request.use(
    config => {
        const token = localStorage.getItem(AUTH_TOKEN_KEY)
        if (token) {
            config.headers = config.headers || {}
            config.headers.Authorization = `Token ${token}`
        }
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

export const registerUser = (payload: { username: string; password: string; email?: string }) => {
    return api.post('/auth/register/', payload)
}

export const loginUser = (payload: { username: string; password: string }) => {
    return api.post('/auth/login/', payload)
}

export const logoutUser = () => {
    return api.post('/auth/logout/')
}

export const deleteAccount = () => {
    return api.post('/auth/delete/')
}

export const requestPasswordReset = (payload: { username: string }) => {
    return api.post('/auth/password-reset/', payload)
}

export const confirmPasswordReset = (payload: { username: string; code: string; password: string; confirm_password: string }) => {
    return api.post('/auth/password-reset/confirm/', payload)
}

export const setAuthStorage = (token: string, username: string) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
    localStorage.setItem(AUTH_USERNAME_KEY, username)

    // Manage multi-account sessions
    const sessionsStr = localStorage.getItem('auth_sessions') || '[]'
    try {
        let sessions = JSON.parse(sessionsStr)
        // Remove existing session for this user if exists (to update token)
        sessions = sessions.filter((s: any) => s.username !== username)
        sessions.push({ username, token })
        localStorage.setItem('auth_sessions', JSON.stringify(sessions))
    } catch (e) {
        localStorage.setItem('auth_sessions', JSON.stringify([{ username, token }]))
    }
}

export const clearAuthStorage = () => {
    // Only clear active state, keep sessions
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USERNAME_KEY)
}

export const removeSession = (username: string) => {
    const sessionsStr = localStorage.getItem('auth_sessions') || '[]'
    try {
        let sessions = JSON.parse(sessionsStr)
        sessions = sessions.filter((s: any) => s.username !== username)
        localStorage.setItem('auth_sessions', JSON.stringify(sessions))
    } catch (e) { }
}

export const getSavedSessions = () => {
    const sessionsStr = localStorage.getItem('auth_sessions') || '[]'
    try {
        return JSON.parse(sessionsStr)
    } catch (e) {
        return []
    }
}

export const switchToSession = (username: string) => {
    const sessions = getSavedSessions()
    const target = sessions.find((s: any) => s.username === username)
    if (target) {
        localStorage.setItem(AUTH_TOKEN_KEY, target.token)
        localStorage.setItem(AUTH_USERNAME_KEY, target.username)
        return true
    }
    return false
}

export const getAuthState = () => {
    return {
        token: localStorage.getItem(AUTH_TOKEN_KEY),
        username: localStorage.getItem(AUTH_USERNAME_KEY)
    }
}
