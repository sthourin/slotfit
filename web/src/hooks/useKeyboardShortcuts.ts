/**
 * Keyboard Shortcuts Hook
 * Handles keyboard shortcuts for workout navigation and actions
 */
import { useEffect, useCallback, useRef } from 'react'

export interface KeyboardShortcutHandlers {
  onPreviousSlot?: () => void
  onNextSlot?: () => void
  onSkipSlot?: () => void
  onCompleteSet?: () => void
  onToggleRestTimer?: () => void
  onCancel?: () => void
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean
  handlers: KeyboardShortcutHandlers
}

/**
 * Hook to handle keyboard shortcuts for workout interface
 * 
 * Shortcuts:
 * - ArrowLeft (←) - Previous slot
 * - ArrowRight (→) - Next slot
 * - S - Skip current slot
 * - Enter - Complete current set / Add set
 * - Space - Start/Stop rest timer
 * - Escape - Cancel action / Close modal
 */
export function useKeyboardShortcuts({
  enabled = true,
  handlers,
}: UseKeyboardShortcutsOptions) {
  const handlersRef = useRef(handlers)

  // Update handlers ref when handlers change
  useEffect(() => {
    handlersRef.current = handlers
  }, [handlers])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't handle shortcuts if disabled
      if (!enabled) return

      // Don't handle shortcuts when user is typing in input fields
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Allow Escape to work even in input fields (for canceling)
        if (event.key === 'Escape') {
          handlersRef.current.onCancel?.()
        }
        return
      }

      // Prevent default for our shortcuts
      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault()
          handlersRef.current.onPreviousSlot?.()
          break

        case 'ArrowRight':
          event.preventDefault()
          handlersRef.current.onNextSlot?.()
          break

        case 's':
        case 'S':
          event.preventDefault()
          handlersRef.current.onSkipSlot?.()
          break

        case 'Enter':
          event.preventDefault()
          handlersRef.current.onCompleteSet?.()
          break

        case ' ':
          event.preventDefault()
          handlersRef.current.onToggleRestTimer?.()
          break

        case 'Escape':
          event.preventDefault()
          handlersRef.current.onCancel?.()
          break
      }
    },
    [enabled]
  )

  useEffect(() => {
    if (enabled) {
      window.addEventListener('keydown', handleKeyDown)
      return () => {
        window.removeEventListener('keydown', handleKeyDown)
      }
    }
  }, [enabled, handleKeyDown])
}
