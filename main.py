from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
logger.info(f"Groq API Key present: {bool(GROQ_API_KEY)}")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set in environment variables")


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
    client = get_groq_client()
    if not client:
        return JSONResponse(
            status_code=500,
            content={"error": "Groq API key not configured"}
        )

    logger.info(f"Generating plan (streaming) for goal: {request.goal}")

    prompt = f"""
You are PlanWise, a friendly and intelligent AI planning assistant.
Create a detailed study/plan for the following goal:

Role: {request.role}
Goal: {request.goal}
Deadline: {request.deadline} days
Daily Available Hours: {request.daily_hours} hours
Topics: {request.topics if request.topics else 'Not specified'}

FORMATTING REQUIREMENTS (VERY IMPORTANT):
- DO NOT use markdown tables. They do not display well on mobile screens.
- Use bullet points, numbered lists, or simple text sections instead.
- Use **bold** for section headings and key terms.
- Use emojis sparingly for visual appeal.
- Keep lines short (under 60 characters where possible).
- Leave a blank line between sections for readability.

TIME SCHEDULING RULES (CRITICAL - READ CAREFULLY):
1. If the user specifies a start and end clock time in their goal or topics (e.g., "study from 9am to 2pm"), then use actual clock times (e.g., 09:00 - 09:30, 09:30 - 10:00).
2. If the user ONLY specifies total hours (e.g., "5 hours") and does NOT specify a start time, you MUST use a countdown/relative timer starting from 00:00.
   - Example for 5 hours: 
     - 00:00 - 01:00 → Deep Work Session 1
     - 01:00 - 01:15 → Break
     - 01:15 - 02:15 → Deep Work Session 2
     - ... and so on until 05:00.
3. DO NOT assume the day starts at 9:00 AM or any other arbitrary time unless the user explicitly asked for it.

Generate a structured plan with:
1. Weekly breakdown of topics (use bullet points, not tables)
2. Daily schedule (follow the TIME SCHEDULING RULES above)
3. Tips for success

Make it realistic and actionable.
"""

    models_to_try = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile"
    ]

    def stream_generator():
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Trying model (streaming): {model}")
                stream = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful planning assistant. Always format output for mobile screens using bullet points and lists, never tables. Follow the TIME SCHEDULING RULES strictly."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                logger.info(f"Model {model} streaming completed")
                return
            except Exception as e:
                logger.warning(f"Model {model} streaming failed: {str(e)}")
                last_error = e
                continue
        logger.error("All Groq models failed for streaming")
        yield f"\n\n❌ Error: All AI models failed. {str(last_error)}"

    return StreamingResponse(
        stream_generator(),
        media_type="text/plain; charset=utf-8"
    )


@app.post("/review-plan")
async def review_plan(request: PlanReviewRequest):
    client = get_groq_client()
    if not client:
        return JSONResponse(
            status_code=500,
            content={"error": "Groq API key not configured"}
        )

    logger.info(f"Reviewing plan (streaming) for goal: {request.goal}")

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

    models_to_try = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile"
    ]

    def stream_generator():
        last_error = None
        for model in models_to_try:
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful planning review assistant. Always format output for mobile screens using bullet points and lists, never tables."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                logger.info(f"Review model {model} streaming completed")
                return
            except Exception as e:
                logger.warning(f"Review model {model} streaming failed: {str(e)}")
                last_error = e
                continue
        yield f"\n\n❌ Error: All AI models failed. {str(last_error)}"

    return StreamingResponse(
        stream_generator(),
        media_type="text/plain; charset=utf-8"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
