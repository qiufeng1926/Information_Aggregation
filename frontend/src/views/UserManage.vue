<template>
  <div class="page-card">
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新增用户</el-button>
      <el-button @click="loadData">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="nickname" label="昵称" width="140" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">{{ ROLE_LABELS[row.role] || row.role }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="查阅权限" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.view_library" type="success" size="small">已授权</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            :disabled="isOtherSuperAdmin(row)"
            @click="openEdit(row)"
          >
            编辑
          </el-button>
          <el-popconfirm title="确定删除该用户？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger" :disabled="row.role === 'super_admin'">删除</el-button>
            </template>
          </el-popconfirm>
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

    <el-dialog v-model="showDialog" :title="editing ? '编辑用户' : '新增用户'" width="480px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!editing" placeholder="至少 3 个字符" />
        </el-form-item>
        <el-form-item :label="editing ? '新密码' : '密码'" :required="!editing">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editing ? '留空则不修改' : '至少 8 位'"
          />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" style="width: 100%" :disabled="!!editing && editing.role === 'super_admin'">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editing" label="状态">
          <el-switch
            v-model="form.enabled"
            active-text="启用"
            inactive-text="禁用"
            :disabled="!!editing && editing.role === 'super_admin'"
          />
        </el-form-item>
        <el-form-item v-if="editing && form.role === 'user'" label="查阅权限">
          <el-switch v-model="form.view_library" active-text="已授权" inactive-text="未授权" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createUser, deleteUser, getUsers, updateUser, type ManagedUser } from '@/api/users'
import { ROLE_LABELS } from '@/utils/permission'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.userInfo?.id)

const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editing = ref<ManagedUser | null>(null)
const list = ref<ManagedUser[]>([])
const pagination = reactive({ page: 1, page_size: 20, total: 0 })

const form = reactive({
  username: '',
  password: '',
  nickname: '',
  role: 'user',
  enabled: true,
  view_library: false,
})

function formatTime(v: string) {
  return v?.replace('T', ' ').slice(0, 19)
}

function isOtherSuperAdmin(row: ManagedUser) {
  return row.role === 'super_admin' && row.id !== currentUserId.value
}

function resetForm() {
  form.username = ''
  form.password = ''
  form.nickname = ''
  form.role = 'user'
  form.enabled = true
  form.view_library = false
}

async function loadData() {
  loading.value = true
  try {
    const res = await getUsers({ page: pagination.page, page_size: pagination.page_size })
    list.value = res.data.items
    pagination.total = res.data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  resetForm()
  showDialog.value = true
}

function openEdit(row: ManagedUser) {
  if (isOtherSuperAdmin(row)) {
    ElMessage.warning('不能编辑其他超级管理员')
    return
  }
  editing.value = row
  form.username = row.username
  form.password = ''
  form.nickname = row.nickname || ''
  form.role = row.role
  form.enabled = row.status === 1
  form.view_library = row.view_library
  showDialog.value = true
}

async function handleSave() {
  if (editing.value) {
    if (form.password && form.password.length < 8) {
      ElMessage.warning('新密码至少 8 位')
      return
    }
  } else {
    const username = form.username.trim()
    if (!username || !form.password) {
      ElMessage.warning('请填写用户名和密码')
      return
    }
    if (username.length < 3) {
      ElMessage.warning('用户名至少 3 个字符')
      return
    }
    if (form.password.length < 8) {
      ElMessage.warning('密码至少 8 位')
      return
    }
  }

  saving.value = true
  try {
    if (editing.value) {
      await updateUser(editing.value.id, {
        nickname: form.nickname || undefined,
        role: form.role,
        status: form.enabled ? 1 : 0,
        view_library: form.view_library,
        password: form.password || undefined,
      })
      ElMessage.success('用户已更新')
    } else {
      await createUser({
        username: form.username.trim(),
        password: form.password,
        nickname: form.nickname || undefined,
        role: form.role,
      })
      ElMessage.success('用户已创建')
    }
    showDialog.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(userId: number) {
  await deleteUser(userId)
  ElMessage.success('用户已删除')
  loadData()
}

onMounted(async () => {
  if (!userStore.userInfo) {
    await userStore.fetchUserInfo()
  }
  loadData()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
