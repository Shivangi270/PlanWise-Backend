from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback
import json
from typing import Optional
from google import genai
from google.oauth2 import service_account
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

# Get credentials from environment variable
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logger.info(f"Credentials JSON present: {bool(credentials_json)}")
logger.info(f"API Key present: {bool(GEMINI_API_KEY)}")

if not credentials_json and not GEMINI_API_KEY:
    logger.error("No credentials or API key set in environment variables")

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

def get_genai_client():
    """Initialize and return a GenAI client with proper credentials"""
    if credentials_json:
        try:
            # Parse the service account JSON
            creds_dict = json.loads(credentials_json)
            
            # Create credentials with the correct OAuth scope for Vertex AI
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
            # Use Vertex AI endpoint
            client = genai.Client(
                credentials=credentials,
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0975816225"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            )
            logger.info("Using service account credentials with Vertex AI")
            return client
        except Exception as e:
            logger.error(f"Failed to create client with service account: {str(e)}")
            raise
    
    elif GEMINI_API_KEY:
        # Fallback to API key
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Using API key")
        return client
    else:
        raise Exception("No credentials available")

@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}

@app.post("/generate-plan")
async def generate_plan(request: PlanRequest):
    try:
        client = get_genai_client()
        
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
        
        logger.info("Sending request to Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        logger.info("Gemini API response received")
        
        return {"plan": response.text, "status": "success"}
        
    except Exception as e:
        logger.error(f"Error in generate_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    try:
        client = get_genai_client()
        
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
        
        logger.info("Sending review request to Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
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
