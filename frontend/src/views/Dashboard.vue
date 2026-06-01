<template>
  <div class="page-card">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-statistic title="达人总数" :value="stats.total" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="抖音达人" :value="stats.douyin" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="小红书达人" :value="stats.xiaohongshu" />
      </el-col>
    </el-row>

    <el-divider />

    <div class="welcome">
      <h3>欢迎使用达人信息聚合系统</h3>
      <p>当前为 Phase 1 版本，支持达人库管理、多维筛选与 Excel 批量导入。</p>
      <el-space>
        <el-button type="primary" @click="$router.push('/influencers')">进入达人库</el-button>
      </el-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { getInfluencers } from '@/api/influencer'

const stats = reactive({
  total: 0,
  douyin: 0,
  xiaohongshu: 0,
})

async function loadStats() {
  const [all, douyin, xhs] = await Promise.all([
    getInfluencers({ page: 1, page_size: 1 }),
    getInfluencers({ page: 1, page_size: 1, platform: 'douyin' }),
    getInfluencers({ page: 1, page_size: 1, platform: 'xiaohongshu' }),
  ])
  stats.total = all.data.total
  stats.douyin = douyin.data.total
  stats.xiaohongshu = xhs.data.total
}

onMounted(loadStats)
</script>

<style scoped>
.welcome h3 {
  margin-top: 0;
}

.welcome p {
  color: #606266;
}
</style>
