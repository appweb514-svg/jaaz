import { useEffect, useState, useCallback } from 'react'

export interface RHCredits {
  coins: number
  wallet: string
  connected: boolean
  error?: string
}

const POLL_INTERVAL = 30000 // 30 seconds

export function useRHCredits() {
  const [credits, setCredits] = useState<RHCredits>({
    coins: 0,
    wallet: '0.00',
    connected: false,
  })
  const [loading, setLoading] = useState(true)

  const fetchCredits = useCallback(async () => {
    try {
      const res = await fetch('/runninghub/credits')
      const data: RHCredits = await res.json()
      setCredits(data)
    } catch (e) {
      console.error('Failed to fetch RH credits:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCredits()
    const interval = setInterval(fetchCredits, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchCredits])

  return { credits, loading, refresh: fetchCredits }
}
