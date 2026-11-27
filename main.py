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
from prompts.general import get_general_rules

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
    created_at: int


class SyncRequest(BaseModel):
    user_id: str
    plans: List[SyncPlanModel]


# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}


@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    client = get_groq_client()
    if not client:
        return JSONResponse(status_code=500, content={"error": "Groq API key not configured"})

    logger.info(f"Generating plan for role: {request.role}, type: {request.plan_type}")

    # 1. Common rules (formatting, no tables, time rules) — all roles
    common_rules = get_common_rules()

    # 2. Role-specific rules
    role = (request.role or "student").lower()
    if role == "student":
        role_rules = get_student_rules(request.plan_type)
        system_persona = "You are a friendly, encouraging study tutor and academic coach."
    elif role == "professional":
        role_rules = get_professional_rules(request.plan_type)
        system_persona = "You are an elite productivity consultant and executive coach."
    else:
        # General / Personal mode (also fallback for any unknown role)
        role_rules = get_general_rules()
        system_persona = "You are a friendly, practical personal assistant."

    # 3. Topics line only matters for student/professional
    topics_line = ""
    if role != "general" and request.topics:
        topics_line = f"Topics/Tasks: {request.topics}"

    prompt = f"""
{role_rules}

{common_rules}

USER DETAILS:
Role: {request.role}
Goal: {request.goal}
Deadline: {request.deadline} days
Daily Available Hours: {request.daily_hours} hours
{topics_line}

Create the plan now, strictly following all formatting and time rules.
"""

    models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]

    def stream_generator():
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Trying model: {model}")
                stream = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_persona},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                logger.info(f"Model {model} completed")
                return
            except Exception as e:
                logger.warning(f"Model {model} failed: {str(e)}")
                last_error = e
                continue

        yield f"\n\n❌ Error: All AI models failed. {str(last_error)}"

    return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")


@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    client = get_groq_client()
    if not client:
        return JSONResponse(status_code=500, content={"error": "Groq API key not configured"})

    prompt = f"""
You are PlanWise Review AI. Critically analyze the following plan:

Goal: {request.goal}

Plan:
{request.plan}

Analyze:
1. Is this plan realistic given the timeline?
2. Are the daily hours achievable?
3. Is the workload balanced?
4. Are there any gaps or overlaps?

FORMATTING REQUIREMENTS:
- DO NOT use markdown tables.
- Use bullet points and short paragraphs.
- Use **bold** for section headings.
- Keep lines short for mobile readability.
- Leave a blank line between sections.

Provide:
- Reality Check: What's unrealistic or challenging?
- Suggestions: Specific improvements
- Optimized Approach: How to make it better

Keep tone encouraging and helpful.
"""

    models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]

    def stream_generator():
        last_error = None
        for model in models_to_try:
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1000,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                last_error = e
                continue
        yield f"\n\n❌ Error: All AI models failed. {str(last_error)}"

    return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")


@app.post("/sync-plans")
async def sync_plans(request: SyncRequest):
    if not supabase:
        return JSONResponse(status_code=500, content={"error": "Supabase not configured"})

    try:
        logger.info(f"Syncing {len(request.plans)} plans for user {request.user_id}")

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
                "created_at": p.created_at
            })

        response = supabase.table("plans").insert(data_to_insert).execute()
        logger.info(f"Successfully synced {len(response.data)} plans.")
        return {"status": "success", "synced_count": len(response.data)}

    except Exception as e:
        logger.error(f"Failed to sync plans: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


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
