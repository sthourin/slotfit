/**
 * Progression Chart Component
 * Shows exercise progression over time
 */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ProgressionDataPoint {
  date: string
  weight: number
  reps: number
  volume: number
}

interface ProgressionChartProps {
  data: ProgressionDataPoint[]
  exerciseName: string
}

export default function ProgressionChart({ data, exerciseName }: ProgressionChartProps) {
  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No progression data available for {exerciseName}</p>
      </div>
    )
  }

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => new Date(value).toLocaleDateString()}
          />
          <YAxis />
          <Tooltip
            labelFormatter={(value) => new Date(value).toLocaleDateString()}
            formatter={(value: number | undefined, name: string) => {
              if (value === undefined) return ['', '']
              if (name === 'volume') {
                return [`${value.toLocaleString()} lbs`, 'Volume']
              }
              if (name === 'weight') {
                return [`${value} lbs`, 'Weight']
              }
              return [value, 'Reps']
            }}
          />
          <Legend />
          <Line type="monotone" dataKey="weight" stroke="#3b82f6" name="Weight (lbs)" />
          <Line type="monotone" dataKey="reps" stroke="#8b5cf6" name="Reps" />
          <Line type="monotone" dataKey="volume" stroke="#10b981" name="Volume (lbs)" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
