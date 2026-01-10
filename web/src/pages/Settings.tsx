import { useEffect, useState } from 'react'
import { useUserStore } from '../stores/userStore'
import ProfileSection from '../components/settings/ProfileSection'
import EquipmentProfilesSection from '../components/settings/EquipmentProfilesSection'
import InjuriesSection from '../components/settings/InjuriesSection'

function Settings() {
  const { user, fetchCurrentUser, loading } = useUserStore()
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!user) {
      fetchCurrentUser()
    }
  }, [user, fetchCurrentUser])

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1)
  }

  if (loading && !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>

        <div className="space-y-8">
          <ProfileSection key={`profile-${refreshKey}`} />
          <EquipmentProfilesSection key={`equipment-${refreshKey}`} onUpdate={handleRefresh} />
          <InjuriesSection key={`injuries-${refreshKey}`} onUpdate={handleRefresh} />
        </div>
      </div>
    </div>
  )
}

export default Settings
