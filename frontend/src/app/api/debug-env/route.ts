import { NextResponse } from 'next/server'

export async function GET() {
  // Block access in production to prevent environment variable exposure
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  return NextResponse.json({
    pocketbaseUrl: process.env.NEXT_PUBLIC_POCKETBASE_URL ? 'SET' : 'NOT SET',
    apiUrl: process.env.NEXT_PUBLIC_API_URL ? 'SET' : 'NOT SET',
    nodeEnv: process.env.NODE_ENV,
  })
}