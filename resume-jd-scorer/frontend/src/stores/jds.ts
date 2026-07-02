import { reactive, ref } from 'vue'
import type { JDRecord } from '../types'

export const jds = ref<JDRecord[]>([])
export const currentJD = ref<JDRecord | null>(null)
export const loading = reactive({
  list: false,
  save: false,
  delete: false,
})
export const error = ref('')
