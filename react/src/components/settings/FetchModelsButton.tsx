import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { RefreshCw, Download } from 'lucide-react'

interface FetchModelsButtonProps {
  providerKey: string
  fetchUrl: string
  onModelsChange: (
    models: Record<string, { type?: 'text' | 'image' | 'video' }>
  ) => void
}

export default function FetchModelsButton({
  providerKey,
  fetchUrl,
  onModelsChange,
}: FetchModelsButtonProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleFetch = async () => {
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const res = await fetch(fetchUrl, {
        headers: { 'User-Agent': 'Jaaz/1.0' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      const models: Record<string, { type?: 'text' | 'image' | 'video' }> = {}
      const modelIds: string[] = data.data?.map((m: any) => m.id) || []

      // Filter free models for opencode-zen
      const isZen = providerKey === 'opencode-zen'
      const filtered = isZen
        ? modelIds.filter(
            (id: string) => id.endsWith('-free') || id === 'big-pickle'
          )
        : modelIds

      filtered.forEach((id: string) => {
        models[id] = { type: 'text' }
      })

      onModelsChange(models)
      setSuccess(`${filtered.length} models fetched (${isZen ? 'free only' : 'all'})`)
    } catch (e: any) {
      setError(e.message || 'Failed to fetch models')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleFetch}
          disabled={loading}
          className="flex items-center gap-1"
        >
          {loading ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {loading ? 'Fetching...' : 'Fetch models from API'}
        </Button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {success && <p className="text-xs text-green-500">{success}</p>}
    </div>
  )
}
