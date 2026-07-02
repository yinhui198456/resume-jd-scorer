import axios from 'axios'
import type { EvaluationResponse, ParseResponse, HistoryRecord } from './types'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function evaluate(jdText: string, resumeText: string): Promise<EvaluationResponse> {
  const { data } = await api.post<EvaluationResponse>('/evaluate', {
    jd_text: jdText,
    resume_text: resumeText,
  })
  return data
}

export async function parseFile(file: File): Promise<ParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ParseResponse>('/parse', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export async function generateAnswers(
  jdText: string,
  resumeText: string,
  questions: string[],
): Promise<string[]> {
  const { data } = await api.post<{ answers: string[] }>('/answers', {
    jd_text: jdText,
    resume_text: resumeText,
    questions,
  })
  return data.answers
}

export async function loadHistory(): Promise<HistoryRecord[]> {
  const { data } = await api.get<{ records: HistoryRecord[] }>('/history')
  return data.records
}

export async function saveHistory(record: HistoryRecord): Promise<HistoryRecord> {
  const { data } = await api.post<{ record: HistoryRecord }>('/history', record)
  return data.record
}

export async function deleteHistory(id: string): Promise<boolean> {
  const { data } = await api.delete<{ deleted: boolean }>(`/history/${id}`)
  return data.deleted
}

export default api
