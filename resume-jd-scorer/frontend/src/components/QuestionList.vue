<template>
  <section v-if="evaluation" class="question-list">
    <h3>面试题（{{ evaluation.follow_up_questions.length }} 道）</h3>
    <button
      v-if="evaluation.follow_up_questions.length"
      class="generate-answers-btn"
      :disabled="loading.answers"
      @click="loadAnswers"
    >
      {{ loading.answers ? '生成中...' : '生成建议答案' }}
    </button>

    <div
      v-for="(q, index) in evaluation.follow_up_questions"
      :key="index"
      class="question-item"
    >
      <div class="question-header" @click="toggle(index)">
        <span class="question-type">{{ typeLabel(q.question_type) }}</span>
        <span class="question-text">{{ index + 1 }}. {{ q.question }}</span>
        <span class="toggle-icon">{{ expanded[index] ? '▼' : '▶' }}</span>
      </div>
      <div v-if="expanded[index]" class="question-body">
        <p class="intent"><strong>意图：</strong>{{ q.intent }}</p>
        <div v-if="answers[index]" class="answer">
          <strong>建议答案/考察要点：</strong>
          <pre>{{ answers[index] }}</pre>
        </div>
        <div v-else class="answer-placeholder">点击上方"生成建议答案"按钮获取参考</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { generateAnswers } from '../api'
import { evaluation, answers, jdText, resumeText, loading } from '../stores/evaluation'

const expanded = reactive<Record<number, boolean>>({})

function toggle(index: number) {
  expanded[index] = !expanded[index]
}

function typeLabel(type: string): string {
  const labels: Record<string, string> = {
    verification: '验证',
    technical: '技术',
    scenario: '场景',
    comprehensive: '综合',
  }
  return labels[type] || type
}

async function loadAnswers() {
  if (!evaluation.value) return
  const questions = evaluation.value.follow_up_questions.map(q => q.question)
  if (!questions.length) return
  loading.answers = true
  try {
    const result = await generateAnswers(jdText.value, resumeText.value, questions)
    result.forEach((answer, idx) => {
      answers.value[idx] = answer
    })
  } catch (e) {
    alert('建议答案生成失败')
  } finally {
    loading.answers = false
  }
}
</script>

<style scoped>
.question-list {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
}

.generate-answers-btn {
  margin-bottom: 12px;
  padding: 8px 16px;
  background: #52c41a;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.generate-answers-btn:disabled {
  background: #b7eb8f;
  cursor: not-allowed;
}

.question-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}

.question-header {
  padding: 10px 12px;
  background: #fafafa;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.question-type {
  font-size: 12px;
  padding: 2px 6px;
  background: #e6f7ff;
  color: #1890ff;
  border-radius: 4px;
  white-space: nowrap;
}

.question-text {
  flex: 1;
  font-size: 14px;
}

.toggle-icon {
  color: #999;
}

.question-body {
  padding: 12px;
  font-size: 14px;
}

.intent {
  color: #666;
  margin: 0 0 8px;
}

.answer pre {
  background: #f6ffed;
  padding: 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}

.answer-placeholder {
  color: #999;
  font-style: italic;
}
</style>
