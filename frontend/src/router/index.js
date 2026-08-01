import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard/index.vue'),
    meta: { title: 'MOM指数' }
  },
  {
    path: '/sector/:code',
    name: 'SectorDetail',
    component: () => import('@/views/SectorDetail/index.vue'),
    meta: { title: '板块详情', showBack: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title}` : 'MOM指数'
  next()
})

export default router
