/**
 * Volume Chart Component
 * Displays weekly volume data as a bar chart
 */
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { type WeeklyVolumeResponse } from '../../services/analytics'

interface VolumeChartProps {
  data: WeeklyVolumeResponse
}

export default function VolumeChart({ data }: VolumeChartProps) {
  const chartData = data.muscle_groups.map((mg) => ({
    name: mg.name,
    sets: mg.total_sets,
    reps: mg.total_reps,
    volume: Math.round(mg.total_volume),
  }))

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            height={100}
            interval={0}
          />
          <YAxis />
          <Tooltip
            formatter={(value: number | undefined, name: string) => {
              if (value === undefined) return ['', '']
              if (name === 'volume') {
                return [`${value.toLocaleString()} lbs`, 'Volume']
              }
              return [value, name === 'sets' ? 'Sets' : 'Reps']
            }}
          />
          <Legend />
          <Bar dataKey="sets" fill="#3b82f6" name="Sets" />
          <Bar dataKey="reps" fill="#8b5cf6" name="Reps" />
          <Bar dataKey="volume" fill="#10b981" name="Volume (lbs)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
