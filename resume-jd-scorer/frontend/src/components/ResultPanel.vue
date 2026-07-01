<template>
  <div v-if="evaluation" class="result-panel">
    <div class="score-card">
      <div class="score-value">{{ evaluation.final_score }}</div>
      <div class="score-label">总分 / 100</div>
      <div class="recommendation" :class="recommendationClass">
        {{ recommendationLabel }}
      </div>
    </div>

    <section>
      <h3>各维度评分</h3>
      <div class="dimension-list">
        <div
          v-for="(dim, key) in evaluation.dimensions"
          :key="key"
          class="dimension-item"
        >
          <div class="dimension-header">
            <span>{{ dimensionLabel(key) }}</span>
            <span class="dimension-score">{{ dim.score }} / {{ dim.max_score }}</span>
          </div>
          <div class="dimension-bar">
            <div
              class="dimension-bar-fill"
              :style="{ width: `${(dim.score / dim.max_score) * 100}%` }"
            ></div>
          </div>
          <p class="dimension-evidence">{{ dim.evidence }}</p>
        </div>
      </div>
    </section>

    <section>
      <h3>优势</h3>
      <ul>
        <li v-for="(s, i) in evaluation.strengths" :key="i">{{ s }}</li>
      </ul>
    </section>

    <section>
      <h3>短板</h3>
      <ul>
        <li v-for="(w, i) in evaluation.weaknesses" :key="i">{{ w }}</li>
      </ul>
    </section>

    <section v-if="evaluation.red_flags.length">
      <h3>红旗信号</h3>
      <ul class="red-flags">
        <li v-for="(f, i) in evaluation.red_flags" :key="i">{{ f }}</li>
      </ul>
    </section>

    <section>
      <h3>总结</h3>
      <p>{{ evaluation.summary }}</p>
    </section>
  </div>
  <div v-else class="empty-state">
    暂无评估结果，请在左侧输入 JD 并上传简历后点击"开始评估"。
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { evaluation } from '../stores/evaluation'

const recommendationLabel = computed(() => {
  const rec = evaluation.value?.recommendation
  if (rec === 'INTERVIEW') return '建议面试'
  if (rec === 'BACKUP') return '备选'
  return '不建议'
})

const recommendationClass = computed(() => {
  const rec = evaluation.value?.recommendation
  if (rec === 'INTERVIEW') return 'interview'
  if (rec === 'BACKUP') return 'backup'
  return 'reject'
})

function dimensionLabel(key: string): string {
  const labels: Record<string, string> = {
    hard_requirement: '硬性要求匹配度',
    skill_match: '技能匹配度',
    experience_match: '经验匹配度',
    bonus_potential: '潜力/加分项',
  }
  return labels[key] || key
}
</script>

<style scoped>
.result-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.score-card {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.score-value {
  font-size: 48px;
  font-weight: bold;
  color: #52c41a;
}

.score-label {
  color: #666;
}

.recommendation {
  margin-top: 8px;
  padding: 4px 12px;
  border-radius: 12px;
  display: inline-block;
  font-weight: bold;
}

.recommendation.interview {
  background: #52c41a;
  color: white;
}

.recommendation.backup {
  background: #faad14;
  color: white;
}

.recommendation.reject {
  background: #ff4d4f;
  color: white;
}

section h3 {
  margin: 0 0 8px;
  font-size: 16px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 4px;
}

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dimension-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.dimension-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin: 4px 0;
}

.dimension-bar-fill {
  height: 100%;
  background: #1890ff;
  border-radius: 4px;
}

.dimension-evidence {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.red-flags li {
  color: #ff4d4f;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: #999;
}
</style>
