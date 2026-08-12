/**
 * Exercise suggestion API service
 */
import { apiClient } from './api'
import type { Target } from './sessions'

export interface SuggestionCard {
  exercise_id: number
  exercise_name: string
  pattern_id: number
  pattern_slug: string
  equipment_name: string | null
  is_bodyweight: boolean
  last_performed: string | null
  is_staple: boolean
  target: Target | null
}

export interface NotRecommendedEntry {
  exercise_name: string
  reason: string
}

export interface AnchorGroup {
  pattern: { id: number; slug: string; name: string }
  covered: boolean
  staples: SuggestionCard[]
}

export interface AnchorSuggestions {
  groups: AnchorGroup[]
  /** Patterns this day plan does not ask for, offered below its own groups. */
  other_groups: AnchorGroup[]
  not_recommended: NotRecommendedEntry[]
}

export interface PartnerSuggestions {
  candidates: SuggestionCard[]
  novelty: SuggestionCard | null
  not_recommended: NotRecommendedEntry[]
}

export async function getAnchorSuggestions(sessionId: number): Promise<AnchorSuggestions> {
  const { data } = await apiClient.get('/suggestions/anchors', { params: { session_id: sessionId } })
  return data
}

export async function getPartnerSuggestions(
  sessionId: number,
  anchorExerciseId: number,
  position: 2 | 3
): Promise<PartnerSuggestions> {
  const { data } = await apiClient.get('/suggestions/partners', {
    params: { session_id: sessionId, anchor_exercise_id: anchorExerciseId, position },
  })
  return data
}
