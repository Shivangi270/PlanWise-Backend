from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback
from typing import Optional
from openai import OpenAI
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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
logger.info(f"DeepSeek API Key present: {bool(DEEPSEEK_API_KEY)}")

if not DEEPSEEK_API_KEY:
    logger.error("DEEPSEEK_API_KEY not set in environment variables")

# Initialize DeepSeek client with OpenAI SDK
def get_deepseek_client():
    if not DEEPSEEK_API_KEY:
        return None
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1"
        )
        logger.info("DeepSeek client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize DeepSeek client: {str(e)}")
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
        client = get_deepseek_client()
        if not client:
            return JSONResponse(
                status_code=500,
                content={"error": "DeepSeek API key not configured"}
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
        
        logger.info("Sending request to DeepSeek API...")
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful planning assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            plan_text = response.choices[0].message.content
            logger.info(f"DeepSeek API response received, length: {len(plan_text)}")
            return {"plan": plan_text, "status": "success"}
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"error": f"DeepSeek API error: {str(e)}"}
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
        client = get_deepseek_client()
        if not client:
            return JSONResponse(
                status_code=500,
                content={"error": "DeepSeek API key not configured"}
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
        
        logger.info("Sending review request to DeepSeek API...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful planning review assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        review_text = response.choices[0].message.content
        logger.info("DeepSeek API review response received")
        
        return {"review": review_text, "status": "success"}
        
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
