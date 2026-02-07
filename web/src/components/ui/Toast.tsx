/**
 * Toast Component
 * Renders toast notifications from uiStore
 */
import { useUIStore, type Toast as ToastType } from '../../stores/uiStore'

const icons: Record<ToastType['type'], string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}

const styles: Record<ToastType['type'], string> = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

const iconStyles: Record<ToastType['type'], string> = {
  success: 'bg-green-100 text-green-600',
  error: 'bg-red-100 text-red-600',
  warning: 'bg-yellow-100 text-yellow-600',
  info: 'bg-blue-100 text-blue-600',
}

function ToastItem({ toast }: { toast: ToastType }) {
  const { removeToast } = useUIStore()

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg ${styles[toast.type]}`}
      role="alert"
      aria-live="polite"
    >
      <span
        className={`flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full text-sm font-bold ${iconStyles[toast.type]}`}
        aria-hidden="true"
      >
        {icons[toast.type]}
      </span>
      <span className="flex-1 text-sm font-medium">{toast.message}</span>
      <button
        onClick={() => removeToast(toast.id)}
        className="flex-shrink-0 p-1 hover:opacity-70 transition-opacity"
        aria-label="Dismiss notification"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  )
}

export default function ToastContainer() {
  const { toasts } = useUIStore()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  )
}
