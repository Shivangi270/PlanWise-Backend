from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import os
import logging
from typing import Optional
from groq import Groq
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
logger.info(f"Groq API Key present: {bool(GROQ_API_KEY)}")

def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {str(e)}")
        return None


class PlanRequest(BaseModel):
    goal: str
    deadline: int
    daily_hours: int
    role: Optional[str] = "student"
    topics: Optional[str] = ""
    plan_type: Optional[str] = "Read & Practice (Both)" # NEW FIELD


class PlanReviewRequest(BaseModel):
    plan: str
    goal: str


@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}


@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    client = get_groq_client()
    if not client:
        return JSONResponse(status_code=500, content={"error": "Groq API key not configured"})

    logger.info(f"Generating plan for role: {request.role}, type: {request.plan_type}")

    # 1. Get the common rules
    common_rules = get_common_rules()

    # 2. Get the role-specific rules
    is_student = request.role.lower() == "student"
    if is_student:
        role_rules = get_student_rules(request.plan_type) 
        system_persona = "You are a friendly, encouraging study tutor and academic coach."
    else:
        role_rules = get_professional_rules(request.plan_type)
        system_persona = "You are an elite productivity consultant and executive coach."

    # 3. Combine everything into the final prompt
    prompt = f"""
{role_rules}

{common_rules}

USER DETAILS:
Role: {request.role}
Goal: {request.goal}
Deadline: {request.deadline} days
Daily Available Hours: {request.daily_hours} hours
Topics/Tasks: {request.topics if request.topics else 'Not specified'}

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
