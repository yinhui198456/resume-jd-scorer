export interface DimensionScore {
  score: number
  max_score: number
  weight: number
  evidence: string
}

export interface FollowUpQuestion {
  question: string
  dimension: string
  intent: string
  question_type: 'verification' | 'technical' | 'scenario' | 'comprehensive'
}

export interface EvaluationResult {
  base_score: number
  credibility_tier: string
  credibility_multiplier: number
  final_score: number
  recommendation: 'INTERVIEW' | 'BACKUP' | 'REJECT'
  dimensions: Record<string, DimensionScore>
  strengths: string[]
  weaknesses: string[]
  red_flags: string[]
  follow_up_questions: FollowUpQuestion[]
  summary: string
}

export interface EvaluationResponse {
  success: boolean
  result?: EvaluationResult
  error?: string
}

export interface ParseResponse {
  success: boolean
  type?: string
  name?: string
  text?: string
  error?: string
}

export interface HistoryRecord {
  id?: string
  created_at?: string
  candidate_name: string
  resume_filename: string
  jd_text: string
  resume_text: string
  result: EvaluationResult
}

export interface JDRecord {
  id?: string
  created_at?: string
  name: string
  content: string
  tags: string[]
}

export interface ResumeRecord {
  id?: string
  created_at?: string
  name: string
  content: string
  filename: string
  contact?: string
  work_years?: string
}
