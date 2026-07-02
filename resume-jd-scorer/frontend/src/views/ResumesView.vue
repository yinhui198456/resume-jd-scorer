<template>
  <div class="resumes-view">
    <div class="page-header">
      <h2>简历管理</h2>
      <button class="btn btn-primary" @click="startCreate">+ 新增简历</button>
    </div>

    <div v-if="editing" class="form-card">
      <h3>{{ form.id ? '编辑简历' : '新增简历' }}</h3>

      <div v-if="!form.id" class="upload-zone" @click="triggerFile" @drop.prevent="handleDrop" @dragover.prevent
        >
        <input ref="fileInput" type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" hidden @change="handleFile" />
        <p>{{ loading.parse ? '解析中...' : '📄 拖拽或点击上传简历文件' }}</p>
        <p class="hint">支持 PDF / Word / 图片 / TXT</p>
      </div>

      <div class="form-row">
        <label>名称 / 候选人姓名</label>
        <input v-model="form.name" type="text" placeholder="例如：张三" />
      </div>
      <div class="form-row">
        <label>联系方式</label>
        <input v-model="form.contact" type="text" placeholder="电话 / 邮箱" />
      </div>
      <div class="form-row">
        <label>工作年限</label>
        <input v-model="form.work_years" type="text" placeholder="例如：5 年" />
      </div>
      <div class="form-row">
        <label>原始文件名</label>
        <input v-model="form.filename" type="text" disabled />
      </div>
      <div class="form-row">
        <label>简历文本（可编辑）</label>
        <textarea v-model="form.content" rows="10" placeholder="解析后的简历文本..." />
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" @click="cancelEdit">取消</button>
        <button class="btn btn-primary" :disabled="loading.save" @click="save">
          {{ loading.save ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div class="list">
      <div v-for="resume in resumes" :key="resume.id" class="list-item">
        <div class="item-main">
          <div class="item-name">{{ resume.name }}</div>
          <div class="item-meta">
            {{ resume.filename }} · {{ resume.contact || '无联系方式' }} · {{ resume.work_years || '未知年限' }}
          </div>
          <div class="item-meta">{{ formatDate(resume.created_at) }}</div>
        </div>
        <div class="item-actions">
          <button class="btn btn-secondary" @click="startEdit(resume)">编辑</button>
          <button class="btn btn-danger" :disabled="loading.delete" @click="remove(resume.id!)">删除</button>
        </div>
      </div>
      <p v-if="!resumes.length" class="empty">暂无简历，点击右上角新增</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { createResume, deleteResume, listResumes, parseFile, updateResume } from '../api'
import { loading, resumes } from '../stores/resumes'
import type { ResumeRecord } from '../types'

const editing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const form = reactive({
  id: '',
  name: '',
  content: '',
  filename: '',
  contact: '',
  work_years: '',
})

onMounted(load)

async function load() {
  loading.list = true
  try {
    resumes.value = await listResumes()
  } finally {
    loading.list = false
  }
}

function startCreate() {
  form.id = ''
  form.name = ''
  form.content = ''
  form.filename = ''
  form.contact = ''
  form.work_years = ''
  editing.value = true
}

function startEdit(resume: ResumeRecord) {
  form.id = resume.id || ''
  form.name = resume.name
  form.content = resume.content
  form.filename = resume.filename
  form.contact = resume.contact || ''
  form.work_years = resume.work_years || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

function triggerFile() {
  fileInput.value?.click()
}

function handleDrop(e: DragEvent) {
  const file = e.dataTransfer?.files[0]
  if (file) parseAndFill(file)
}

function handleFile(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) parseAndFill(file)
}

async function parseAndFill(file: File) {
  loading.parse = true
  try {
    const result = await parseFile(file)
    if (result.success && result.text) {
      form.content = result.text
      form.filename = file.name
      if (!form.name) {
        form.name = file.name.replace(/\.[^/.]+$/, '')
      }
    } else {
      alert(result.error || '简历解析失败')
    }
  } finally {
    loading.parse = false
  }
}

async function save() {
  loading.save = true
  try {
    const payload = {
      name: form.name.trim(),
      content: form.content.trim(),
      filename: form.filename,
      contact: form.contact.trim() || undefined,
      work_years: form.work_years.trim() || undefined,
    }
    if (form.id) {
      await updateResume(form.id, payload)
    } else {
      await createResume(payload)
    }
    await load()
    editing.value = false
  } finally {
    loading.save = false
  }
}

async function remove(id: string) {
  if (!confirm('确定删除这份简历吗？')) return
  loading.delete = true
  try {
    await deleteResume(id)
    await load()
  } finally {
    loading.delete = false
  }
}

function formatDate(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.resumes-view {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.form-card {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.form-card h3 {
  margin: 0 0 16px;
  font-size: 16px;
}

.upload-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 16px;
  background: white;
}

.upload-zone:hover {
  border-color: #1890ff;
}

.upload-zone p {
  margin: 0;
  font-size: 14px;
}

.upload-zone .hint {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}

.form-row {
  margin-bottom: 16px;
}

.form-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #666;
}

.form-row input,
.form-row textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
}

.form-row input:disabled {
  background: #f5f5f5;
  color: #999;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  margin-bottom: 12px;
  background: white;
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 6px;
}

.item-meta {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.empty {
  color: #999;
  text-align: center;
  padding: 40px 0;
}
</style>
