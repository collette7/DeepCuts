# DeepCuts Backend

FastAPI service providing AI-powered music recommendations and API endpoints.

## Backend-Specific Features

- **AI Model Switching**: Dynamic switching between Claude and Gemini models with fallback
- **Async Processing**: FastAPI async endpoints for concurrent API calls
- **Progressive Data Loading**: Returns AI recommendations immediately, external data loads separately
- **Authentication Middleware**: JWT token validation and user context
- **Database Integration**: Supabase PostgreSQL with Row Level Security
- **Session Tracking**: Recommendation analytics and user behavior tracking

## AI Model Configuration

### Supported Models
- **Claude**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`
- **Gemini**: `gemini-1.5-flash`, `gemini-pro`

### Model Switching
```python
# Set via environment
ACTIVE_MODEL=gemini-1.5-flash

# Or programmatically
from app.config.model_switch import model_switch
model_switch.switch_to(AIModel.CLAUDE_35_SONNET)
```

## Project Structure

```
app/
├── config/
│   └── model_switch.py     # AI model switching logic
├── models/                 # Pydantic data models
│   ├── albums.py
│   ├── favorites.py
│   ├── recommendations.py
│   └── searchSuggestions.py
├── services/               # Business logic services
│   ├── ai.py              # AI recommendation service
│   ├── discogs.py         # Discogs API integration
│   ├── favorites.py       # User favorites management
│   └── recommendations.py # Recommendation sessions
├── config.py              # Configuration settings
├── database.py            # Database connections
└── main.py               # FastAPI application
```

## API Endpoints

### Core Endpoints
- `GET /` - Health check and service status
- `POST /api/v1/search` - Get AI-powered album recommendations
- `GET /api/v1/albums/random` - Get random album suggestions

### Album Data
- `GET /api/v1/albums/{album_id}/spotify` - Get Spotify and Discogs data for album
- `POST /api/v1/discogs/search` - Search Discogs for album suggestions

### User Favorites
- `POST /api/v1/favorites/add` - Add album to user favorites
- `DELETE /api/v1/favorites/remove/{album_id}` - Remove album from favorites
- `GET /api/v1/favorites` - Get user's favorite albums
- `GET /api/v1/favorites/with-details` - Get favorites with full album details

## Environment Variables

Create a `.env` file with the following variables:

```bash
# Database & Authentication
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# AI Models (configure at least one)
CLAUDE_API_KEY=your_anthropic_api_key
GEMINI_API_KEY=your_google_gemini_api_key

# Music APIs
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
DISCOGS_KEY=your_discogs_consumer_key
DISCOGS_SECRET=your_discogs_consumer_secret

# Configuration
ACTIVE_MODEL=gemini-1.5-flash  # or claude-3-5-sonnet-20241022
DEFAULT_AI_MODEL=gemini-1.5-flash
FRONTEND_URL=http://localhost:3000  # Optional: additional CORS origin
```

## Development Setup

### Prerequisites
- Python 3.8+
- At least one AI API key (Claude or Gemini)

### Quick Start
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys
uvicorn app.main:app --reload --port 8000
```

### Verify Setup
- Health check: http://localhost:8000
- API docs: http://localhost:8000/docs

## AI Model Configuration

The backend supports multiple AI models with automatic fallback:

### Available Models
- **Claude**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`
- **Gemini**: `gemini-1.5-flash`, `gemini-pro`

### Model Switching
```python
# Set active model via environment variable
ACTIVE_MODEL=claude-3-5-sonnet-20241022

# Or programmatically
from app.config.model_switch import model_switch
model_switch.switch_to(AIModel.CLAUDE_35_SONNET)
```

## Database Schema

### Core Tables
- `users` - User accounts and profiles
- `albums` - Album metadata cache
- `favorites` - User favorite albums
- `recommendation_sessions` - Search session tracking
- `recommended_albums` - Individual recommendations per session

### Security
- Row Level Security (RLS) enabled on all user data
- JWT token authentication via Supabase
- User isolation enforced at database level

## Deployment

### Environment Setup
1. Set production environment variables
2. Configure CORS origins for your frontend domain
3. Set up database with production Supabase instance

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Platform Deployment
The backend includes a `Procfile` for platforms like Render, Railway, or Heroku:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black app/

# Type checking
mypy app/

# Linting
flake8 app/
```

### Logging
The application uses structured logging with different levels:
- `INFO`: General application flow
- `ERROR`: Errors and exceptions
- `WARNING`: Potential issues

Logs include model switching, API calls, and authentication events.

## API Documentation

With the server running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **OpenAPI spec**: http://localhost:8000/openapi.json

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Commit changes: `git commit -m 'Add new feature'`
5. Push to branch: `git push origin feature/new-feature`
6. Open a Pull Request

## License

This project is proprietary software. All rights reserved. See the [LICENSE](../LICENSE) file for details.