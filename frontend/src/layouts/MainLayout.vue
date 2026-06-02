<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">达人聚合系统</div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#fff">
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/collection">
          <el-icon><Search /></el-icon>
          <span>自动采集</span>
        </el-menu-item>
        <el-menu-item index="/review">
          <el-icon><Checked /></el-icon>
          <span>待审核</span>
        </el-menu-item>
        <el-menu-item index="/influencers">
          <el-icon><User /></el-icon>
          <span>{{ influencerMenuLabel }}</span>
        </el-menu-item>
        <el-menu-item v-if="showAdminMenus" index="/tags">
          <el-icon><CollectionTag /></el-icon>
          <span>标签管理</span>
        </el-menu-item>
        <el-menu-item v-if="showAdminMenus" index="/agencies">
          <el-icon><OfficeBuilding /></el-icon>
          <span>MCN机构</span>
        </el-menu-item>
        <el-menu-item v-if="showAdminMenus" index="/match">
          <el-icon><Connection /></el-icon>
          <span>智能匹配</span>
        </el-menu-item>
        <el-menu-item v-if="showAccessReview" index="/access-review">
          <el-icon><Stamp /></el-icon>
          <span>{{ accessMenuLabel }}</span>
        </el-menu-item>
        <el-menu-item v-if="showUserManage" index="/users">
          <el-icon><Setting /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <el-tag v-if="roleLabel" size="small" type="info">{{ roleLabel }}</el-tag>
          <span class="username">{{ userStore.userInfo?.nickname || userStore.userInfo?.username }}</span>
          <el-button link type="primary" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  ROLE_LABELS,
  canManageUsers,
  canReviewAccess,
  canUseMatch,
  isUser,
  normalizeRole,
} from '@/utils/permission'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/influencers')) return '/influencers'
  if (route.path.startsWith('/collection')) return '/collection'
  if (route.path.startsWith('/review')) return '/review'
  if (route.path.startsWith('/tags')) return '/tags'
  if (route.path.startsWith('/match')) return '/match'
  if (route.path.startsWith('/agencies')) return '/agencies'
  if (route.path.startsWith('/users')) return '/users'
  if (route.path.startsWith('/access-review')) return '/access-review'
  return route.path
})

const currentTitle = computed(() => {
  if (route.path.startsWith('/influencers') && isUser(userStore.userInfo?.role)) {
    return '我的达人'
  }
  return (route.meta.title as string) || '达人信息聚合系统'
})

const role = computed(() => normalizeRole(userStore.userInfo?.role))
const roleLabel = computed(() => ROLE_LABELS[role.value] || role.value)
const showAdminMenus = computed(() => canUseMatch(role.value))
const showUserManage = computed(() => canManageUsers(role.value))
const showAccessReview = computed(
  () => canReviewAccess(role.value) || isUser(userStore.userInfo?.role)
)
const accessMenuLabel = computed(() => (isUser(userStore.userInfo?.role) ? '权限申请' : '权限审核'))
const influencerMenuLabel = computed(() => (isUser(userStore.userInfo?.role) ? '我的达人' : '达人库'))

onMounted(() => {
  userStore.fetchUserInfo()
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-aside {
  background: #001529;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: #606266;
}

.layout-main {
  background: #f5f7fa;
}
</style>
