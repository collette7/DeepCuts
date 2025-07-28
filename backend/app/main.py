from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import supabase_admin

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def hello_api():
    return {"msg":"Blello"}

@app.get("/testdb")
def check_database():
    """Test database connection"""
    try:
        result = supabase_admin.table('albums').select('*').limit(1).execute()
        return {
            "status": "healthy",
            "message": "Database connection successful",
            "tables_accessible": True
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database connection failed: {str(e)}",
            "tables_accessible": False
        }