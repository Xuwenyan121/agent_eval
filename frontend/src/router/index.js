import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('@/views/Agents.vue'),
  },
  {
    path: '/agents/create',
    name: 'AgentCreate',
    component: () => import('@/views/AgentCreate.vue'),
  },
  {
    path: '/agents/:id/edit',
    name: 'AgentEdit',
    component: () => import('@/views/AgentCreate.vue'),
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: () => import('@/views/Datasets.vue'),
  },
  {
    path: '/datasets/:id',
    name: 'DatasetDetail',
    component: () => import('@/views/DatasetDetail.vue'),
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/Tasks.vue'),
  },
  {
    path: '/tasks/create',
    name: 'TaskCreate',
    component: () => import('@/views/TaskCreate.vue'),
  },
  {
    path: '/tasks/:id',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetail.vue'),
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/Reports.vue'),
  },
  {
    path: '/reports/:id',
    name: 'ReportDetail',
    component: () => import('@/views/ReportDetail.vue'),
  },
  {
    path: '/badcases',
    name: 'BadCases',
    component: () => import('@/views/BadCases.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
  },
  {
    path: '/traces/:id',
    name: 'TraceDetail',
    component: () => import('@/views/TraceDetail.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router