import { createRouter, createWebHistory } from 'vue-router'
import DataView from '../views/DataView.vue'
import TrainView from '../views/TrainView.vue'
import PredictView from '../views/PredictView.vue'
import AnalysisView from '../views/AnalysisView.vue'
import AuthView from '../views/AuthView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import { getAuthState } from '../api'

const routes = [
    {
        path: '/',
        name: 'Data',
        component: DataView,
        meta: { requiresAuth: true }
    },
    {
        path: '/analysis',
        name: 'Analysis',
        component: AnalysisView,
        meta: { requiresAuth: true }
    },
    {
        path: '/train',
        name: 'Train',
        component: TrainView,
        meta: { requiresAuth: true }
    },
    {
        path: '/predict',
        name: 'Predict',
        component: PredictView,
        meta: { requiresAuth: true }
    },
    {
        path: '/auth',
        name: 'Auth',
        component: AuthView
    },
    {
        path: '/forgot-password',
        name: 'ForgotPassword',
        component: ForgotPasswordView
    },
    {
        path: '/login',
        redirect: '/auth'
    },
    {
        path: '/register',
        redirect: '/auth'
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, _from, next) => {
    const { token } = getAuthState()
    if (to.meta.requiresAuth && !token) {
        next({ name: 'Auth' })
        return
    }
    if (to.name === 'Auth' && token) {
        next({ name: 'Data' })
        return
    }
    next()
})

export default router
