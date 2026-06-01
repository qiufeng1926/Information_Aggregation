<template>
  <div class="page-card">
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-statistic title="达人总数" :value="stats.influencerTotal" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="待审核" :value="stats.pendingReview">
          <template #suffix>
            <el-button link type="primary" @click="$router.push('/review')">去审核</el-button>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="6">
        <el-statistic title="今日采集" :value="stats.todayCollected" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="任务成功率" :value="stats.successRate" suffix="%" />
      </el-col>
    </el-row>

    <el-divider />

    <CollectionSessionPanel />

    <el-divider />

    <el-alert
      v-if="stats.runningTaskId"
      type="warning"
      :closable="false"
      show-icon
      :title="`采集任务 #${stats.runningTaskId} 正在执行，队列中还有 ${stats.queuedTasks} 个任务等待`"
      style="margin-bottom: 16px"
    />

    <div class="welcome">
      <h3>欢迎使用达人信息聚合系统</h3>
      <p>Phase 5：智能匹配已上线。采集前请在工作台配置星图 / 蒲公英登录态。</p>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/collection')">发起采集</el-button>
        <el-button type="success" @click="$router.push('/review')">待审核列表</el-button>
        <el-button type="warning" @click="$router.push('/match')">智能匹配</el-button>
        <el-button @click="$router.push('/influencers')">达人库</el-button>
        <el-button @click="$router.push('/tags')">标签管理</el-button>
        <el-button @click="$router.push('/agencies')">MCN机构</el-button>
      </el-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import CollectionSessionPanel from '@/components/CollectionSessionPanel.vue'
import { getCollectionStats } from '@/api/collection'
import { getInfluencers } from '@/api/influencer'

const stats = reactive({
  influencerTotal: 0,
  pendingReview: 0,
  todayCollected: 0,
  successRate: 100,
  runningTaskId: null as number | null,
  queuedTasks: 0,
})

async function loadStats() {
  const [influencers, collection] = await Promise.all([
    getInfluencers({ page: 1, page_size: 1 }),
    getCollectionStats(),
  ])
  stats.influencerTotal = influencers.data.total
  stats.pendingReview = collection.data.pending_review
  stats.todayCollected = collection.data.today_collected
  stats.successRate = collection.data.success_rate
  stats.runningTaskId = collection.data.running_task_id
  stats.queuedTasks = collection.data.queued_tasks
}

onMounted(loadStats)
</script>

<style scoped>
.stats-row {
  margin-bottom: 8px;
}

.welcome h3 {
  margin-top: 0;
}

.welcome p {
  color: #606266;
}
</style>
