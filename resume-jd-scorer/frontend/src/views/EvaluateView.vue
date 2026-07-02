<template>
  <div class="evaluate-view">
    <div class="selector-bar">
      <div class="selector-group">
        <label>选择 JD</label>
        <select v-model="selectedJDId" @change="onJDChange">
          <option value="">-- 直接输入 --</option>
          <option v-for="jd in jds" :key="jd.id" :value="jd.id">{{ jd.name }}</option>
        </select>
        <router-link to="/jds" class="link">管理 JD</router-link>
      </div>

      <div class="selector-group">
        <label>选择简历</label>
        <select v-model="selectedResumeId" @change="onResumeChange">
          <option value="">-- 直接上传 --</option>
          <option v-for="resume in resumes" :key="resume.id" :value="resume.id">{{ resume.name }}</option>
        </select>
        <router-link to="/resumes" class="link">管理简历</router-link>
      </div>

      <button v-if="evaluation" class="btn btn-primary" :disabled="loading.save" @click="save">
        {{ loading.save ? '保存中...' : '保存到历史' }}
      </button>
    </div>

    <div class="evaluate-body">
      <HistorySidebar />
      <div class="input-section">
        <InputPanel />
      </div>
      <div class="result-section">
        <ResultPanel />
        <QuestionList />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listJDs, listResumes, saveHistory } from '../api'
import HistorySidebar from '../components/HistorySidebar.vue'
import InputPanel from '../components/InputPanel.vue'
import QuestionList from '../components/QuestionList.vue'
import ResultPanel from '../components/ResultPanel.vue'
import { evaluation, jdText, loading, resumeFilename, resumeText } from '../stores/evaluation'
import { jds } from '../stores/jds'
import { resumes } from '../stores/resumes'

const selectedJDId = ref('')
const selectedResumeId = ref('')

onMounted(async () => {
  try {
    jds.value = await listJDs()
    resumes.value = await listResumes()
  } catch (e) {
    console.error('Failed to load JDs or resumes', e)
  }
})

function onJDChange() {
  const jd = jds.value.find((j) => j.id === selectedJDId.value)
  if (jd) {
    jdText.value = jd.content
  }
}

function onResumeChange() {
  const resume = resumes.value.find((r) => r.id === selectedResumeId.value)
  if (resume) {
    resumeText.value = resume.content
    resumeFilename.value = resume.filename
  }
}

async function save() {
  if (!evaluation.value) return
  loading.save = true
  try {
    await saveHistory({
      candidate_name: '',
      resume_filename: resumeFilename.value,
      jd_text: jdText.value,
      resume_text: resumeText.value,
      result: evaluation.value,
    })
    alert('保存成功')
  } catch (e) {
    alert('保存失败')
  } finally {
    loading.save = false
  }
}
</script>

<style scoped>
.evaluate-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.selector-bar {
  height: 56px;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 24px;
  background: white;
  flex-shrink: 0;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-group label {
  font-size: 14px;
  color: #666;
}

.selector-group select {
  padding: 6px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  min-width: 160px;
}

.link {
  font-size: 13px;
  color: #1890ff;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.evaluate-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.input-section,
.result-section {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.input-section {
  border-right: 1px solid #f0f0f0;
}

.result-section {
  background: #fafafa;
}
</style>
