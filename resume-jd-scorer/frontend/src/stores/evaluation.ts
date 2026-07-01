import { reactive, ref } from 'vue'
import type { EvaluationResult, HistoryRecord } from '../types'

export const jdText = ref('')
export const resumeText = ref('')
export const resumeFilename = ref('')
export const evaluation = ref<EvaluationResult | null>(null)
export const answers = ref<Record<number, string>>({})
export const history = ref<HistoryRecord[]>([])
export const loading = reactive({
  parse: false,
  evaluate: false,
  answers: false,
  save: false,
})
export const error = ref('')
