/**
 * Movement pattern API service
 */
import { apiClient } from './api'

export interface MovementPattern {
  id: number
  slug: string
  name: string
  opposite_pattern_id: number | null
  is_neutral: boolean
  display_order: number
}

export interface TrendPoint {
  week_start: string
  index: number
}

export interface PatternProgress {
  pattern_id: number
  slug: string
  name: string
  trend: TrendPoint[]
}

export async function listPatterns(): Promise<MovementPattern[]> {
  const { data } = await apiClient.get('/patterns/')
  return data
}

export async function getPatternProgress(weeks = 12): Promise<PatternProgress[]> {
  const { data } = await apiClient.get('/patterns/progress', { params: { weeks } })
  return data
}
