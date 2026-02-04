import { createRouter, createWebHistory } from 'vue-router'
import DataView from '../views/DataView.vue'
import TrainView from '../views/TrainView.vue'
import PredictView from '../views/PredictView.vue'
import AnalysisView from '../views/AnalysisView.vue'

const routes = [
    {
        path: '/',
        name: 'Data',
        component: DataView
    },
    {
        path: '/analysis',
        name: 'Analysis',
        component: AnalysisView
    },
    {
        path: '/train',
        name: 'Train',
        component: TrainView
    },
    {
        path: '/predict',
        name: 'Predict',
        component: PredictView
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
