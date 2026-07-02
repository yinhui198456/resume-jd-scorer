import axios from 'axios'
import type {
  EvaluationResponse,
  ParseResponse,
  HistoryRecord,
  JDRecord,
  ResumeRecord,
} from './types'

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

export async function evaluatePair(jdId: string, resumeId: string): Promise<EvaluationResponse> {
  const { data } = await api.post<EvaluationResponse>('/evaluate/pair', {
    jd_id: jdId,
    resume_id: resumeId,
  })
  return data
}

export async function parseFile(file: File): Promise<ParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ParseResponse>('/parse', formData)
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

// JD management
export async function listJDs(): Promise<JDRecord[]> {
  const { data } = await api.get<{ records: JDRecord[] }>('/jds')
  return data.records
}

export async function getJD(id: string): Promise<JDRecord> {
  const { data } = await api.get<{ record: JDRecord }>(`/jds/${id}`)
  return data.record
}

export async function createJD(jd: Omit<JDRecord, 'id' | 'created_at'>): Promise<JDRecord> {
  const { data } = await api.post<{ record: JDRecord }>('/jds', jd)
  return data.record
}

export async function updateJD(id: string, jd: Partial<JDRecord>): Promise<JDRecord> {
  const { data } = await api.put<{ record: JDRecord }>(`/jds/${id}`, jd)
  return data.record
}

export async function deleteJD(id: string): Promise<boolean> {
  const { data } = await api.delete<{ deleted: boolean }>(`/jds/${id}`)
  return data.deleted
}

// Resume management
export async function listResumes(): Promise<ResumeRecord[]> {
  const { data } = await api.get<{ records: ResumeRecord[] }>('/resumes')
  return data.records
}

export async function getResume(id: string): Promise<ResumeRecord> {
  const { data } = await api.get<{ record: ResumeRecord }>(`/resumes/${id}`)
  return data.record
}

export async function createResume(
  resume: Omit<ResumeRecord, 'id' | 'created_at'>,
): Promise<ResumeRecord> {
  const { data } = await api.post<{ record: ResumeRecord }>('/resumes', resume)
  return data.record
}

export async function updateResume(id: string, resume: Partial<ResumeRecord>): Promise<ResumeRecord> {
  const { data } = await api.put<{ record: ResumeRecord }>(`/resumes/${id}`, resume)
  return data.record
}

export async function deleteResume(id: string): Promise<boolean> {
  const { data } = await api.delete<{ deleted: boolean }>(`/resumes/${id}`)
  return data.deleted
}

export default api
