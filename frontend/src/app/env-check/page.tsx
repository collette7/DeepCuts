'use client'

export default function EnvCheck() {
  const envVars = {
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
    supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'MISSING',
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    spotifyClientId: process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID ? 'SET' : 'MISSING',
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Environment Variables Check</h1>
      <pre>{JSON.stringify(envVars, null, 2)}</pre>
      
      <h2>Build Info:</h2>
      <p>Node ENV: {process.env.NODE_ENV}</p>
      <p>Timestamp: {new Date().toISOString()}</p>
    </div>
  )
}