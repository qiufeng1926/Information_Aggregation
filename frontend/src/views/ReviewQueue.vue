<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-select v-model="taskId" placeholder="筛选任务" clearable style="width: 200px" @change="handleSearch">
        <el-option v-for="t in tasks" :key="t.id" :label="`${t.keyword} (#${t.id})`" :value="t.id" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="loadData">刷新</el-button>
      <div style="flex: 1"></div>
      <el-button type="success" :disabled="!selectedIds.length" @click="handleBatchApprove">
        批量通过 ({{ selectedIds.length }})
      </el-button>
      <el-button type="danger" :disabled="!selectedIds.length" @click="handleBatchReject">
        批量拒绝
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="list"
      stripe
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column label="头像" width="70">
        <template #default="{ row }">
          <el-avatar :size="40" :src="row.avatar_url || undefined">
            {{ row.nickname?.[0] || '达' }}
          </el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="nickname" label="昵称" min-width="140" />
      <el-table-column label="平台" width="80">
        <template #default="{ row }">{{ formatPlatform(row.platform) }}</template>
      </el-table-column>
      <el-table-column label="粉丝量" width="100">
        <template #default="{ row }">{{ formatFollowers(row.follower_count) }}</template>
      </el-table-column>
      <el-table-column label="匹配度" width="90">
        <template #default="{ row }">
          <el-tag type="success">{{ row.match_score }}分</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="标签" min-width="140">
        <template #default="{ row }">
          <el-tag v-for="tag in row.matched_tags || []" :key="tag" size="small" style="margin-right: 4px">
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="带货信息" min-width="160">
        <template #default="{ row }">
          <span v-if="row.extra_data">
            GMV {{ row.extra_data.recent_gmv }} / 橱窗 {{ row.extra_data.showcase_count }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" @click="handleApprove([row.id])">通过</el-button>
          <el-button link type="danger" @click="handleReject([row.id])">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approveCollected,
  formatFollowers,
  formatPlatform,
  getCollectionTasks,
  getPendingReview,
  rejectCollected,
  type CollectedInfluencer,
  type CollectionTask,
} from '@/api/collection'

const route = useRoute()
const loading = ref(false)
const list = ref<CollectedInfluencer[]>([])
const tasks = ref<CollectionTask[]>([])
const selectedIds = ref<number[]>([])
const taskId = ref<number | undefined>(
  route.query.task_id ? Number(route.query.task_id) : undefined
)

const pagination = reactive({ page: 1, page_size: 20, total: 0 })

function handleSelectionChange(rows: CollectedInfluencer[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function loadTasks() {
  const res = await getCollectionTasks({ page: 1, page_size: 100 })
  tasks.value = res.data.items
}

async function loadData() {
  loading.value = true
  try {
    const res = await getPendingReview({
      task_id: taskId.value,
      page: pagination.page,
      page_size: pagination.page_size,
    })
    list.value = res.data.items
    pagination.total = res.data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

async function handleApprove(ids: number[]) {
  const res = await approveCollected(ids)
  ElMessage.success(`已通过 ${res.data.approved} 条，入库达人库`)
  selectedIds.value = []
  loadData()
}

async function handleReject(ids: number[]) {
  await ElMessageBox.confirm('确认拒绝所选达人？', '提示', { type: 'warning' })
  const res = await rejectCollected(ids)
  ElMessage.success(`已拒绝 ${res.data.rejected} 条`)
  selectedIds.value = []
  loadData()
}

function handleBatchApprove() {
  handleApprove(selectedIds.value)
}

function handleBatchReject() {
  handleReject(selectedIds.value)
}

watch(
  () => route.query.task_id,
  (val) => {
    taskId.value = val ? Number(val) : undefined
    loadData()
  }
)

onMounted(async () => {
  await loadTasks()
  loadData()
})
</script>

<style scoped>
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
