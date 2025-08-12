import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string

// Debug logging in production
if (typeof window !== 'undefined') {
  console.log('Initializing Supabase with:', {
    url: supabaseUrl ? supabaseUrl.substring(0, 40) + '...' : 'UNDEFINED',
    keyPresent: !!supabaseAnonKey,
    urlType: typeof supabaseUrl,
    keyType: typeof supabaseAnonKey
  })
}

// Check if variables are defined and valid
if (!supabaseUrl || typeof supabaseUrl !== 'string' || supabaseUrl === 'undefined') {
  console.error('Supabase URL is invalid:', supabaseUrl)
  throw new Error('Invalid NEXT_PUBLIC_SUPABASE_URL environment variable')
}

if (!supabaseAnonKey || typeof supabaseAnonKey !== 'string' || supabaseAnonKey === 'undefined') {
  console.error('Supabase Anon Key is invalid')
  throw new Error('Invalid NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable')
}

// Ensure URL is properly formatted
const cleanUrl = supabaseUrl.trim()
const cleanKey = supabaseAnonKey.trim()

export const supabase = createClient(cleanUrl, cleanKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    // Keep session for 7 days instead of default 1 hour
    storageKey: 'supabase.auth.token',
    storage: typeof window !== 'undefined' ? window.localStorage : undefined
  }
})