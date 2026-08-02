/**
 * Persistent banner shown on any page (except the session page itself) when
 * the user has an unfinished training session in progress.
 *
 * Calls resume() once on mount to check for an active session; the store is
 * the source of truth so this stays in sync with whatever the Session page
 * itself does. Renders nothing until that check settles, once it settles
 * with no session, once the session is completed, or on the /session route
 * (where the full session UI already handles this).
 */
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSessionStore } from '../../stores/sessionStore'

export default function ResumeBanner() {
  const { session, resume, discard, busy } = useSessionStore()
  const [checked, setChecked] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!checked) {
      // Deliberately swallowed: resume() now re-throws on anything but a 404,
      // and this banner renders on every page. A failed check leaves the banner
      // hidden (its only job is to offer a resume), and the store keeps the
      // error for the Session page to display -- it must not become an
      // unhandled rejection here.
      resume()
        .catch(() => undefined)
        .finally(() => setChecked(true))
    }
  }, [checked, resume])

  if (!session || session.state === 'completed' || location.pathname === '/session') return null

  const handleDiscard = () => {
    if (!window.confirm('Discard this session? Everything logged will be lost.')) return
    discard()
  }

  return (
    <div
      className="bg-yellow-50 border-b border-yellow-200 px-6 py-2 flex justify-between items-center"
      data-testid="resume-banner"
    >
      <span className="text-sm text-yellow-800">You have an unfinished session.</span>
      <div className="space-x-3">
        <button onClick={() => navigate('/session')} className="text-sm font-medium text-blue-600">
          Resume
        </button>
        <button
          onClick={handleDiscard}
          disabled={busy}
          className="text-sm text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Discard
        </button>
      </div>
    </div>
  )
}
