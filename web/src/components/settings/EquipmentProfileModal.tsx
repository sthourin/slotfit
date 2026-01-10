import { useEffect, useState } from 'react'
import { equipmentProfileApi, type EquipmentProfile, type EquipmentProfileCreate, type EquipmentProfileUpdate } from '../../services/equipmentProfiles'
import { equipmentApi, type Equipment } from '../../services/equipment'

interface EquipmentProfileModalProps {
  profile: EquipmentProfile | null
  onClose: () => void
}

function EquipmentProfileModal({ profile, onClose }: EquipmentProfileModalProps) {
  const [name, setName] = useState('')
  const [selectedEquipment, setSelectedEquipment] = useState<number[]>([])
  const [isDefault, setIsDefault] = useState(false)
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchEquipment = async () => {
      try {
        const data = await equipmentApi.list()
        setEquipmentList(data)
      } catch (error) {
        console.error('Failed to fetch equipment:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchEquipment()
  }, [])

  useEffect(() => {
    if (profile) {
      setName(profile.name)
      setSelectedEquipment(profile.equipment_ids)
      setIsDefault(profile.is_default)
    }
  }, [profile])

  const handleToggleEquipment = (equipmentId: number) => {
    setSelectedEquipment((prev) =>
      prev.includes(equipmentId)
        ? prev.filter((id) => id !== equipmentId)
        : [...prev, equipmentId]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      alert('Please enter a profile name')
      return
    }

    setSaving(true)
    try {
      if (profile) {
        // Update existing profile
        const updateData: EquipmentProfileUpdate = {
          name,
          equipment_ids: selectedEquipment,
        }
        await equipmentProfileApi.update(profile.id, updateData)
        // If setting as default, use the set-default endpoint (this clears other defaults)
        if (isDefault && !profile.is_default) {
          await equipmentProfileApi.setDefault(profile.id)
        }
      } else {
        // Create new profile
        const createData: EquipmentProfileCreate = {
          name,
          equipment_ids: selectedEquipment,
          is_default: isDefault,
        }
        await equipmentProfileApi.create(createData)
      }
      onClose()
    } catch (error) {
      console.error('Failed to save equipment profile:', error)
      alert('Failed to save equipment profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Group equipment by category
  const groupedEquipment = equipmentList.reduce((acc, eq) => {
    const category = eq.category || 'Other'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(eq)
    return acc
  }, {} as Record<string, Equipment[]>)

  // Filter equipment by search term
  const filteredGroupedEquipment = Object.entries(groupedEquipment).reduce((acc, [category, items]) => {
    const filtered = items.filter((eq) =>
      eq.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    if (filtered.length > 0) {
      acc[category] = filtered
    }
    return acc
  }, {} as Record<string, Equipment[]>)

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-gray-600">Loading equipment...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {profile ? 'Edit Equipment Profile' : 'Create Equipment Profile'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="px-6 py-4 space-y-4">
            {/* Name Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Profile Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Home Gym, Office Gym"
                required
              />
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Equipment
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Search equipment..."
              />
            </div>

            {/* Equipment Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Equipment ({selectedEquipment.length} selected)
              </label>
              <div className="border border-gray-300 rounded-md max-h-64 overflow-y-auto">
                {Object.keys(filteredGroupedEquipment).length === 0 ? (
                  <div className="p-4 text-gray-500 text-center">No equipment found</div>
                ) : (
                  Object.entries(filteredGroupedEquipment).map(([category, items]) => (
                    <div key={category} className="border-b border-gray-200 last:border-b-0">
                      <div className="px-3 py-2 bg-gray-50 font-medium text-sm text-gray-700">
                        {category}
                      </div>
                      <div className="px-3 py-2">
                        {items.map((eq) => (
                          <label
                            key={eq.id}
                            className="flex items-center py-1 hover:bg-gray-50 cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={selectedEquipment.includes(eq.id)}
                              onChange={() => handleToggleEquipment(eq.id)}
                              className="mr-2"
                            />
                            <span className="text-sm text-gray-900">{eq.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Set as Default */}
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={isDefault}
                  onChange={(e) => setIsDefault(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Set as default profile</span>
              </label>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : profile ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EquipmentProfileModal
