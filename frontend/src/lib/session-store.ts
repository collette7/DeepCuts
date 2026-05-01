import { Session } from '@supabase/supabase-js'

let currentSession: Session | null = null

export function setCurrentSession(session: Session | null): void {
  currentSession = session
}

export function getCurrentSession(): Session | null {
  return currentSession
}
