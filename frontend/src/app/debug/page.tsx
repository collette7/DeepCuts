'use client'

import { useEffect, useState } from 'react'

export default function DebugPage() {
  const [envVars, setEnvVars] = useState<any>({})
  
  useEffect(() => {
    // Check client-side env vars
    setEnvVars({
      supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
      supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      apiUrl: process.env.NEXT_PUBLIC_API_URL,
      allEnvKeys: Object.keys(process.env).filter(key => key.startsWith('NEXT_PUBLIC_'))
    })
  }, [])

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Environment Debug</h1>
      <pre>{JSON.stringify(envVars, null, 2)}</pre>
      
      <h2>Direct Access Test:</h2>
      <p>NEXT_PUBLIC_SUPABASE_URL: {process.env.NEXT_PUBLIC_SUPABASE_URL || 'UNDEFINED'}</p>
      <p>NEXT_PUBLIC_SUPABASE_ANON_KEY: {process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'UNDEFINED'}</p>
      <p>NEXT_PUBLIC_API_URL: {process.env.NEXT_PUBLIC_API_URL || 'UNDEFINED'}</p>
    </div>
  )
}