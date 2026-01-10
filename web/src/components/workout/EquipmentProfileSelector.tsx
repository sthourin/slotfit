/**
 * Equipment Profile Selector Component
 * Displays equipment profiles for selection
 */
import { useState, useEffect } from 'react'
import { useEquipmentStore } from '../../stores/equipmentStore'

interface EquipmentProfileSelectorProps {
  selectedProfileId: number | null
  onSelectProfile: (profileId: number | null) => void
}

export default function EquipmentProfileSelector({
  selectedProfileId,
  onSelectProfile,
}: EquipmentProfileSelectorProps) {
  const { profiles, loading, loadProfiles, defaultProfileId } = useEquipmentStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (profiles.length === 0) {
      loadProfiles().catch((err) => {
        console.error('Failed to load equipment profiles:', err)
        setError('Failed to load equipment profiles')
      })
    }
  }, [profiles.length, loadProfiles])

  // Auto-select default profile if none selected
  useEffect(() => {
    if (defaultProfileId && !selectedProfileId) {
      onSelectProfile(defaultProfileId)
    }
  }, [defaultProfileId, selectedProfileId, onSelectProfile])

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-sm text-gray-600">Loading equipment profiles...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-4">
        <p className="text-red-600 text-sm mb-2">{error}</p>
        <button
          onClick={() => {
            setError(null)
            loadProfiles()
          }}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (profiles.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-gray-600 text-sm mb-2">No equipment profiles found.</p>
        <p className="text-xs text-gray-500">
          Create a profile in{' '}
          <a href="/settings" className="text-blue-600 hover:underline">
            Settings
          </a>
          .
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {profiles.map((profile) => (
        <button
          key={profile.id}
          onClick={() => onSelectProfile(profile.id)}
          className={`w-full text-left p-4 border-2 rounded-lg transition-colors ${
            selectedProfileId === profile.id
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{profile.name}</span>
                {profile.is_default && (
                  <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                    Default
                  </span>
                )}
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {profile.equipment_ids.length} piece
                {profile.equipment_ids.length !== 1 ? 's' : ''} of equipment
              </div>
            </div>
            {selectedProfileId === profile.id && (
              <div className="ml-4 text-blue-600">
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            )}
          </div>
        </button>
      ))}
      
      {/* Option to use no equipment profile */}
      <button
        onClick={() => onSelectProfile(null)}
        className={`w-full text-left p-4 border-2 rounded-lg transition-colors ${
          selectedProfileId === null
            ? 'border-blue-600 bg-blue-50'
            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
        }`}
      >
        <div className="flex items-center justify-between">
          <div>
            <span className="font-semibold">All Equipment Available</span>
            <div className="text-sm text-gray-600 mt-1">
              No equipment restrictions
            </div>
          </div>
          {selectedProfileId === null && (
            <div className="ml-4 text-blue-600">
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          )}
        </div>
      </button>
    </div>
  )
}
