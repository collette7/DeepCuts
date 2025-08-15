# DeepCuts Frontend - Learn Modern Web Development

A comprehensive Next.js React application that demonstrates modern web development practices through a real-world music recommendation system. This project serves as both a functional application and an educational resource for learning frontend development.

## 🎯 Learning Objectives

This codebase teaches you:
- **Modern React patterns** with hooks, context, and component composition
- **Next.js 13+ App Router** for server/client component architecture
- **TypeScript integration** for type-safe development
- **Authentication flows** with JWT tokens and session management
- **API integration** with progressive loading and error handling
- **State management** patterns from local state to global context
- **Performance optimization** through caching and lazy loading
- **Security best practices** including input sanitization and XSS prevention

## 💡 Key Educational Concepts

### **Frontend Architecture Patterns**
Learn how modern applications separate concerns:
- **Presentation Layer**: React components for UI
- **State Layer**: Context and hooks for data management  
- **Service Layer**: API client for backend communication
- **Styling Layer**: SCSS modules for maintainable styles

### **Progressive Enhancement**
See how the app provides immediate value while loading enhanced features:
1. **Basic content loads first** (AI recommendations)
2. **Enhanced data loads progressively** (Spotify/Discogs enrichment)
3. **Graceful fallbacks** when services are unavailable

### **Authentication Architecture**
Understand modern auth patterns:
- **JWT token management** with automatic refresh
- **Session persistence** across browser sessions
- **Route protection** and conditional rendering
- **Error handling** for expired/invalid tokens

## Frontend-Specific Features

- **Responsive Design**: CSS Grid/Flexbox layouts optimized for music browsing
- **Progressive Loading**: Spotify/Discogs data loads progressively for better UX
- **Design System**: SCSS variables and consistent component styling
- **Client-Side Routing**: Next.js App Router for seamless navigation
- **State Management**: React Context for authentication and app state

## Development Setup

### Prerequisites
- Node.js 18+
- Running DeepCuts backend on port 8000

### Quick Start
```bash
npm install
cp .env.local.example .env.local  # Configure your environment
npm run dev
```

### Environment Variables
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_SPOTIFY_CLIENT_ID=your_spotify_client_id
```

## Project Structure

```
src/
├── app/                    # Next.js app directory
│   ├── components/         # Reusable UI components
│   ├── contexts/          # React contexts (Auth, etc.)
│   ├── favorites/         # Favorites page
│   └── page.tsx          # Home page
├── lib/                   # Utility libraries
│   ├── api.ts            # API client
│   ├── auth-error-handler.ts
│   └── supabase.ts       # Supabase configuration
└── styles/               # Global styles and variables
    ├── _variables.scss   # Design system variables
    └── globals.css       # Global CSS
```

## Key Components

- **Navigation**: Main navigation with user authentication
- **AlbumCard**: Displays album information with actions
- **AlbumDetails**: Detailed album view with Spotify/Discogs links
- **RecommendationsSection**: Grid layout for album recommendations
- **AuthModal**: User authentication interface

## API Integration

The frontend communicates with the FastAPI backend through a centralized API client (`lib/api.ts`) that handles:

- AI-powered album search and recommendations (using Claude, Gemini, or GPT)
- User favorites management
- Spotify data enrichment
- Discogs metadata lookup
- Authentication token management

## 📚 Learning Path

### **Beginner Path**
1. **[Wave 1: React Fundamentals](./wave-1.md)** - Components, hooks, and Next.js basics
2. **[Wave 2: Authentication Systems](./wave-2.md)** - JWT, Supabase, and user management
3. **[Glossary](./glossary.md)** - Comprehensive technical terms and concepts

### **Intermediate Path**  
3. **[Wave 3: API Integration](./wave-3.md)** - Progressive loading and state management
4. **[Wave 4: Advanced Patterns](./wave-4.md)** - Performance optimization and deployment

### **Quick Reference**
- **[Technical Glossary](./glossary.md)** - All concepts and terms explained
- **Code Examples** - Look for `💡 Concept Explained` and `🔍 Deep Dive` sections throughout

## 🔍 Code Study Guide

### **Start Here: Core Files to Understand**

1. **`src/app/page.tsx`** - Main application logic and React patterns
   - Study the hooks usage (useState, useEffect, useCallback)
   - Observe progressive loading implementation
   - Note error handling and loading states

2. **`src/lib/api.ts`** - API client pattern and HTTP communication
   - See how authentication headers are managed
   - Study error handling and retry logic
   - Understand caching implementation

3. **`src/app/contexts/AuthContext.tsx`** - State management with React Context
   - Learn session management
   - Study authentication flows
   - See how context provides global state

4. **`src/app/components/AlbumCard.tsx`** - Component design patterns
   - Understand prop interfaces and TypeScript
   - See event handling and conditional rendering
   - Study accessibility implementation

## 🛡️ Security Concepts Demonstrated

This codebase implements several security best practices:

### **Input Sanitization**
```typescript
// Always sanitize user input
const sanitizedQuery = query.trim().slice(0, 200);
const sanitizedAlbumId = encodeURIComponent(albumId);
```

### **Authentication Security**
- JWT tokens stored securely
- Automatic token refresh
- Session validation on each request
- Graceful handling of expired sessions

### **XSS Prevention**  
- React automatically escapes user content
- No dangerous `innerHTML` usage
- Safe URL construction with `encodeURIComponent`

## Deployment

### Environment Setup

Ensure production environment variables are configured:
- Update `NEXT_PUBLIC_API_URL` to point to production backend
- Configure Supabase for production environment
- Set up Spotify app credentials for production domain

### Build and Deploy

```bash
# Build for production
npm run build

# Start production server
npm start
```

## 📖 Additional Learning Resources

- **[React Documentation](https://react.dev)** - Official React guides
- **[Next.js Documentation](https://nextjs.org/docs)** - Framework-specific features
- **[TypeScript Handbook](https://www.typescriptlang.org/docs/)** - Type system fundamentals
- **[Supabase Guides](https://supabase.com/docs)** - Authentication and database patterns

