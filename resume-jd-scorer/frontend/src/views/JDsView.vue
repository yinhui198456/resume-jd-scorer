<template>
  <div class="jds-view">
    <div class="page-header">
      <h2>JD 管理</h2>
      <button class="btn btn-primary" @click="startCreate">+ 新增 JD</button>
    </div>

    <div v-if="editing" class="form-card">
      <h3>{{ form.id ? '编辑 JD' : '新增 JD' }}</h3>
      <div class="form-row">
        <label>名称</label>
        <input v-model="form.name" type="text" placeholder="例如：高级 Java 后端" />
      </div>
      <div class="form-row">
        <label>标签（逗号分隔）</label>
        <input v-model="form.tagsText" type="text" placeholder="后端, Java, 电商" />
      </div>
      <div class="form-row">
        <label>JD 内容</label>
        <textarea v-model="form.content" rows="10" placeholder="请粘贴 JD 文本..." />
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" @click="cancelEdit">取消</button>
        <button class="btn btn-primary" :disabled="loading.save" @click="save">
          {{ loading.save ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div class="list">
      <div v-for="jd in jds" :key="jd.id" class="list-item">
        <div class="item-main">
          <div class="item-name">{{ jd.name }}</div>
          <div class="item-tags">
            <span v-for="tag in jd.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div class="item-meta">{{ formatDate(jd.created_at) }}</div>
        </div>
        <div class="item-actions">
          <button class="btn btn-secondary" @click="startEdit(jd)">编辑</button>
          <button class="btn btn-danger" :disabled="loading.delete" @click="remove(jd.id!)">删除</button>
        </div>
      </div>
      <p v-if="!jds.length" class="empty">暂无 JD，点击右上角新增</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { createJD, deleteJD, listJDs, updateJD } from '../api'
import { jds, loading } from '../stores/jds'
import type { JDRecord } from '../types'

const editing = ref(false)
const form = reactive({
  id: '',
  name: '',
  content: '',
  tagsText: '',
})

onMounted(load)

async function load() {
  loading.list = true
  try {
    jds.value = await listJDs()
  } finally {
    loading.list = false
  }
}

function startCreate() {
  form.id = ''
  form.name = ''
  form.content = ''
  form.tagsText = ''
  editing.value = true
}

function startEdit(jd: JDRecord) {
  form.id = jd.id || ''
  form.name = jd.name
  form.content = jd.content
  form.tagsText = (jd.tags || []).join(', ')
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

function parseTags(text: string): string[] {
  return text
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
}

async function save() {
  loading.save = true
  try {
    const payload = {
      name: form.name.trim(),
      content: form.content.trim(),
      tags: parseTags(form.tagsText),
    }
    if (form.id) {
      await updateJD(form.id, payload)
    } else {
      await createJD(payload)
    }
    await load()
    editing.value = false
  } finally {
    loading.save = false
  }
}

async function remove(id: string) {
  if (!confirm('确定删除这条 JD 吗？')) return
  loading.delete = true
  try {
    await deleteJD(id)
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
.jds-view {
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

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.tag {
  font-size: 12px;
  padding: 2px 8px;
  background: #e6f7ff;
  color: #1890ff;
  border-radius: 4px;
}

.item-meta {
  font-size: 12px;
  color: #999;
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
