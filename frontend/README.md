# DeepCuts Frontend

Next.js React application providing the user interface for DeepCuts music recommendations.

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

