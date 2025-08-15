# DeepCuts Frontend - Technical Glossary

## Core Technologies

### **Next.js**
A React-based framework that provides server-side rendering (SSR), static site generation (SSG), and client-side routing. Think of it as React with superpowers - it handles the complex build process, routing, and performance optimizations automatically.

**Real-world analogy**: If React is like having a powerful car engine, Next.js is like having that engine in a luxury car with automatic transmission, GPS, and all the advanced features built-in.

### **React**
A JavaScript library for building user interfaces using components. Components are reusable pieces of UI that manage their own state.

**Key concepts in this project**:
- **Functional Components**: Modern way to write React components using functions
- **Hooks**: Special functions that let you "hook into" React features (useState, useEffect, etc.)
- **JSX**: JavaScript XML - allows you to write HTML-like code in JavaScript

### **TypeScript**
JavaScript with type definitions. Helps catch errors during development by ensuring variables, functions, and objects have the expected types.

**Example**:
```typescript
// JavaScript (no type checking)
function greet(name) { return "Hello " + name; }

// TypeScript (with type checking)  
function greet(name: string): string { return "Hello " + name; }
```

## Authentication & Security

### **JWT (JSON Web Tokens)**
A compact, URL-safe way to securely transmit information between parties. Think of it as a digital passport that proves who you are.

**Structure**: `header.payload.signature`
- **Header**: Contains token type and hashing algorithm
- **Payload**: Contains user data and claims
- **Signature**: Ensures the token hasn't been tampered with

**Real-world analogy**: Like a concert wristband that proves you paid for entry and shows what areas you can access.

### **Supabase**
An open-source Firebase alternative that provides authentication, database, and real-time subscriptions. It handles user signup, login, and session management automatically.

**Key features used**:
- **Authentication**: User signup/login with magic links or passwords
- **Row Level Security (RLS)**: Database-level security that ensures users only see their own data
- **Real-time subscriptions**: Automatically sync data changes across clients

### **Authentication Flow**
1. User provides credentials (email/password or magic link)
2. Supabase verifies credentials and issues JWT token
3. Frontend stores token and includes it in API requests
4. Backend validates token and grants/denies access

### **Session Management**
The process of maintaining user login state across browser refreshes and multiple tabs.

**In this app**:
- Sessions persist in localStorage
- Tokens are automatically refreshed before expiration
- Auth state is shared via React Context

## API & Networking

### **REST API**
Representational State Transfer - a way for frontend and backend to communicate using HTTP methods (GET, POST, PUT, DELETE).

**HTTP Methods used**:
- **GET**: Retrieve data (get albums, favorites)
- **POST**: Create new data (search albums, add favorites)
- **DELETE**: Remove data (remove from favorites)
- **PATCH**: Update existing data (update favorites)

### **API Client Pattern**
A centralized class that handles all communication with the backend. Provides benefits like:
- **Consistent error handling** across all API calls
- **Automatic authentication** header injection
- **Request/response transformation** in one place
- **Caching and retries** logic centralization

### **Progressive Loading**
A UX pattern where basic content loads immediately, then enhanced data loads in the background.

**Example in this app**:
1. AI recommendations load instantly (fast)
2. Spotify/Discogs data loads progressively (slower but richer)
3. User sees results immediately, then enhanced data appears

### **CORS (Cross-Origin Resource Sharing)**
A security feature that controls which websites can access your API. When frontend (localhost:3000) tries to access backend (localhost:8000), browsers block it unless CORS is configured.

## State Management

### **React Context**
A way to share data between components without prop drilling (passing props through multiple component layers).

**Real-world analogy**: Like a company announcement board - instead of telling each employee individually, you post it once and everyone can read it.

### **State Management Patterns**
Different ways to handle data in React applications:

1. **Local State** (useState): Data only needed by one component
2. **Lifted State**: Data shared between sibling components (moved to common parent)
3. **Context State**: Data needed across many unrelated components
4. **External State**: Data managed by external libraries (Redux, Zustand)

### **Client vs Server State**
- **Client State**: UI state, form inputs, modal open/closed
- **Server State**: User data, search results, favorites (comes from API)

## React Patterns & Concepts

### **Client Components vs Server Components**
**Server Components** (Next.js 13+):
- Run on the server during build or request
- Can directly access databases and APIs
- Rendered to HTML before sending to browser
- Cannot use browser APIs or event handlers

**Client Components** (marked with 'use client'):
- Run in the browser
- Can use hooks, event handlers, and browser APIs
- Required for interactive features

### **Hooks Deep Dive**

#### **useState**
Manages component state (data that can change).
```typescript
const [count, setCount] = useState(0); // count is value, setCount is updater
```

#### **useEffect**  
Handles side effects (API calls, timers, subscriptions).
```typescript
useEffect(() => {
  // Effect logic
  return () => {
    // Cleanup logic (optional)
  };
}, [dependencies]); // Dependencies array controls when effect runs
```

#### **useCallback**
Prevents unnecessary re-renders by memoizing functions.
```typescript
const expensiveFunction = useCallback(() => {
  // Function logic
}, [dependencies]);
```

#### **Custom Hooks**
Reusable stateful logic extracted into custom functions.
```typescript
function useAuth() {
  // Auth logic
  return { user, login, logout };
}
```

## CSS & Styling

### **SCSS (Sass)**
CSS with superpowers - adds variables, nesting, mixins, and functions.

**Benefits**:
- **Variables**: Reusable values like colors and sizes
- **Nesting**: Write CSS that mirrors HTML structure  
- **Mixins**: Reusable blocks of CSS
- **Imports**: Split styles into multiple files

### **CSS Modules**
Automatically scope CSS classes to specific components, preventing style conflicts.

