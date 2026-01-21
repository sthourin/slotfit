/**
 * Tag API service
 */
import { apiClient } from './api'

export interface Tag {
  id: number
  name: string
  category: string | null
}

export interface TagListResponse {
  tags: Tag[]
  total: number
  skip: number
  limit: number
}

export interface TagCreate {
  name: string
  category?: string | null
}

export const tagsService = {
  /**
   * List all tags
   */
  async list(params?: {
    skip?: number
    limit?: number
    search?: string
    category?: string
  }): Promise<TagListResponse> {
    const queryParams = new URLSearchParams()
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString())
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString())
    if (params?.search) queryParams.append('search', params.search)
    if (params?.category) queryParams.append('category', params.category)

    const response = await apiClient.get<TagListResponse>(`/tags/?${queryParams}`)
    return response.data
  },

  /**
   * Create a new tag (or get existing if name matches)
   */
  async create(tag: TagCreate): Promise<Tag> {
    const response = await apiClient.post<Tag>('/tags/', tag)
    return response.data
  },

  /**
   * Get a tag by ID
   */
  async getById(tagId: number): Promise<Tag> {
    const response = await apiClient.get<Tag>(`/tags/${tagId}`)
    return response.data
  },

  /**
   * Delete a tag
   */
  async delete(tagId: number): Promise<void> {
    await apiClient.delete(`/tags/${tagId}`)
  },

  /**
   * Add a tag to an exercise
   */
  async addToExercise(exerciseId: number, tagName: string): Promise<Tag> {
    const response = await apiClient.post<Tag>(
      `/tags/exercises/${exerciseId}/tags?tag_name=${encodeURIComponent(tagName)}`
    )
    return response.data
  },

  /**
   * Remove a tag from an exercise
   */
  async removeFromExercise(exerciseId: number, tagId: number): Promise<void> {
    await apiClient.delete(`/tags/exercises/${exerciseId}/tags/${tagId}`)
  },

  /**
   * Add a tag to a routine
   */
  async addToRoutine(routineId: number, tagName: string): Promise<Tag> {
    const response = await apiClient.post<Tag>(
      `/tags/routines/${routineId}/tags?tag_name=${encodeURIComponent(tagName)}`
    )
    return response.data
  },

  /**
   * Remove a tag from a routine
   */
  async removeFromRoutine(routineId: number, tagId: number): Promise<void> {
    await apiClient.delete(`/tags/routines/${routineId}/tags/${tagId}`)
  },

  /**
   * Add a tag to a workout
   */
  async addToWorkout(workoutId: number, tagName: string): Promise<Tag> {
    const response = await apiClient.post<Tag>(
      `/tags/workouts/${workoutId}/tags?tag_name=${encodeURIComponent(tagName)}`
    )
    return response.data
  },

  /**
   * Remove a tag from a workout
   */
  async removeFromWorkout(workoutId: number, tagId: number): Promise<void> {
    await apiClient.delete(`/tags/workouts/${workoutId}/tags/${tagId}`)
  },
}
