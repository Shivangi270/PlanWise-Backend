from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback
from typing import Optional
import google.generativeai as genai
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

# Get API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger.info(f"API Key present: {bool(GEMINI_API_KEY)}")
logger.info(f"API Key first 10 chars: {GEMINI_API_KEY[:10] if GEMINI_API_KEY else 'None'}")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not set in environment variables")

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

@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}

@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is missing")
            return JSONResponse(
                status_code=500,
                content={"error": "GEMINI_API_KEY is not configured on the server"}
            )
        
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info(f"Generating plan for goal: {request.goal}")
        
        # Test the API key first
        try:
            model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Gemini model: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Gemini model error: {str(e)}"}
            )
        
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
        
        logger.info("Sending request to Gemini API...")
        
        try:
            response = model.generate_content(prompt)
            logger.info(f"Gemini API response received, length: {len(response.text)}")
            return {"plan": response.text, "status": "success"}
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"error": f"Gemini API error: {str(e)}"}
            )
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is missing")
            return JSONResponse(
                status_code=500,
                content={"error": "GEMINI_API_KEY is not configured on the server"}
            )
        
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info(f"Reviewing plan for goal: {request.goal}")
        
        model = genai.GenerativeModel('gemini-pro')
        
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
        
        logger.info("Sending review request to Gemini API...")
        response = model.generate_content(prompt)
        logger.info("Gemini API review response received")
        
        return {"review": response.text, "status": "success"}
        
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
