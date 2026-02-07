/**
 * SlotTypeIndicator - Visual badge for slot type (warmup/standard/finisher/etc)
 */
import type { SlotType } from '../../services/routines'

interface SlotTypeIndicatorProps {
  slotType: SlotType
  size?: 'sm' | 'md' | 'lg'
}

const SLOT_TYPE_CONFIG: Record<
  SlotType,
  {
    label: string
    borderColor: string
    bgColor: string
    textColor: string
    description: string | null
  }
> = {
  standard: {
    label: 'STANDARD',
    borderColor: 'border-gray-300',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    description: null,
  },
  warmup: {
    label: 'WARMUP',
    borderColor: 'border-orange-300',
    bgColor: 'bg-gradient-to-r from-orange-50 to-yellow-50',
    textColor: 'text-orange-700',
    description: 'Light activation to prepare muscles',
  },
  finisher: {
    label: 'FINISHER',
    borderColor: 'border-red-400',
    bgColor: 'bg-gradient-to-r from-red-50 to-orange-50',
    textColor: 'text-red-700',
    description: 'High-intensity to exhaust the muscle',
  },
  active_recovery: {
    label: 'RECOVERY',
    borderColor: 'border-teal-300',
    bgColor: 'bg-gradient-to-r from-teal-50 to-blue-50',
    textColor: 'text-teal-700',
    description: 'Low-intensity movement for recovery',
  },
  wildcard: {
    label: 'WILDCARD',
    borderColor: 'border-purple-400',
    bgColor: 'bg-gradient-to-r from-purple-50 to-pink-50',
    textColor: 'text-purple-700',
    description: 'Your choice - no restrictions',
  },
}

const SIZE_CLASSES = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
}

export default function SlotTypeIndicator({ slotType, size = 'md' }: SlotTypeIndicatorProps) {
  const config = SLOT_TYPE_CONFIG[slotType] || SLOT_TYPE_CONFIG.standard

  return (
    <span
      className={`
        inline-flex items-center font-semibold rounded-md border
        ${config.borderColor} ${config.bgColor} ${config.textColor}
        ${SIZE_CLASSES[size]}
      `}
    >
      {config.label}
    </span>
  )
}

export function getSlotTypeConfig(slotType: SlotType) {
  return SLOT_TYPE_CONFIG[slotType] || SLOT_TYPE_CONFIG.standard
}
