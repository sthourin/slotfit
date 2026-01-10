import { useEffect, useState } from 'react'
import { injuryApi, type InjuryType, type UserInjury, type UserInjuryCreate, type UserInjuryUpdate } from '../../services/injuries'

interface AddInjuryModalProps {
  injury: UserInjury | null
  onClose: () => void
}

const BODY_AREAS = ['Shoulder', 'Elbow', 'Back', 'Knee', 'Wrist', 'Neck', 'Hip', 'Ankle']

function AddInjuryModal({ injury, onClose }: AddInjuryModalProps) {
  const [selectedBodyArea, setSelectedBodyArea] = useState<string | null>(null)
  const [injuryTypes, setInjuryTypes] = useState<InjuryType[]>([])
  const [filteredInjuryTypes, setFilteredInjuryTypes] = useState<InjuryType[]>([])
  const [selectedInjuryTypeId, setSelectedInjuryTypeId] = useState<number | null>(null)
  const [severity, setSeverity] = useState<'mild' | 'moderate' | 'severe'>('moderate')
  const [notes, setNotes] = useState('')
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchInjuryTypes = async () => {
      try {
        const data = await injuryApi.listInjuryTypes()
        setInjuryTypes(data)
        setFilteredInjuryTypes(data)
      } catch (error) {
        console.error('Failed to fetch injury types:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchInjuryTypes()
  }, [])

  useEffect(() => {
    if (injury) {
      setSelectedInjuryTypeId(injury.injury_type_id)
      setSeverity(injury.severity)
      setNotes(injury.notes || '')
      setDisclaimerAccepted(true) // Already accepted if editing
    }
  }, [injury])

  useEffect(() => {
    if (selectedBodyArea) {
      const filtered = injuryTypes.filter((it) => it.body_area === selectedBodyArea)
      setFilteredInjuryTypes(filtered)
    } else {
      setFilteredInjuryTypes(injuryTypes)
    }
  }, [selectedBodyArea, injuryTypes])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedInjuryTypeId) {
      alert('Please select an injury type')
      return
    }

    if (!disclaimerAccepted && !injury) {
      alert('Please accept the disclaimer')
      return
    }

    setSaving(true)
    try {
      if (injury) {
        // Update existing injury
        const updateData: UserInjuryUpdate = {
          severity,
          notes: notes.trim() || null,
        }
        await injuryApi.updateUserInjury(injury.id, updateData)
      } else {
        // Create new injury
        const createData: UserInjuryCreate = {
          injury_type_id: selectedInjuryTypeId,
          severity,
          notes: notes.trim() || null,
        }
        await injuryApi.addUserInjury(createData)
      }
      onClose()
    } catch (error: any) {
      console.error('Failed to save injury:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to save injury. Please try again.'
      alert(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const _selectedInjuryType = injuryTypes.find((it) => it.id === selectedInjuryTypeId)

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-gray-600">Loading injury types...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {injury ? 'Edit Injury' : 'Add Injury'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="px-6 py-4 space-y-4">
            {/* Disclaimer */}
            {!injury && (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800 mb-3">
                  <strong>Disclaimer:</strong> This feature helps you avoid potentially problematic exercises but is{' '}
                  <strong>not medical advice</strong>. Please consult a healthcare professional for injury management.
                </p>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={disclaimerAccepted}
                    onChange={(e) => setDisclaimerAccepted(e.target.checked)}
                    className="mr-2"
                    required
                  />
                  <span className="text-sm text-yellow-800">
                    I understand this is not medical advice
                  </span>
                </label>
              </div>
            )}

            {/* Body Area Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Body Area
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedBodyArea(null)}
                  className={`px-3 py-1 text-sm rounded-md ${
                    selectedBodyArea === null
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  All
                </button>
                {BODY_AREAS.map((area) => (
                  <button
                    key={area}
                    type="button"
                    onClick={() => setSelectedBodyArea(area)}
                    className={`px-3 py-1 text-sm rounded-md ${
                      selectedBodyArea === area
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {area}
                  </button>
                ))}
              </div>
            </div>

            {/* Injury Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Injury Type
              </label>
              <div className="border border-gray-300 rounded-md max-h-64 overflow-y-auto">
                {filteredInjuryTypes.length === 0 ? (
                  <div className="p-4 text-gray-500 text-center">No injury types found</div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {filteredInjuryTypes.map((it) => (
                      <label
                        key={it.id}
                        className={`flex items-start p-3 hover:bg-gray-50 cursor-pointer ${
                          selectedInjuryTypeId === it.id ? 'bg-blue-50' : ''
                        }`}
                      >
                        <input
                          type="radio"
                          name="injuryType"
                          value={it.id}
                          checked={selectedInjuryTypeId === it.id}
                          onChange={() => setSelectedInjuryTypeId(it.id)}
                          className="mt-1 mr-3"
                          disabled={!!injury} // Can't change injury type when editing
                        />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{it.name}</div>
                          {it.description && (
                            <div className="text-sm text-gray-500 mt-1">{it.description}</div>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Severity Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="severity"
                    value="mild"
                    checked={severity === 'mild'}
                    onChange={(e) => setSeverity(e.target.value as 'mild' | 'moderate' | 'severe')}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-900">
                    <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium mr-2">
                      Mild
                    </span>
                    Minor discomfort, can usually continue training with modifications
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="severity"
                    value="moderate"
                    checked={severity === 'moderate'}
                    onChange={(e) => setSeverity(e.target.value as 'mild' | 'moderate' | 'severe')}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-900">
                    <span className="inline-block px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-medium mr-2">
                      Moderate
                    </span>
                    Noticeable pain, requires exercise modifications
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="severity"
                    value="severe"
                    checked={severity === 'severe'}
                    onChange={(e) => setSeverity(e.target.value as 'mild' | 'moderate' | 'severe')}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-900">
                    <span className="inline-block px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-medium mr-2">
                      Severe
                    </span>
                    Significant pain, may require complete avoidance of certain movements
                  </span>
                </label>
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notes (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Add any additional notes about your injury..."
              />
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
              disabled={saving || (!injury && !disclaimerAccepted)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : injury ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default AddInjuryModal
