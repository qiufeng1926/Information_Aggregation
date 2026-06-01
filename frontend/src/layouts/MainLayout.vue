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
          <span>达人库</span>
        </el-menu-item>
        <el-menu-item index="/tags">
          <el-icon><CollectionTag /></el-icon>
          <span>标签管理</span>
        </el-menu-item>
        <el-menu-item index="/agencies">
          <el-icon><OfficeBuilding /></el-icon>
          <span>MCN机构</span>
        </el-menu-item>
        <el-menu-item index="/match">
          <el-icon><Connection /></el-icon>
          <span>智能匹配</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
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
  return route.path
})

const currentTitle = computed(() => (route.meta.title as string) || '达人信息聚合系统')

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
