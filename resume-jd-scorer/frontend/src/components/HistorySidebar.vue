<template>
  <aside class="history-sidebar">
    <h3>历史记录</h3>
    <button class="refresh-btn" :disabled="loading" @click="refresh">刷新</button>
    <ul>
      <li
        v-for="record in history"
        :key="record.id"
        class="history-item"
        @click="loadRecord(record)"
      >
        <div class="history-name">{{ record.candidate_name || '未知候选人' }}</div>
        <div class="history-meta">
          {{ formatDate(record.created_at) }} · {{ record.result.final_score }}分
        </div>
        <button class="delete-btn" @click.stop="remove(record.id!)">删除</button>
      </li>
    </ul>
    <p v-if="!history.length" class="empty">暂无历史记录</p>
  </aside>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { deleteHistory, loadHistory } from '../api'
import { evaluation, history, jdText, resumeText, resumeFilename } from '../stores/evaluation'
import type { HistoryRecord } from '../types'

defineProps<{ loading?: boolean }>()

onMounted(refresh)

async function refresh() {
  history.value = await loadHistory()
}

function loadRecord(record: HistoryRecord) {
  jdText.value = record.jd_text
  resumeText.value = record.resume_text
  resumeFilename.value = record.resume_filename
  evaluation.value = record.result
}

async function remove(id: string) {
  if (!confirm('确定删除这条记录吗？')) return
  await deleteHistory(id)
  await refresh()
}

function formatDate(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.history-sidebar {
  width: 220px;
  padding: 16px;
  border-right: 1px solid #f0f0f0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

h3 {
  margin: 0;
  font-size: 16px;
}

.refresh-btn {
  padding: 6px 12px;
  background: #fafafa;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  padding: 10px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
}

.history-item:hover {
  background: #f6ffed;
}

.history-name {
  font-weight: bold;
  font-size: 14px;
}

.history-meta {
  font-size: 12px;
  color: #666;
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 12px;
  color: #ff4d4f;
  background: transparent;
  border: none;
  cursor: pointer;
  display: none;
}

.history-item:hover .delete-btn {
  display: block;
}

.empty {
  color: #999;
  font-size: 13px;
}
</style>
