from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
import logging

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

# Get API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
logger.info(f"Groq API Key present: {bool(GROQ_API_KEY)}")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set in environment variables")

# Replace this section:
def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {str(e)}")
        return None

# Models
class PlanRequest(BaseModel):
    goal: str
    deadline: int
    daily_hours: int
    role: Optional[str] = "student"
    topics: Optional[str] = ""

class PlanReviewRequest(BaseModel):
    plan: str
    goal: str

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}

# Generate Plan endpoint
@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    try:
        client = get_groq_client()
        if not client:
            return JSONResponse(
                status_code=500,
                content={"error": "Groq API key not configured"}
            )
        
        logger.info(f"Generating plan for goal: {request.goal}")
        
        prompt = f"""
You are PlanWise, a friendly and intelligent AI planning assistant.
Create a detailed study/plan for the following goal:

Role: {request.role}
Goal: {request.goal}
Deadline: {request.deadline} days
Daily Available Hours: {request.daily_hours} hours
Topics: {request.topics if request.topics else 'Not specified'}

Generate a structured plan with:
1. Weekly breakdown of topics
2. Daily schedule
3. Tips for success

Make it realistic and actionable. Use emojis for visual appeal.
"""
        
        logger.info("Sending request to Groq API...")
        
        # Try multiple Groq models in fallback order
        models_to_try = [
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768"
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Trying model: {model}")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful planning assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                plan_text = response.choices[0].message.content
                logger.info(f"Model {model} succeeded, response length: {len(plan_text)}")
                return {"plan": plan_text, "status": "success", "model": model}
            except Exception as e:
                logger.warning(f"Model {model} failed: {str(e)}")
                last_error = e
                continue
        
        # If all models fail
        logger.error("All Groq models failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"All AI models failed. Last error: {str(last_error)}"}
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

# Review Plan endpoint
@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    try:
        client = get_groq_client()
        if not client:
            return JSONResponse(
                status_code=500,
                content={"error": "Groq API key not configured"}
            )
        
        logger.info(f"Reviewing plan for goal: {request.goal}")
        
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

Provide:
- Reality Check: What's unrealistic or challenging?
- Suggestions: Specific improvements
- Optimized Approach: How to make it better

Keep tone encouraging and helpful.
"""
        
        logger.info("Sending review request to Groq API...")
        
        models_to_try = [
            "llama3-70b-8192",
            "llama3-8b-8192"
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful planning review assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                review_text = response.choices[0].message.content
                logger.info(f"Review model {model} succeeded")
                return {"review": review_text, "status": "success", "model": model}
            except Exception as e:
                logger.warning(f"Review model {model} failed: {str(e)}")
                last_error = e
                continue
        
        logger.error("All Groq review models failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"All AI models failed for review. Last error: {str(last_error)}"}
        )
        
    except Exception as e:
        logger.error(f"Error in review_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Review error: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
