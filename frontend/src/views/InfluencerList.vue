<template>
  <div class="page-card">
    <div class="filter-bar">
      <el-select v-model="filters.platform" placeholder="平台" clearable style="width: 140px">
        <el-option v-for="item in PLATFORM_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="filters.source" placeholder="来源" clearable style="width: 140px">
        <el-option v-for="item in SOURCE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索昵称/ID" clearable style="width: 200px" />
      <el-input-number v-model="filters.follower_min" :min="0" placeholder="粉丝下限" controls-position="right" />
      <el-input-number v-model="filters.follower_max" :min="0" placeholder="粉丝上限" controls-position="right" />
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="handleReset">重置</el-button>
      <div style="flex: 1"></div>
      <el-button type="success" @click="showCreate = true">新增达人</el-button>
      <el-button @click="showImport = true">Excel 导入</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column label="头像" width="70">
        <template #default="{ row }">
          <el-avatar :size="40" :src="row.avatar_url || undefined">
            {{ row.nickname?.[0] || '达' }}
          </el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="nickname" label="昵称" min-width="140" />
      <el-table-column label="平台" width="100">
        <template #default="{ row }">{{ formatPlatform(row.platform) }}</template>
      </el-table-column>
      <el-table-column prop="platform_uid" label="达人ID" min-width="140" />
      <el-table-column label="粉丝量" width="110">
        <template #default="{ row }">{{ formatFollowers(row.follower_count) }}</template>
      </el-table-column>
      <el-table-column label="来源" width="100">
        <template #default="{ row }">{{ formatSource(row.source) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/influencers/${row.id}`)">详情</el-button>
          <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
      />
    </div>

    <el-dialog v-model="showCreate" title="新增达人" width="520px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="平台" required>
          <el-select v-model="createForm.platform" style="width: 100%">
            <el-option v-for="item in PLATFORM_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="达人ID" required>
          <el-input v-model="createForm.platform_uid" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="createForm.nickname" />
        </el-form-item>
        <el-form-item label="粉丝量">
          <el-input-number v-model="createForm.follower_count" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="createForm.source" style="width: 100%">
            <el-option v-for="item in SOURCE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showImport" title="Excel 导入达人" width="520px">
      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="handleFileChange">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
      </el-upload>
      <p class="import-tip">必填列：平台、达人ID；可选列：昵称、粉丝量、来源、头像链接、主页链接</p>
      <div v-if="importResult" class="import-result">
        <p>总计 {{ importResult.total }} 条，成功 {{ importResult.success }} 条，失败 {{ importResult.failed }} 条</p>
        <ul v-if="importResult.errors.length">
          <li v-for="(err, idx) in importResult.errors" :key="idx">{{ err }}</li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="showImport = false">关闭</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importFile" @click="handleImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  PLATFORM_OPTIONS,
  SOURCE_OPTIONS,
  createInfluencer,
  deleteInfluencer,
  formatFollowers,
  formatPlatform,
  formatSource,
  getInfluencers,
  importInfluencers,
  type ImportResult,
  type Influencer,
} from '@/api/influencer'

const loading = ref(false)
const creating = ref(false)
const importing = ref(false)
const showCreate = ref(false)
const showImport = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<ImportResult | null>(null)
const list = ref<Influencer[]>([])

const filters = reactive({
  platform: '',
  source: '',
  keyword: '',
  follower_min: undefined as number | undefined,
  follower_max: undefined as number | undefined,
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const createForm = reactive({
  platform: 'douyin',
  platform_uid: '',
  nickname: '',
  follower_count: 0,
  source: 'manual',
})

async function loadData() {
  loading.value = true
  try {
    const res = await getInfluencers({
      page: pagination.page,
      page_size: pagination.page_size,
      platform: filters.platform || undefined,
      source: filters.source || undefined,
      keyword: filters.keyword || undefined,
      follower_min: filters.follower_min,
      follower_max: filters.follower_max,
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

function handleReset() {
  filters.platform = ''
  filters.source = ''
  filters.keyword = ''
  filters.follower_min = undefined
  filters.follower_max = undefined
  handleSearch()
}

async function handleCreate() {
  if (!createForm.platform_uid) {
    ElMessage.warning('请填写达人ID')
    return
  }
  creating.value = true
  try {
    await createInfluencer(createForm)
    ElMessage.success('创建成功')
    showCreate.value = false
    loadData()
  } finally {
    creating.value = false
  }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确认删除该达人？', '提示', { type: 'warning' })
  await deleteInfluencer(id)
  ElMessage.success('删除成功')
  loadData()
}

function handleFileChange(file: UploadFile) {
  importFile.value = file.raw || null
  importResult.value = null
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const res = await importInfluencers(importFile.value)
    importResult.value = res.data
    ElMessage.success('导入完成')
    loadData()
  } finally {
    importing.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.import-tip {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}

.import-result {
  margin-top: 12px;
  font-size: 13px;
  color: #606266;
}

.import-result ul {
  margin: 8px 0 0;
  padding-left: 20px;
  color: #f56c6c;
}
</style>
