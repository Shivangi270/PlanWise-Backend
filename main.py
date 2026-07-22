from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from typing import Optional
import openai
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PlanWise API", description="AI-powered planning assistant")

# CORS - Allow your app to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure AI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

# Helper function: Generate Plan using OpenAI
def generate_plan_with_openai(goal: str, deadline: int, daily_hours: int, role: str, topics: str):
    openai.api_key = OPENAI_API_KEY
    
    prompt = f"""
You are PlanWise, a friendly and intelligent AI planning assistant.
You help users create realistic, achievable plans for their goals.

User Information:
- Role: {role}
- Goal: {goal}
- Deadline: {deadline} days
- Daily Available Hours: {daily_hours} hours
- Topics/Subjects: {topics if topics else 'Not specified'}

Your task:
1. Generate a structured plan with daily/weekly breakdown
2. Make it realistic and achievable
3. Include tips for success

Format your response as:
## 📋 YOUR PLAN: {goal}
### ⏰ Timeline: {deadline} days
### 📅 Daily Hours: {daily_hours}

### 📆 Weekly Breakdown:
- Week 1: ...
- Week 2: ...
...

### 📋 Daily Schedule:
- Day 1: ...
- Day 2: ...
...

### 💡 Tips for Success:
1. ...
2. ...
3. ...
"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful planning assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")

# Helper function: Generate Plan using Gemini
def generate_plan_with_gemini(goal: str, deadline: int, daily_hours: int, role: str, topics: str):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
You are PlanWise, a friendly and intelligent AI planning assistant.
You help users create realistic, achievable plans for their goals.

User Information:
- Role: {role}
- Goal: {goal}
- Deadline: {deadline} days
- Daily Available Hours: {daily_hours} hours
- Topics/Subjects: {topics if topics else 'Not specified'}

Generate a structured plan with weekly breakdown, daily schedule, and tips for success.
Make it realistic and achievable.
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "PlanWise API is running!", "status": "healthy"}

@app.post("/generate-plan")
def generate_plan(request: PlanRequest):
    """
    Generate a personalized plan using AI
    """
    try:
        if OPENAI_API_KEY:
            plan = generate_plan_with_openai(
                request.goal,
                request.deadline,
                request.daily_hours,
                request.role,
                request.topics or ""
            )
        elif GEMINI_API_KEY:
            plan = generate_plan_with_gemini(
                request.goal,
                request.deadline,
                request.daily_hours,
                request.role,
                request.topics or ""
            )
        else:
            raise HTTPException(status_code=500, detail="No AI API key configured")
        
        return {"plan": plan, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-plan")
def review_plan(request: PlanReviewRequest):
    """
    Review and suggest improvements for a plan
    """
    prompt = f"""
You are PlanWise Review AI. Critically analyze the following plan.

Plan:
{request.plan}

Goal: {request.goal}

Analyze:
1. Is the plan realistic given the timeline?
2. Are the daily hours achievable?
3. Is the workload balanced?
4. Are there any gaps or overlaps?

Provide:
- Reality Check: What's unrealistic or challenging?
- Suggestions: Specific improvements
- Optimized Approach: How to make it better

Keep tone encouraging and helpful, not critical.
"""
    
    try:
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful planning review assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            review = response.choices[0].message.content
        elif GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            review = response.text
        else:
            raise HTTPException(status_code=500, detail="No AI API key configured")
        
        return {"review": review, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
