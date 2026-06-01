<template>
  <div v-loading="loading" class="page-card">
    <div class="header">
      <el-button @click="$router.back()">返回</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </div>

    <template v-if="form">
      <el-descriptions title="基础信息" :column="2" border>
        <el-descriptions-item label="昵称">{{ form.nickname || '-' }}</el-descriptions-item>
        <el-descriptions-item label="平台">{{ formatPlatform(form.platform) }}</el-descriptions-item>
        <el-descriptions-item label="达人ID">{{ form.platform_uid }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ formatSource(form.source) }}</el-descriptions-item>
        <el-descriptions-item label="粉丝量">{{ formatFollowers(form.follower_count) }}</el-descriptions-item>
        <el-descriptions-item label="互动率">{{ form.engagement_rate ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="主页链接" :span="2">
          <a v-if="form.profile_url" :href="form.profile_url" target="_blank">{{ form.profile_url }}</a>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h3>运营信息</h3>
      <el-form :model="profileForm" label-width="100px">
        <el-form-item label="合作政策">
          <el-input v-model="profileForm.cooperation_policy" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="内部备注">
          <el-input v-model="profileForm.internal_notes" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="拍摄风格">
          <el-select
            v-model="profileForm.shooting_style"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="人设特点">
          <el-select
            v-model="profileForm.persona_traits"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="contactPhone" placeholder="手机号" style="width: 240px; margin-right: 12px" />
          <el-input v-model="contactWechat" placeholder="微信号" style="width: 240px" />
        </el-form-item>
      </el-form>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  formatFollowers,
  formatPlatform,
  formatSource,
  getInfluencer,
  updateInfluencer,
  type Influencer,
} from '@/api/influencer'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const form = ref<Influencer | null>(null)

const profileForm = reactive({
  cooperation_policy: '',
  internal_notes: '',
  shooting_style: [] as string[],
  persona_traits: [] as string[],
})

const contactPhone = ref('')
const contactWechat = ref('')

async function loadDetail() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const res = await getInfluencer(id)
    form.value = res.data

    const profile = res.data.profile
    profileForm.cooperation_policy = profile?.cooperation_policy || ''
    profileForm.internal_notes = profile?.internal_notes || ''
    profileForm.shooting_style = profile?.shooting_style || []
    profileForm.persona_traits = profile?.persona_traits || []
    contactPhone.value = (profile?.contact_info?.phone as string) || ''
    contactWechat.value = (profile?.contact_info?.wechat as string) || ''
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.value) return
  saving.value = true
  try {
    await updateInfluencer(form.value.id, {
      profile: {
        cooperation_policy: profileForm.cooperation_policy,
        internal_notes: profileForm.internal_notes,
        shooting_style: profileForm.shooting_style,
        persona_traits: profileForm.persona_traits,
        contact_info: {
          phone: contactPhone.value,
          wechat: contactWechat.value,
        },
      },
    })
    ElMessage.success('保存成功')
    loadDetail()
  } finally {
    saving.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

h3 {
  margin: 0 0 16px;
}
</style>
