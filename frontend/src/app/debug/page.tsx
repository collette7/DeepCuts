'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function DebugPage() {
  const router = useRouter()
  const [envVars, setEnvVars] = useState<Record<string, unknown>>({})
  const isDev = process.env.NODE_ENV === 'development'

  useEffect(() => {
    // Block access in production to prevent environment variable exposure
    if (!isDev) {
      router.replace('/')
      return
    }

    setEnvVars({
      pocketbaseUrl: process.env.NEXT_PUBLIC_POCKETBASE_URL ? 'SET' : 'NOT SET',
      apiUrl: process.env.NEXT_PUBLIC_API_URL ? 'SET' : 'NOT SET',
    })
  }, [isDev, router])

  if (!isDev) return null

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Environment Debug (Development Only)</h1>
      <pre>{JSON.stringify(envVars, null, 2)}</pre>
    </div>
  )
}