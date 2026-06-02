<template>
  <div class="page-card">
    <el-card v-if="isUserRole" shadow="never" class="section">
      <template #header>申请查阅权限</template>
      <p class="tip">普通用户默认只能查看自己采集并通过审核的达人。如需查看完整达人库，请提交申请。</p>
      <el-input v-model="applyReason" type="textarea" :rows="3" placeholder="申请理由（可选）" />
      <el-button type="primary" style="margin-top: 12px" @click="handleApply">提交申请</el-button>
    </el-card>

    <el-card v-if="canReview" shadow="never" class="section">
      <template #header>权限策略</template>
      <el-form inline>
        <el-form-item label="屏蔽上级任务">
          <el-switch
            v-model="settings.block_upper_role_tasks"
            active-text="普通用户不可查看管理员及以上任务"
            @change="saveSettings"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="canReview" shadow="never" class="section">
      <template #header>
        <div class="header-row">
          <span>查阅权限申请</span>
          <el-radio-group v-model="statusFilter" size="small" @change="loadData">
            <el-radio-button label="pending">待审核</el-radio-button>
            <el-radio-button label="approved">已通过</el-radio-button>
            <el-radio-button label="rejected">已拒绝</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="用户" width="160">
          <template #default="{ row }">{{ row.nickname || row.username }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column v-if="statusFilter === 'pending'" label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="handleReview(row.id, true)">通过</el-button>
            <el-button link type="danger" @click="handleReview(row.id, false)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAccessRequests,
  getPermissionSettings,
  reviewAccessRequest,
  submitAccessRequest,
  updatePermissionSettings,
  type AccessRequest,
} from '@/api/permissions'
import { useUserStore } from '@/stores/user'
import { canReviewAccess, isUser as checkIsUser, normalizeRole } from '@/utils/permission'

const userStore = useUserStore()
const loading = ref(false)
const list = ref<AccessRequest[]>([])
const statusFilter = ref('pending')
const applyReason = ref('')
const settings = ref({ block_upper_role_tasks: true })

const canReview = computed(() => canReviewAccess(userStore.userInfo?.role))
const isUserRole = computed(() => checkIsUser(userStore.userInfo?.role))

function formatTime(v: string) {
  return v?.replace('T', ' ').slice(0, 19)
}

function statusLabel(s: string) {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] || s
}

function statusType(s: string) {
  return ({ pending: 'warning', approved: 'success', rejected: 'info' } as const)[s] || 'info'
}

async function loadSettings() {
  const res = await getPermissionSettings()
  settings.value = res.data
}

async function loadData() {
  loading.value = true
  try {
    const res = await getAccessRequests({ status: statusFilter.value, page: 1, page_size: 50 })
    list.value = res.data.items
  } finally {
    loading.value = false
  }
}

async function handleApply() {
  await submitAccessRequest(applyReason.value || undefined)
  ElMessage.success('申请已提交')
  applyReason.value = ''
}

async function handleReview(id: number, approve: boolean) {
  await reviewAccessRequest(id, approve)
  ElMessage.success(approve ? '已通过' : '已拒绝')
  loadData()
}

async function saveSettings() {
  await updatePermissionSettings(settings.value.block_upper_role_tasks)
  ElMessage.success('策略已更新')
}

onMounted(async () => {
  await userStore.fetchUserInfo()
  if (canReview.value) {
    loadSettings()
    loadData()
  }
})
</script>

<style scoped>
.section {
  margin-bottom: 16px;
}

.tip {
  color: #606266;
  font-size: 13px;
  margin: 0 0 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
