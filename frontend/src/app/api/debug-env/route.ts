import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'SET' : 'NOT SET',
    supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'NOT SET',
    apiUrl: process.env.NEXT_PUBLIC_API_URL ? 'SET' : 'NOT SET',
    nodeEnv: process.env.NODE_ENV,
    // Show first few chars to verify they're loading correctly
    urlPreview: process.env.NEXT_PUBLIC_SUPABASE_URL?.substring(0, 30),
    apiPreview: process.env.NEXT_PUBLIC_API_URL?.substring(0, 30),
  })
}