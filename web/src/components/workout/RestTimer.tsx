/**
 * Rest Timer Component
 * Countdown timer for rest periods with sound option
 */
import { useState, useEffect, useRef } from 'react'

interface RestTimerProps {
  initialSeconds?: number
  onComplete?: () => void
  externalControl?: {
    isRunning: boolean
    onToggle: (isRunning: boolean) => void
  }
}

export default function RestTimer({
  initialSeconds = 60,
  onComplete,
  externalControl,
}: RestTimerProps) {
  const [seconds, setSeconds] = useState(initialSeconds)
  const [internalIsRunning, setInternalIsRunning] = useState(false)
  
  // Use external control if provided, otherwise use internal state
  const isRunning = externalControl ? externalControl.isRunning : internalIsRunning
  const setIsRunning = externalControl
    ? (running: boolean) => externalControl.onToggle(running)
    : setInternalIsRunning
  const [soundEnabled, setSoundEnabled] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (isRunning && seconds > 0) {
      intervalRef.current = setInterval(() => {
        setSeconds((prev) => {
          if (prev <= 1) {
            setIsRunning(false)
            if (soundEnabled) {
              playSound()
            }
            onComplete?.()
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isRunning, seconds, soundEnabled, onComplete])

  const playSound = () => {
    // Create a simple beep sound using Web Audio API
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = 800
      oscillator.type = 'sine'

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)

      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.5)
    } catch (error) {
      console.warn('Could not play sound:', error)
    }
  }

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins}:${String(secs).padStart(2, '0')}`
  }

  const handleStart = () => {
    setIsRunning(true)
  }

  const handlePause = () => {
    setIsRunning(false)
  }

  const handleToggle = () => {
    setIsRunning(!isRunning)
  }

  const handleReset = () => {
    setIsRunning(false)
    setSeconds(initialSeconds)
  }

  const handleAddTime = (addSeconds: number) => {
    setSeconds((prev) => prev + addSeconds)
  }

  const isLowTime = seconds <= 10 && seconds > 0

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold">Rest Timer</h3>
        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className={`p-2 rounded-lg transition-colors ${
            soundEnabled
              ? 'bg-blue-100 text-blue-600'
              : 'bg-gray-100 text-gray-400'
          }`}
          title={soundEnabled ? 'Sound enabled' : 'Sound disabled'}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            {soundEnabled ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zM17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"
              />
            )}
          </svg>
        </button>
      </div>

      {/* Timer Display */}
      <div
        className={`
          text-center py-8 mb-4 rounded-lg transition-colors
          ${isLowTime ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-900'}
        `}
      >
        <div className="text-5xl font-bold font-mono">{formatTime(seconds)}</div>
      </div>

      {/* Controls */}
      <div className="space-y-3">
        <div className="flex gap-2">
          <button
            onClick={handleToggle}
            className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
              isRunning
                ? 'bg-yellow-600 text-white hover:bg-yellow-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {isRunning ? 'Pause' : 'Start'}
          </button>
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Reset
          </button>
        </div>

        {/* Quick Add Time */}
        <div className="flex gap-2">
          <button
            onClick={() => handleAddTime(30)}
            className="flex-1 px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            +30s
          </button>
          <button
            onClick={() => handleAddTime(60)}
            className="flex-1 px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            +1m
          </button>
          <button
            onClick={() => handleAddTime(120)}
            className="flex-1 px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            +2m
          </button>
        </div>
      </div>
    </div>
  )
}
