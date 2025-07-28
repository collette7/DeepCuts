from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import supabase_admin
from api import albums

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def welcome():
    return {"msg":"Blello errybodie"}

@app.get("/testdb")
def check_database():
    """Test database connection"""
    try:
        result = supabase_admin.table('albums').select('*').limit(1).execute()
        return {
            "status": "healthy",
            "message": "Connection successful",
            "tables_accessible": True
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Connection FAILED!: {str(e)}",
            "tables_accessible": False
        }
    
@app.get("/albums/{album_id}")