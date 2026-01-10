import { useEffect, useState } from 'react'
import { equipmentProfileApi, type EquipmentProfile } from '../../services/equipmentProfiles'
import EquipmentProfileModal from './EquipmentProfileModal'

interface EquipmentProfilesSectionProps {
  onUpdate?: () => void
}

function EquipmentProfilesSection({ onUpdate }: EquipmentProfilesSectionProps) {
  const [profiles, setProfiles] = useState<EquipmentProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingProfile, setEditingProfile] = useState<EquipmentProfile | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const fetchProfiles = async () => {
    setLoading(true)
    try {
      const data = await equipmentProfileApi.list()
      setProfiles(data)
    } catch (error) {
      console.error('Failed to fetch equipment profiles:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfiles()
  }, [])

  const handleCreate = () => {
    setEditingProfile(null)
    setShowModal(true)
  }

  const handleEdit = (profile: EquipmentProfile) => {
    setEditingProfile(profile)
    setShowModal(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this equipment profile?')) {
      return
    }

    setDeletingId(id)
    try {
      await equipmentProfileApi.delete(id)
      await fetchProfiles()
      onUpdate?.()
    } catch (error) {
      console.error('Failed to delete equipment profile:', error)
      alert('Failed to delete equipment profile. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleSetDefault = async (id: number) => {
    try {
      await equipmentProfileApi.setDefault(id)
      await fetchProfiles()
      onUpdate?.()
    } catch (error) {
      console.error('Failed to set default profile:', error)
      alert('Failed to set default profile. Please try again.')
    }
  }

  const handleModalClose = () => {
    setShowModal(false)
    setEditingProfile(null)
    fetchProfiles()
    onUpdate?.()
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-gray-600">Loading equipment profiles...</div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Equipment Profiles</h2>
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
          >
            <svg className="h-5 w-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Profile
          </button>
        </div>

        {profiles.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No equipment profiles yet. Create one to get started.
          </div>
        ) : (
          <div className="space-y-3">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-md hover:bg-gray-50"
              >
                <div className="flex items-center space-x-3">
                  {profile.is_default && (
                    <svg className="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  )}
                  <div>
                    <div className="font-medium text-gray-900">{profile.name}</div>
                    <div className="text-sm text-gray-500">
                      {profile.equipment_ids.length} equipment item{profile.equipment_ids.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {!profile.is_default && (
                    <button
                      onClick={() => handleSetDefault(profile.id)}
                      className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900"
                      title="Set as default"
                    >
                      Set Default
                    </button>
                  )}
                  <button
                    onClick={() => handleEdit(profile)}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(profile.id)}
                    disabled={deletingId === profile.id}
                    className="px-3 py-1 text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
                  >
                    {deletingId === profile.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <EquipmentProfileModal
          profile={editingProfile}
          onClose={handleModalClose}
        />
      )}
    </>
  )
}

export default EquipmentProfilesSection
