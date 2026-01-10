import { useState } from 'react'
import { useUserStore } from '../../stores/userStore'
import { getDeviceId } from '../../services/api'

function ProfileSection() {
  const { user, updateProfile, loading } = useUserStore()
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [preferredUnits, setPreferredUnits] = useState<'lbs' | 'kg'>(user?.preferred_units || 'lbs')
  const [showDeviceId, setShowDeviceId] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)

  const handleSave = async () => {
    if (!user) return

    setSaveLoading(true)
    try {
      await updateProfile({
        display_name: displayName,
        preferred_units: preferredUnits,
      })
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update profile:', error)
      alert('Failed to update profile. Please try again.')
    } finally {
      setSaveLoading(false)
    }
  }

  const handleCancel = () => {
    setDisplayName(user?.display_name || '')
    setPreferredUnits(user?.preferred_units || 'lbs')
    setIsEditing(false)
  }

  if (!user) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile</h2>

      <div className="space-y-4">
        {/* Display Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Display Name
          </label>
          {isEditing ? (
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your display name"
            />
          ) : (
            <div className="text-gray-900">{user.display_name}</div>
          )}
        </div>

        {/* Preferred Units */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Preferred Units
          </label>
          {isEditing ? (
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="lbs"
                  checked={preferredUnits === 'lbs'}
                  onChange={(e) => setPreferredUnits(e.target.value as 'lbs' | 'kg')}
                  className="mr-2"
                />
                <span>Pounds (lbs)</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="kg"
                  checked={preferredUnits === 'kg'}
                  onChange={(e) => setPreferredUnits(e.target.value as 'lbs' | 'kg')}
                  className="mr-2"
                />
                <span>Kilograms (kg)</span>
              </label>
            </div>
          ) : (
            <div className="text-gray-900">{user.preferred_units === 'lbs' ? 'Pounds (lbs)' : 'Kilograms (kg)'}</div>
          )}
        </div>

        {/* Device ID (for debugging) */}
        <div>
          <button
            type="button"
            onClick={() => setShowDeviceId(!showDeviceId)}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center"
          >
            <span>{showDeviceId ? 'Hide' : 'Show'} Device ID</span>
            <svg
              className={`ml-1 h-4 w-4 transition-transform ${showDeviceId ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showDeviceId && (
            <div className="mt-2 p-3 bg-gray-50 rounded-md text-sm font-mono text-gray-600 break-all">
              {getDeviceId()}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3 pt-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saveLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saveLoading ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleCancel}
                disabled={saveLoading}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Edit Profile
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProfileSection
