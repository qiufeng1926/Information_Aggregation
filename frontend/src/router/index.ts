import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: MainLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'collection',
          name: 'CollectionTasks',
          component: () => import('@/views/CollectionTasks.vue'),
          meta: { title: '自动采集' },
        },
        {
          path: 'review',
          name: 'ReviewQueue',
          component: () => import('@/views/ReviewQueue.vue'),
          meta: { title: '待审核' },
        },
        {
          path: 'influencers',
          name: 'InfluencerList',
          component: () => import('@/views/InfluencerList.vue'),
          meta: { title: '达人库' },
        },
        {
          path: 'influencers/:id',
          name: 'InfluencerDetail',
          component: () => import('@/views/InfluencerDetail.vue'),
          meta: { title: '达人详情' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }
})

export default router
