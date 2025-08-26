# DeepCuts Record Discovery

A full-stack album recommendation platform powered by Spotify, Discogs, and multiple AI models. Built using **FastAPI**, **Supabase**, and **Next.js + TypeScript**, this app helps music lovers discover albums similar to the ones they already love — especially the deep cuts.

## ✨ Features

- **AI-Powered Recommendations**: Intelligent album suggestions using Claude and Gemini models with dynamic switching
- **Music Discovery**: Explore new albums with detailed reasoning for each recommendation
- **Favorites Management**: Save and organize your favorite albums with user accounts
- **Spotify Integration**: Listen to preview tracks and access full albums on Spotify
- **Discogs Integration**: Rich metadata and discography information
- **Responsive Design**: Seamless experience across desktop and mobile devices
- **Secure Authentication**: User accounts powered by Supabase Auth

## 🔧 Tech Stack

### Frontend (`/frontend`)
- **Framework**: [Next.js 14](https://nextjs.org/) with App Router
- **Language**: TypeScript
- **Styling**: SCSS with design system variables
- **State Management**: React Context
- **Authentication**: Supabase Auth
  
### Backend (`/backend`)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL (via Supabase)
- **AI**: Claude and Gemini models with dynamic model switching capability
- **External APIs**: Spotify Web API, Discogs API
- **Authentication**: Supabase integration

### Infrastructure
- **Database & Auth**: [Supabase](https://supabase.com/)
- **Backend Deployment**: Render or similar platforms
- **Frontend Deployment**: Vercel or similar platforms

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.8+
- Supabase account
- Spotify Developer account
- Discogs account
- AI API keys (Claude and/or Gemini)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/DeepCuts.git
cd DeepCuts
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env with your credentials

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Create .env.local file
cp .env.local.example .env.local
# Edit .env.local with your credentials

# Start the development server
npm run dev
```

### 4. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
DeepCuts/
├── frontend/              # Next.js React application
│   ├── src/app/          # App router pages and components
│   ├── src/lib/          # Utilities and API client
│   ├── src/styles/       # SCSS stylesheets and variables
│   └── README.md         # Frontend documentation
├── backend/              # FastAPI Python application
│   ├── app/              # Application modules
│   ├── requirements.txt  # Python dependencies
│   └── README.md         # Backend documentation
└── README.md            # This file
```

## 🔑 Environment Variables

### Backend (.env)
```bash
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# AI Models (configure at least one)
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key

# Music APIs
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
DISCOGS_TOKEN=your_discogs_token
```

### Frontend (.env.local)
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Spotify
NEXT_PUBLIC_SPOTIFY_CLIENT_ID=your_spotify_client_id
```

## 🛠️ Development

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations
Database schema is managed through Supabase. See `/backend/database/` for SQL migration files.

### API Documentation
With the backend running, visit http://localhost:8000/docs for interactive API documentation.

## 🚀 Deployment

### Backend Deployment
1. Deploy to Render, Railway, or similar platform
2. Set environment variables in your deployment platform
3. Update CORS settings for your frontend domain

### Frontend Deployment
1. Deploy to Vercel, Netlify, or similar platform
2. Update `NEXT_PUBLIC_API_URL` to point to your deployed backend
3. Configure build settings for Next.js

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add new amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/) for music data
- [Discogs API](https://www.discogs.com/developers/) for comprehensive album metadata
- [Claude AI](https://www.anthropic.com/claude) and [Google Gemini](https://ai.google.dev/) for intelligent recommendations
- [Supabase](https://supabase.com/) for database and authentication
- [Next.js](https://nextjs.org/) and [FastAPI](https://fastapi.tiangolo.com/) for the excellent frameworks



