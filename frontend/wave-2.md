# Wave 2: Authentication Systems & User Management

**Learning Objectives**: Master modern authentication patterns, JWT token management, and secure user session handling using Supabase and React Context.

**Prerequisites**: Wave 1 completed, understanding of React hooks and context

**Time Commitment**: 5-7 hours

---

## 🎯 What You'll Learn

By the end of this wave, you'll understand:
- JWT token structure and security principles
- Supabase authentication architecture and integration
- Session management across browser tabs and refreshes
- React Context for global state management
- Authentication error handling and recovery
- Protected routes and conditional UI rendering

---

## 💡 Concept Explained: Authentication vs Authorization

**Authentication** (Who are you?):
- Proving identity (login with email/password)
- Obtaining access tokens
- Session management

**Authorization** (What can you do?):  
- Checking permissions for specific actions
- Role-based access control
- Resource-level security

**Real-world analogy**: 
- **Authentication** = Showing your ID to get into a concert
- **Authorization** = Your ticket showing which section you can access

---

## 🔐 JWT Tokens Deep Dive

Let's examine how JWT tokens work by studying the authentication flow:

### **JWT Structure**

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

This breaks down into three parts:
- **Header**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9`
- **Payload**: `eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ`
- **Signature**: `SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c`

### **💡 Concept Explained: JWT Security Model**

**What JWT tokens contain**:
```json
{
  "aud": "authenticated",
  "exp": 1640995200,
  "sub": "user-uuid-here",
  "email": "user@example.com",
  "app_metadata": {
    "provider": "email",
    "providers": ["email"]
  },
  "user_metadata": {},
  "role": "authenticated"
}
```

**Security principles**:
1. **Stateless**: Server doesn't store session data
2. **Self-contained**: All necessary info is in the token  
3. **Tamper-proof**: Signature prevents modification
4. **Expiring**: Tokens have built-in expiration

**Why not just use session cookies?**
- **Scalability**: No server-side session storage needed
- **Cross-domain**: Works across different domains/services  
- **Mobile-friendly**: Easier to handle in mobile apps
- **Microservices**: Each service can validate independently

---

## 🏗️ Supabase Authentication Architecture

Let's analyze the AuthContext implementation to understand modern auth patterns:

### **Authentication Context Setup**

```tsx
// File: src/app/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signUp: (email: string, password?: string) => Promise<{ error: unknown }>
  signIn: (email: string, password?: string) => Promise<{ error: unknown }>
  signOut: () => Promise<void>
  clearSession: () => void
}
```

**🔍 Deep Dive: Context Interface Design**

This interface provides everything components need for authentication:
- **State**: Current user and session info
- **Actions**: Functions to sign up, sign in, sign out
- **Status**: Loading state for UI feedback
- **Recovery**: Clear session for error handling

**Benefits of this pattern**:
- **Single source of truth** for auth state
- **Consistent API** across all components
- **Automatic state synchronization** across app
- **Built-in error handling** and loading states

### **Session Management Implementation**

```tsx
useEffect(() => {
  const getSession = async () => {
    try {
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Session error:', error)
        setSession(null)
        setUser(null)
      } else {
        setSession(session)
        setUser(session?.user ?? null)
      }
    } catch (error) {
      console.error('Failed to get session:', error)
      setSession(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  getSession()
}, [])
```

**💡 Concept Explained: Session Initialization**

This effect runs once when the app loads and:
1. **Checks for existing session** in browser storage
2. **Validates the session** with Supabase
3. **Sets initial auth state** based on results
4. **Handles errors gracefully** by clearing invalid sessions

**Why this pattern is important**:
- Users stay logged in across browser sessions
- Invalid/expired sessions are cleaned up automatically
- Loading states prevent flash of unauthenticated content

### **Real-time Authentication State**

```tsx
const { data: { subscription } } = supabase.auth.onAuthStateChange(
  async (event, session) => {
    console.log('Auth state change:', event, session?.user?.email)
    
    if (event === 'TOKEN_REFRESHED' && !session) {
      console.warn('Token refresh failed, clearing session')
      clearSession()
      return
    }
    
    setSession(session)
    setUser(session?.user ?? null)
    setLoading(false)
  }
)
```

**🔍 Deep Dive: Authentication Events**

Supabase fires events for various auth state changes:
- **SIGNED_IN**: User successfully logged in
- **SIGNED_OUT**: User logged out  
- **TOKEN_REFRESHED**: Access token was refreshed
- **USER_UPDATED**: User profile was modified
- **PASSWORD_RECOVERY**: Password reset initiated

**Auto token refresh**: Supabase automatically refreshes tokens before they expire, keeping users logged in without manual intervention.

---

## 🔄 Authentication Flows

### **Magic Link Authentication**

```tsx
const signIn = async (email: string, password?: string) => {
  if (password) {
    // Traditional password login
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return { error }
  } else {
    // Magic link login
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`
      }
    })
    return { error }
  }
}
```

**💡 Concept Explained: Magic Links vs Passwords**

**Magic Links**:
- **User Experience**: No password to remember/type
- **Security**: Each link is single-use and time-limited
- **Simplicity**: Reduces password reset flows
- **Mobile-friendly**: Works well across devices

**Traditional Passwords**:
- **Immediate access**: No email round-trip required
- **Offline capable**: Works without email access
- **Familiar**: Users understand the flow
- **Control**: Users manage their own security

**When to offer both**: Give users choice based on their preferences and context.

### **Authentication Callback Handling**

```tsx
// File: src/app/auth/callback/page.tsx (conceptual)
export default function AuthCallback() {
  useEffect(() => {
    const handleAuthCallback = async () => {
      const { data, error } = await supabase.auth.getSession()
      if (error) {
        // Handle error
        redirect('/login?error=auth_failed')
      } else {
        // Success - redirect to app
        redirect('/')
      }
    }
    
    handleAuthCallback()
  }, [])
  
  return <div>Completing sign in...</div>
}
```

**Why callback pages are needed**:
- Magic links redirect users back to your app
- URL contains authentication tokens that need processing
- Provides feedback during authentication completion
- Handles both success and error cases

---

## 🛡️ Security Considerations

### **Token Storage Security**

```tsx
const clearSession = () => {
  setSession(null)
  setUser(null)
  // Clear any stored tokens
  if (typeof window !== 'undefined') {
    localStorage.removeItem('supabase.auth.token')
    sessionStorage.clear()
  }
}
```

**🔍 Deep Dive: Storage Options**

**localStorage vs sessionStorage vs httpOnly cookies**:

| Storage Type | Persistence | XSS Vulnerable | CSRF Vulnerable | Best For |
|--------------|-------------|----------------|------------------|----------|
| localStorage | Until cleared | Yes | No | Long-term sessions |
| sessionStorage | Tab lifetime | Yes | No | Short-term sessions |
| httpOnly cookies | Configurable | No | Yes | Most secure |

**Supabase choice**: Uses localStorage with automatic refresh for balance of security and UX.

### **Authentication Error Handling**

```tsx
// File: src/lib/auth-error-handler.ts
export function isRefreshTokenError(error: any): boolean {
  return (
    error?.message?.includes('refresh_token_not_found') ||
    error?.message?.includes('invalid_token') ||
    error?.message?.includes('token_refresh_failed')
  )
}

export async function handleAuthError(error: any) {
  console.error('Auth error:', error)
  
  if (isRefreshTokenError(error)) {
    // Clear invalid session
    const { supabase } = await import('@/lib/supabase')
    await supabase.auth.signOut()
    
    // Optionally redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login?error=session_expired'
    }
  }
}
```

**💡 Concept Explained: Graceful Auth Failures**

Authentication can fail for many reasons:
- **Network issues**: Can't reach auth server
- **Token expiry**: Refresh token has expired  
- **Token corruption**: Local storage was tampered with
- **Server issues**: Auth service is down

**Good error handling**:
1. **Categorize errors** - permanent vs temporary
2. **Provide clear feedback** to users
3. **Auto-recovery** where possible
4. **Fallback gracefully** to unauthenticated state

---

## 🎨 Authentication UI Patterns

### **Conditional Rendering Based on Auth State**

```tsx
// From main page component
const { user } = useAuth();

// Show different UI based on auth state
{!user ? (
  <button onClick={() => setAuthModalOpen(true)}>
    Sign in to save favorites
  </button>
) : (
  <button onClick={() => handleToggleFavorite(album)}>
    {isFavorited ? 'Remove from favorites' : 'Add to favorites'}
  </button>
)}
```

**Pattern advantages**:
- **Progressive enhancement**: App works without login
- **Clear value proposition**: Show what login enables
- **Smooth transitions**: No page reloads for auth changes

### **Auth Modal Implementation**

```tsx
// Conceptual auth modal structure
function AuthModal({ isOpen, onClose }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const { signIn, signUp, loading, error } = useAuth()
  
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      {mode === 'signin' ? (
        <LoginForm onSubmit={signIn} />
      ) : (
        <SignupForm onSubmit={signUp} />
      )}
      <button onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}>
        {mode === 'signin' ? 'Need an account?' : 'Have an account?'}
      </button>
    </Modal>
  )
}
```

**💡 Concept Explained: Modal vs Page Auth**

**Modal Authentication** (used in this app):
- **Context preservation**: User doesn't lose their place
- **Faster conversion**: Lower friction to sign up
- **Progressive disclosure**: Auth is secondary to main flow

**Page-based Authentication**:
- **Focus**: Dedicated space for complex auth flows
- **SEO**: Auth pages can be indexed/bookmarked
- **Accessibility**: Easier to implement proper focus management

---

## 🔗 API Integration with Authentication

### **Authenticated API Requests**

```tsx
// From api.ts
private async getAuthHeaders(): Promise<HeadersInit> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };

  try {
    const { supabase } = await import('@/lib/supabase');
    const { data: { session }, error } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
  } catch (error) {
    console.error('Error getting auth headers:', error);
  }
  
  return headers;
}
```

**🔍 Deep Dive: Authorization Headers**

**Bearer token pattern**:
- **Standard**: RFC 6750 compliant
- **Stateless**: Server validates without session lookup
- **Flexible**: Works with any JWT-compatible backend

**Error handling in API requests**:
```tsx
if (response.status === 401) {
  throw new Error('Please sign in to save favorites');
}
```

This provides clear user feedback when auth is required.

---

## 📱 Cross-Tab Session Synchronization

```tsx
// Session state automatically syncs across tabs via Supabase
const { data: { subscription } } = supabase.auth.onAuthStateChange(
  async (event, session) => {
    // This fires in ALL tabs when auth state changes
    setSession(session)
    setUser(session?.user ?? null)
  }
)
```

**💡 Concept Explained: Multi-Tab Synchronization**

**Without sync**: User logs out in one tab, other tabs still show logged-in state

**With sync**: 
- Login in tab A → all tabs update to logged-in
- Logout in tab B → all tabs update to logged-out  
- Token refresh → all tabs get new token

**How it works**: Supabase uses `storage` events and `BroadcastChannel` API to sync state across browser tabs.

---

## 🛠️ Practical Exercises

### **Exercise 1: Enhanced Error Handling**

Improve the authentication error handling with user-friendly messages:

```tsx
function getErrorMessage(error: any): string {
  switch (error?.message) {
    case 'Invalid login credentials':
      return 'Email or password is incorrect'
    case 'Email not confirmed':
      return 'Please check your email and click the confirmation link'
    case 'Email rate limit exceeded':
      return 'Too many attempts. Please try again in a few minutes'
    default:
      return 'Something went wrong. Please try again'
  }
}
```

### **Exercise 2: Session Timeout Warning**

Add a warning when the user's session is about to expire:

```tsx
function useSessionTimeout() {
  const [showWarning, setShowWarning] = useState(false)
  
  useEffect(() => {
    // Calculate time until token expiry
    // Show warning 5 minutes before expiration
    // Provide option to extend session
  }, [])
  
  return { showWarning, extendSession, signOutNow }
}
```

### **Exercise 3: Role-based UI**

Add role-based conditional rendering:

```tsx
function AdminPanel() {
  const { user } = useAuth()
  const isAdmin = user?.app_metadata?.role === 'admin'
  
  if (!isAdmin) return null
  
  return (
    <div>
      <h2>Admin Controls</h2>
      {/* Admin-only features */}
    </div>
  )
}
```

---

## 🔍 Common Authentication Patterns

### **✅ Good Patterns**

```tsx
// 1. Always check loading state
const { user, loading } = useAuth()
if (loading) return <LoadingSpinner />

// 2. Provide clear feedback
const handleSignIn = async () => {
  setLoading(true)
  try {
    const { error } = await signIn(email, password)
    if (error) {
      setError(getErrorMessage(error))
    }
  } finally {
    setLoading(false)
  }
}

// 3. Graceful fallbacks
const handleFavorite = async () => {
  if (!user) {
    setAuthModalOpen(true) // Request auth
    return
  }
  // Proceed with authenticated action
}
```

### **❌ Anti-Patterns to Avoid**

```tsx
// 1. Don't store sensitive data in localStorage
localStorage.setItem('password', password) // Never do this!

// 2. Don't trust client-side auth checks alone
if (user.role === 'admin') {
  // Client-side check is good for UX
  deleteAllData() // But server must also verify!
}

// 3. Don't ignore auth errors
try {
  await signIn(email, password)
} catch (error) {
  // Ignoring errors leads to confused users
}
```

---

## 🎯 Key Takeaways

1. **JWT tokens are self-contained** - they carry all necessary user information
2. **Sessions should sync across tabs** - use real-time auth state changes
3. **Always handle auth errors gracefully** - provide clear user feedback
4. **Progressive enhancement** - app should work without login, better with it
5. **Security is layered** - client checks for UX, server checks for security
6. **Context provides global auth state** - single source of truth for all components

---

## 🚀 Next Steps

Ready for Wave 3? You'll explore API integration patterns, learning how to implement progressive loading, handle caching strategies, and manage complex application state effectively.

**Coming up in Wave 3**:
- API client architecture and patterns
- Progressive loading and data enrichment
- Caching strategies for better performance  
- Error boundaries and recovery patterns
- State synchronization patterns

---

## 📚 Additional Resources

- **[Supabase Auth Guide](https://supabase.com/docs/guides/auth)** - Comprehensive authentication docs
- **[JWT.io](https://jwt.io/)** - JWT token decoder and documentation
- **[React Context Guide](https://react.dev/learn/passing-data-deeply-with-context)** - Official React context documentation
- **[Web Security Best Practices](https://owasp.org/Top10/)** - OWASP security guidelines