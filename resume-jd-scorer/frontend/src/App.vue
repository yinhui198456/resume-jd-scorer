<template>
  <div class="app">
    <header class="app-header">
      <h1>简历 JD 评估器</h1>
      <button v-if="evaluation" class="save-btn" :disabled="loading.save" @click="save">
        {{ loading.save ? '保存中...' : '保存到历史' }}
      </button>
    </header>
    <main class="app-body">
      <HistorySidebar />
      <div class="input-section">
        <InputPanel />
      </div>
      <div class="result-section">
        <ResultPanel />
        <QuestionList />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { evaluation, jdText, resumeFilename, resumeText, loading } from './stores/evaluation'
import { saveHistory } from './api'
import HistorySidebar from './components/HistorySidebar.vue'
import InputPanel from './components/InputPanel.vue'
import QuestionList from './components/QuestionList.vue'
import ResultPanel from './components/ResultPanel.vue'

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

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #333;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  height: 56px;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-header h1 {
  margin: 0;
  font-size: 18px;
}

.save-btn {
  padding: 6px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.save-btn:disabled {
  background: #91caff;
}

.app-body {
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
