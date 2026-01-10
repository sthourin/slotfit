import { useEffect, useState } from 'react'
import { injuryApi, type UserInjury } from '../../services/injuries'
import AddInjuryModal from './AddInjuryModal'

interface InjuriesSectionProps {
  onUpdate?: () => void
}

function InjuriesSection({ onUpdate }: InjuriesSectionProps) {
  const [activeInjuries, setActiveInjuries] = useState<UserInjury[]>([])
  const [healedInjuries, setHealedInjuries] = useState<UserInjury[]>([])
  const [loading, setLoading] = useState(true)
  const [showHealed, setShowHealed] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingInjury, setEditingInjury] = useState<UserInjury | null>(null)

  const fetchInjuries = async () => {
    setLoading(true)
    try {
      const active = await injuryApi.listUserInjuries(true)
      const healed = await injuryApi.listUserInjuries(false)
      setActiveInjuries(active)
      setHealedInjuries(healed.filter((i) => !i.is_active))
    } catch (error) {
      console.error('Failed to fetch injuries:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInjuries()
  }, [])

  const handleAdd = () => {
    setEditingInjury(null)
    setShowModal(true)
  }

  const handleEdit = (injury: UserInjury) => {
    setEditingInjury(injury)
    setShowModal(true)
  }

  const handleMarkHealed = async (id: number) => {
    try {
      await injuryApi.updateUserInjury(id, { is_active: false })
      await fetchInjuries()
      onUpdate?.()
    } catch (error) {
      console.error('Failed to mark injury as healed:', error)
      alert('Failed to update injury. Please try again.')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to remove this injury from your profile?')) {
      return
    }

    try {
      await injuryApi.deleteUserInjury(id)
      await fetchInjuries()
      onUpdate?.()
    } catch (error) {
      console.error('Failed to delete injury:', error)
      alert('Failed to delete injury. Please try again.')
    }
  }

  const handleModalClose = () => {
    setShowModal(false)
    setEditingInjury(null)
    fetchInjuries()
    onUpdate?.()
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'mild':
        return 'bg-green-100 text-green-800'
      case 'moderate':
        return 'bg-yellow-100 text-yellow-800'
      case 'severe':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-gray-600">Loading injuries...</div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {/* Disclaimer */}
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">
            <strong>Disclaimer:</strong> This feature helps you avoid potentially problematic exercises but is{' '}
            <strong>not medical advice</strong>. Please consult a healthcare professional for injury management.
          </p>
        </div>

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Injuries</h2>
          <button
            onClick={handleAdd}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
          >
            <svg className="h-5 w-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Injury
          </button>
        </div>

        {/* Active Injuries */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Active Injuries</h3>
          {activeInjuries.length === 0 ? (
            <div className="text-gray-500 text-center py-4">No active injuries</div>
          ) : (
            <div className="space-y-3">
              {activeInjuries.map((injury) => (
                <div
                  key={injury.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getSeverityColor(injury.severity)}`}>
                      {injury.severity}
                    </span>
                    <div>
                      <div className="font-medium text-gray-900">{injury.injury_type.name}</div>
                      {injury.notes && <div className="text-sm text-gray-500">{injury.notes}</div>}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleEdit(injury)}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleMarkHealed(injury.id)}
                      className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900"
                    >
                      Mark Healed
                    </button>
                    <button
                      onClick={() => handleDelete(injury.id)}
                      className="px-3 py-1 text-sm text-red-600 hover:text-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Healed Injuries */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-700">Healed Injuries</h3>
            <button
              onClick={() => setShowHealed(!showHealed)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showHealed ? 'Hide' : 'Show'} ({healedInjuries.length})
            </button>
          </div>
          {showHealed && (
            <>
              {healedInjuries.length === 0 ? (
                <div className="text-gray-500 text-center py-4">No healed injuries</div>
              ) : (
                <div className="space-y-3">
                  {healedInjuries.map((injury) => (
                    <div
                      key={injury.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-md bg-gray-50"
                    >
                      <div className="flex items-center space-x-3">
                        <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700">
                          Healed
                        </span>
                        <div>
                          <div className="font-medium text-gray-700">{injury.injury_type.name}</div>
                          {injury.notes && <div className="text-sm text-gray-500">{injury.notes}</div>}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDelete(injury.id)}
                        className="px-3 py-1 text-sm text-red-600 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showModal && (
        <AddInjuryModal
          injury={editingInjury}
          onClose={handleModalClose}
        />
      )}
    </>
  )
}

export default InjuriesSection
