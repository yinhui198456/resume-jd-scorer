import { reactive, ref } from 'vue'
import type { ResumeRecord } from '../types'

export const resumes = ref<ResumeRecord[]>([])
export const currentResume = ref<ResumeRecord | null>(null)
export const loading = reactive({
  list: false,
  save: false,
  delete: false,
  parse: false,
})
export const error = ref('')