```scss
// AlbumCard.module.scss
.title { color: blue; } 

// Becomes: .AlbumCard_title__xyz123
```

### **Design System**
A consistent set of design patterns, components, and variables used across an application.

**In this project**:
- Color palette defined in SCSS variables
- Consistent spacing and typography
- Reusable component styles

## Performance & Optimization

### **Code Splitting**
Breaking application into smaller chunks that load only when needed.

**Next.js does this automatically**:
- Each page is a separate chunk
- Dynamic imports create additional chunks
- Users only download code for pages they visit

### **Lazy Loading**
Deferring the loading of non-critical resources until they're needed.

**Examples**:
- Images load when they become visible
- Components load when first rendered
- API data loads after initial page render

### **Caching Strategies**

#### **Browser Caching**
- Static assets (CSS, JS, images) cached by browser
- Reduces repeat downloads

#### **Application Caching**
- Search results cached in memory (Map/Set)
- Prevents duplicate API calls for same query

#### **HTTP Caching**
- API responses cached by browser or CDN
- Headers like `Cache-Control` control caching behavior

## Error Handling & UX

### **Error Boundaries**
React components that catch JavaScript errors in component tree and display fallback UI.

### **Graceful Degradation**
Design principle where app remains functional even when advanced features fail.

**Examples**:
- Show placeholder when album covers fail to load
- Display basic data when Spotify enrichment fails
- Allow browsing even when favorites feature is down

### **Loading States**
UI feedback showing that something is happening in the background.

**Types**:
- **Skeleton screens**: Placeholder content mimicking final layout
- **Spinners**: Traditional loading indicators
- **Progressive disclosure**: Show basic info first, details later

## AI & External APIs

### **AI Prompt Engineering**
The art of crafting prompts that get the best results from AI models.

**Good prompts are**:
- **Specific**: Clear about what you want
- **Contextual**: Provide relevant background information
- **Structured**: Use consistent format for consistent results

### **API Integration Patterns**

#### **Webhook vs Polling**
- **Polling**: Regularly check for updates (every 30 seconds)
- **Webhooks**: Server pushes updates when they happen

#### **Rate Limiting**
Controlling how many requests can be made to an API in a given time period.

**Strategies**:
- Exponential backoff (wait longer after each failure)
- Request queuing
- User feedback about limits

## Deployment & DevOps

### **Environment Variables**
Configuration values that change between development, staging, and production.

**Examples**:
- API URLs (localhost vs production domain)
- API keys and secrets
- Feature flags

### **Build Process**
Steps to transform development code into production-ready files.

**Next.js build process**:
1. TypeScript compilation
2. CSS compilation and optimization  
3. JavaScript bundling and minification
4. Image optimization
5. Static generation for pages that don't need server rendering

### **Vercel Deployment**
Platform specifically designed for Next.js applications.

**Benefits**:
- Automatic builds from Git commits
- Global CDN for fast loading worldwide
- Automatic HTTPS certificates
- Environment variable management

## Modern JavaScript Concepts

### **ES6+ Features Used**

#### **Async/Await**
Modern way to handle asynchronous operations (cleaner than Promises).

```typescript
// Old way (Promises)
fetch('/api/data')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error(error));

// New way (async/await)
try {
  const response = await fetch('/api/data');
  const data = await response.json();
  console.log(data);
} catch (error) {
  console.error(error);
}
```

#### **Destructuring**
Extract values from objects and arrays with clean syntax.

```typescript
// Object destructuring
const { user, loading } = useAuth();

// Array destructuring  
const [albums, setAlbums] = useState([]);
```

#### **Template Literals**
String interpolation with backticks.

```typescript
const message = `Hello ${user.name}, you have ${favoriteCount} favorites`;
```

#### **Optional Chaining**
Safely access nested object properties.

```typescript
// Instead of: user && user.profile && user.profile.name
const userName = user?.profile?.name;
```

## Database Concepts

### **Row Level Security (RLS)**
Database feature that automatically filters query results based on user identity.

**Example**: Users can only see their own favorites, even if they somehow access the favorites table directly.

### **Database Relations**
How data tables connect to each other:
- **One-to-Many**: One user has many favorites
- **Many-to-Many**: Many users can favorite many albums (junction table)

### **ACID Properties**
Database transaction principles:
- **Atomicity**: All operations succeed or all fail
- **Consistency**: Data remains valid after transactions
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed data survives system failures

## Web Security

### **XSS (Cross-Site Scripting)**
Malicious scripts injected into web pages. React prevents this by escaping user content by default.

### **CSRF (Cross-Site Request Forgery)**
Attacks that trick users into performing unwanted actions. Prevented by validating request origins.

### **Input Sanitization**
Cleaning user input to prevent injection attacks.

**Example in codebase**:
```typescript
const sanitizedQuery = query.trim().slice(0, 200); // Limit length and trim whitespace
```

### **Path Traversal**
Attack where malicious input tries to access unauthorized files. Prevented by encoding user input in URLs.

```typescript
const sanitizedAlbumId = encodeURIComponent(albumId);
```

---

## Quick Reference

### **Component Lifecycle**
1. **Mount**: Component is created and added to DOM
2. **Update**: Component re-renders due to state/props changes
3. **Unmount**: Component is removed from DOM

### **React Hooks Rules**
1. Only call hooks at the top level (not in loops/conditions)
2. Only call hooks from React functions (components or custom hooks)

### **Common HTTP Status Codes**
- **200 OK**: Request successful
- **201 Created**: Resource created successfully  
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource doesn't exist
- **500 Internal Server Error**: Server error

### **Browser Storage Options**
- **localStorage**: Persists until manually cleared
- **sessionStorage**: Cleared when tab closes
- **Cookies**: Can be set to expire, sent with every request
- **IndexedDB**: Large amounts of structured data