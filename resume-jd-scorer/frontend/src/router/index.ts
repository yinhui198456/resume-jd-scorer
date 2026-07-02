import { createRouter, createWebHistory } from 'vue-router'
import EvaluateView from '../views/EvaluateView.vue'
import JDsView from '../views/JDsView.vue'
import ResumesView from '../views/ResumesView.vue'

const routes = [
  { path: '/', redirect: '/evaluate' },
  { path: '/evaluate', component: EvaluateView, name: 'Evaluate' },
  { path: '/jds', component: JDsView, name: 'JDs' },
  { path: '/resumes', component: ResumesView, name: 'Resumes' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
