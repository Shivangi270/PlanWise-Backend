from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import os
import logging
from typing import Optional, List
from groq import Groq
from supabase import create_client, Client
from dotenv import load_dotenv

# Import our custom prompts
from prompts.common import get_common_rules
from prompts.student import get_student_rules
from prompts.professional import get_professional_rules

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="PlanWise API", description="AI-powered planning assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API KEYS ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {str(e)}")
else:
    logger.warning("Supabase credentials missing. Cloud sync will be disabled.")

def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {str(e)}")
        return None

# --- MODELS ---
class PlanRequest(BaseModel):
    goal: str
    deadline: int
    daily_hours: int
    role: Optional[str] = "student"
    topics: Optional[str] = ""
    plan_type: Optional[str] = "Read & Practice (Both)"

class PlanReviewRequest(BaseModel):
    plan: str
    goal: str

class SyncPlanModel(BaseModel):
    goal: str
    deadline: int
    daily_hours: int
    role: str
    topics: str
    plan_text: str
    created_at: int # Timestamp from local device

class SyncRequest(BaseModel):
    user_id: str
    plans: List[SyncPlanModel]

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}

@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    # ... (Keep your existing generate-plan code exactly as it is) ...
    pass # Replace with actual code

@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    # ... (Keep your existing review-plan code exactly as it is) ...
    pass # Replace with actual code

# --- NEW ENDPOINT: Sync Plans to Supabase ---
@app.post("/sync-plans")
async def sync_plans(request: SyncRequest):
    if not supabase:
        return JSONResponse(status_code=500, content={"error": "Supabase not configured"})
    
    try:
        logger.info(f"Syncing {len(request.plans)} plans for user {request.user_id}")
        
        # Format the data for Supabase
        data_to_insert = []
        for p in request.plans:
            data_to_insert.append({
                "user_id": request.user_id,
                "goal": p.goal,
                "deadline": p.deadline,
                "daily_hours": p.daily_hours,
                "role": p.role,
                "topics": p.topics,
                "plan_text": p.plan_text,
                # Convert local timestamp to standard ISO format for Postgres
                "created_at": p.created_at
            })
            
        # Insert into Supabase
        response = supabase.table("plans").insert(data_to_insert).execute()
        
        logger.info(f"Successfully synced {len(response.data)} plans.")
        return {"status": "success", "synced_count": len(response.data)}
        
    except Exception as e:
        logger.error(f"Failed to sync plans: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- NEW ENDPOINT: Get Plans from Supabase (for re-installs/new devices) ---
@app.get("/get-plans/{user_id}")
async def get_plans(user_id: str):
    if not supabase:
        return JSONResponse(status_code=500, content={"error": "Supabase not configured"})
    
    try:
        response = supabase.table("plans").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"status": "success", "plans": response.data}
    except Exception as e:
        logger.error(f"Failed to fetch plans: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
