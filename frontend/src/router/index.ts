import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { useUserStore } from '@/stores/user'
import { normalizeRole, ROLES } from '@/utils/permission'

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
        {
          path: 'tags',
          name: 'TagManage',
          component: () => import('@/views/TagManage.vue'),
          meta: { title: '标签管理', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN] },
        },
        {
          path: 'match',
          name: 'MatchList',
          component: () => import('@/views/MatchList.vue'),
          meta: { title: '智能匹配', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN] },
        },
        {
          path: 'match/:id',
          name: 'MatchDetail',
          component: () => import('@/views/MatchDetail.vue'),
          meta: { title: '匹配结果', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN] },
        },
        {
          path: 'agencies',
          name: 'AgencyList',
          component: () => import('@/views/AgencyList.vue'),
          meta: { title: 'MCN机构', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN] },
        },
        {
          path: 'agencies/:id',
          name: 'AgencyDetail',
          component: () => import('@/views/AgencyDetail.vue'),
          meta: { title: '机构详情', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN] },
        },
        {
          path: 'users',
          name: 'UserManage',
          component: () => import('@/views/UserManage.vue'),
          meta: { title: '用户管理', roles: [ROLES.SUPER_ADMIN] },
        },
        {
          path: 'access-review',
          name: 'AccessReview',
          component: () => import('@/views/AccessReview.vue'),
          meta: { title: '权限审核', roles: [ROLES.ADMIN, ROLES.SUPER_ADMIN, ROLES.USER] },
        },
      ],
    },
  ],
})

function canAccessRoute(requiredRoles: string[] | undefined, role: string) {
  if (!requiredRoles?.length) return true
  if (role === ROLES.SUPER_ADMIN) return true
  return requiredRoles.includes(role)
}

router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }

  const requiredRoles = to.meta.roles as string[] | undefined
  if (token && requiredRoles?.length) {
    const store = useUserStore()
    if (!store.userInfo) {
      try {
        await store.fetchUserInfo()
      } catch {
        store.logout()
        return '/login'
      }
    }
    const role = normalizeRole(store.userInfo?.role)
    if (!canAccessRoute(requiredRoles, role)) {
      return '/dashboard'
    }
  }
})

export default router
