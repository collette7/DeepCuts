import { NextResponse } from 'next/server'

export async function GET() {
  // Block access in production to prevent environment variable exposure
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  return NextResponse.json({
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'SET' : 'NOT SET',
    supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'NOT SET',
    apiUrl: process.env.NEXT_PUBLIC_API_URL ? 'SET' : 'NOT SET',
    nodeEnv: process.env.NODE_ENV,
  })
}