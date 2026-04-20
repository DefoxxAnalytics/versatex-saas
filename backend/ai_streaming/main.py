"""
FastAPI Streaming Service for AI Insights.

Provides Server-Sent Events (SSE) streaming for real-time LLM responses.
Runs as a separate microservice alongside Django backend.

Usage:
    uvicorn ai_streaming.main:app --host 0.0.0.0 --port 8002
"""
import json
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Insights Streaming Service",
    description="Real-time streaming for AI-powered procurement insights",
    version="1.0.0"
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default-key")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class StreamRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt for context"
    )
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model to use"
    )
    max_tokens: int = Field(
        default=2000,
        ge=1,
        le=4096,
        description="Maximum tokens in response"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Sampling temperature"
    )
    organization_id: Optional[int] = Field(
        default=None,
        description="Organization ID for context"
    )


class QuickQueryRequest(BaseModel):
    query: str = Field(..., description="Quick query about procurement data")
    context: Optional[dict] = Field(
        default=None,
        description="Optional context data (spending stats, etc.)"
    )
    organization_id: Optional[int] = Field(
        default=None,
        description="Organization ID"
    )


async def verify_token(request: Request) -> dict:
    """Verify JWT token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


PROCUREMENT_CHAT_PROMPT = """You are an AI procurement analytics assistant for Versatex Analytics.
You help users understand their procurement data, identify cost savings opportunities,
analyze supplier performance, and answer questions about their spending patterns.

Guidelines:
- Be concise and actionable in your responses
- Reference specific data when available
- Suggest follow-up questions or analyses
- Flag any concerning patterns or risks
- Use clear formatting with bullet points for lists
- Include confidence levels when making estimates

When uncertain, ask clarifying questions rather than guessing."""


def get_anthropic_client():
    """Get Anthropic client if available."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def get_openai_client():
    """Get OpenAI client if available."""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.warning("openai package not installed")
        return None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
    }


@app.post("/api/ai/stream")
async def stream_chat(
    request: StreamRequest,
    user: dict = Depends(verify_token)
):
    """
    Stream chat responses using Server-Sent Events.

    Attempts Anthropic first, falls back to OpenAI if unavailable.
    """
    anthropic_client = get_anthropic_client()
    openai_client = get_openai_client()

    if not anthropic_client and not openai_client:
        raise HTTPException(
            status_code=503,
            detail="No AI provider configured"
        )

    system_prompt = request.system_prompt or PROCUREMENT_CHAT_PROMPT
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    async def anthropic_stream():
        """Stream from Anthropic Claude."""
        try:
            async with anthropic_client.messages.stream(
                model=request.model,
                max_tokens=request.max_tokens,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"

                final_message = await stream.get_final_message()
                yield f"data: {json.dumps({'done': True, 'usage': {'input_tokens': final_message.usage.input_tokens, 'output_tokens': final_message.usage.output_tokens}})}\n\n"
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def openai_stream():
        """Stream from OpenAI."""
        try:
            openai_messages = [{"role": "system", "content": system_prompt}]
            openai_messages.extend(messages)

            stream = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=openai_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'token': chunk.choices[0].delta.content})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    if anthropic_client and request.model.startswith("claude"):
        stream_generator = anthropic_stream()
    elif openai_client:
        stream_generator = openai_stream()
    else:
        stream_generator = anthropic_stream()

    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/ai/quick-query")
async def quick_query(
    request: QuickQueryRequest,
    user: dict = Depends(verify_token)
):
    """
    Stream a quick query response about procurement data.

    Optimized for single-turn Q&A about spending, suppliers, etc.
    """
    context_str = ""
    if request.context:
        context_str = f"\n\nCurrent data context:\n{json.dumps(request.context, indent=2)}"

    system_prompt = f"""{PROCUREMENT_CHAT_PROMPT}{context_str}

Answer the user's question concisely based on the available context."""

    messages = [ChatMessage(role="user", content=request.query)]

    stream_request = StreamRequest(
        messages=messages,
        system_prompt=system_prompt,
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        temperature=0.5,
        organization_id=request.organization_id,
    )

    return await stream_chat(stream_request, user)


@app.post("/api/ai/analyze-insight")
async def analyze_insight_stream(
    request: Request,
    user: dict = Depends(verify_token)
):
    """
    Stream deep analysis of a specific insight.

    Provides detailed breakdown with actionable recommendations.
    """
    data = await request.json()
    insight = data.get("insight", {})
    context = data.get("context", {})

    analysis_prompt = f"""Analyze this procurement insight in detail:

INSIGHT:
Type: {insight.get('type', 'Unknown')}
Title: {insight.get('title', 'No title')}
Description: {insight.get('description', 'No description')}
Severity: {insight.get('severity', 'Unknown')}
Potential Savings: ${insight.get('potential_savings', 0):,.2f}
Confidence: {insight.get('confidence', 0):.0%}

CONTEXT:
{json.dumps(context, indent=2) if context else 'No additional context'}

Provide:
1. Root cause analysis
2. Impact assessment
3. Recommended actions (prioritized)
4. Implementation timeline
5. Expected outcomes
6. Risks and mitigations
7. Success metrics"""

    messages = [ChatMessage(role="user", content=analysis_prompt)]

    stream_request = StreamRequest(
        messages=messages,
        system_prompt=PROCUREMENT_CHAT_PROMPT,
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0.3,
    )

    return await stream_chat(stream_request, user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
