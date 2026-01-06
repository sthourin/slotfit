/**
 * Base API client configuration
 */
import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Custom params serializer to handle arrays correctly for FastAPI
const paramsSerializer = (params: any): string => {
  const searchParams = new URLSearchParams()
  
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) {
      continue
    }
    
    if (Array.isArray(value)) {
      // FastAPI expects array params as repeated query params: ?key=1&key=2
      value.forEach((item) => {
        searchParams.append(key, String(item))
      })
    } else {
      searchParams.append(key, String(value))
    }
  }
  
  return searchParams.toString()
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  paramsSerializer: {
    serialize: paramsSerializer,
  },
})

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Improve error messages
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      error.message = 'Network Error: Cannot connect to server. Please ensure the backend is running at http://localhost:8000'
    } else if (error.response) {
      // Server responded with error status
      const responseData = error.response.data as any
      
      // FastAPI validation errors can be:
      // - String: { "detail": "Error message" }
      // - Array: { "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }
      if (responseData?.detail) {
        if (Array.isArray(responseData.detail)) {
          // Format validation errors nicely
          const errors = responseData.detail.map((err: any) => {
            const field = err.loc?.join('.') || 'field'
            return `${field}: ${err.msg}`
          }).join(', ')
          error.message = `Validation Error: ${errors}`
        } else {
          error.message = String(responseData.detail)
        }
      } else if (responseData?.message) {
        error.message = String(responseData.message)
      }
    }
    return Promise.reject(error)
  }
)

// Shared types
export interface MuscleGroup {
  id: number
  name: string
  level: number
  parent_id: number | null
}

export interface Equipment {
  id: number
  name: string
  category: string | null
}
