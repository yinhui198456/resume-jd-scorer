<template>
  <div class="input-panel">
    <h2>JD 输入</h2>
    <textarea
      v-model="jdText"
      placeholder="请粘贴 JD 文本..."
      rows="12"
      class="jd-textarea"
    ></textarea>

    <h2>简历输入</h2>
    <div
      class="upload-zone"
      :class="{ dragging }"
      @dragenter.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx,.doc,.txt,image/*"
        hidden
        @change="handleFileSelect"
      />
      <p v-if="resumeFilename">已选择：{{ resumeFilename }}</p>
      <p v-else>📄 拖拽或点击上传简历文件<br />支持 PDF / Word / 图片</p>
    </div>

    <textarea
      v-model="resumeText"
      placeholder="[解析后的简历文本预览区]"
      rows="12"
      class="resume-textarea"
    ></textarea>

    <button class="evaluate-btn" :disabled="loading.evaluate" @click="onEvaluate">
      {{ loading.evaluate ? '评估中...' : '开始评估' }}
    </button>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { evaluate as apiEvaluate, parseFile } from '../api'
import { jdText, resumeText, resumeFilename, evaluation, loading, error } from '../stores/evaluation'

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFile(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  await parseResume(file)
}

const handleFileSelect = handleFile

async function handleDrop(event: DragEvent) {
  dragging.value = false
  const file = event.dataTransfer?.files[0]
  if (!file) return
  await parseResume(file)
}

async function parseResume(file: File) {
  loading.parse = true
  error.value = ''
  try {
    const result = await parseFile(file)
    if (!result.success || !result.text) {
      error.value = result.error || '文件解析失败'
      return
    }
    resumeText.value = result.text
    resumeFilename.value = result.name || file.name
  } catch (e) {
    error.value = '文件解析请求失败'
  } finally {
    loading.parse = false
  }
}

async function onEvaluate() {
  if (!jdText.value.trim() || !resumeText.value.trim()) {
    error.value = '请填写 JD 并上传简历'
    return
  }
  loading.evaluate = true
  error.value = ''
  try {
    const response = await apiEvaluate(jdText.value, resumeText.value)
    if (!response.success || !response.result) {
      error.value = response.error || '评估失败'
      return
    }
    evaluation.value = response.result
  } catch (e) {
    error.value = '评估请求失败，请确认后端服务已启动'
  } finally {
    loading.evaluate = false
  }
}
</script>

<style scoped>
.input-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

h2 {
  margin: 0 0 4px;
  font-size: 16px;
}

textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.upload-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-zone:hover,
.upload-zone.dragging {
  border-color: #1890ff;
  background: #f0f7ff;
}

.evaluate-btn {
  padding: 12px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
}

.evaluate-btn:disabled {
  background: #91caff;
  cursor: not-allowed;
}

.error {
  color: #ff4d4f;
  margin: 0;
}
</style>
