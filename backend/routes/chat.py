"""
Chat API routes with RAG support.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.lm_router import lm_router
from services.rag_service import rag_service
from services.gemini_client import LM_UNAVAILABLE_PREFIX
from utils.chat_tools import _render_tool_response, execute_chat_tool


router = APIRouter()


class ChatRequest(BaseModel):
    text: str
    game: str = None
    use_rag: bool = True
    lm_provider: str = "auto"
    tool: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    sources: list = []
    context_used: bool = False
    sources_count: int = 0
    lm_provider: Optional[str] = None
    tool_name: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None


def _chat_fallback_for_lm_unavailable(user_text: str, lm_response: str, raw_game: Optional[str] = None) -> str:
    """
    Generate a helpful fallback response when LLM is unavailable.
    """
    if lm_response.startswith(LM_UNAVAILABLE_PREFIX):
        game_context = f" for {raw_game}" if raw_game else ""
        return (
            f"I apologize, but I'm currently unable to connect to the AI language model{game_context}. "
            f"This might be due to API key issues or service unavailability. "
            f"Your message was: \"{user_text}\". "
            f"Please check your API key configuration or try again later."
        )
    return lm_response


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    AI chat endpoint with optional RAG context and tool calling.
    """
    try:
        if request.tool:
            tool_name = request.tool.get("name")
            if not tool_name:
                raise HTTPException(status_code=400, detail="Tool name is required")

            tool_params = request.tool.get("params") or {}
            tool_result = await execute_chat_tool(tool_name, tool_params)
            response_text = _render_tool_response(tool_name, tool_result)

            return ChatResponse(
                response=response_text,
                sources=[],
                context_used=False,
                sources_count=0,
                lm_provider=None,
                tool_name=tool_name,
                tool_result=tool_result,
            )

        # Prepare context if RAG is enabled
        context_docs = []
        if request.use_rag and request.game:
            try:
                from utils.validation import _require_game_key
                game_key = _require_game_key(request.game)
                context_docs = rag_service.retrieve_context(
                    query=request.text,
                    game=game_key,
                    top_k=3,
                )
            except (ValueError, Exception):
                # Invalid game key or retrieval failure — continue without RAG
                context_docs = []

        # Build prompt with context if available
        if context_docs:
            context_text = "\n".join([doc.get("content", "") for doc in context_docs])
            augmented_prompt = f"Context:\n{context_text}\n\nUser Question: {request.text}"
            context_used = True
        else:
            augmented_prompt = request.text
            context_used = False

        # Get response from language model via router (auto-failover across providers)
        selected_provider = request.lm_provider or "auto"
        try:
            result = await lm_router.generate_with_provider(
                augmented_prompt,
                preferred_provider=request.lm_provider,
            )
            selected_provider = result.get("provider", selected_provider)
            lm_response = result.get("response", "")

            if lm_response.startswith(LM_UNAVAILABLE_PREFIX):
                lm_response = _chat_fallback_for_lm_unavailable(
                    request.text, lm_response, request.game
                )

        except Exception as e:
            lm_response = _chat_fallback_for_lm_unavailable(
                request.text, f"Error: {str(e)}", request.game
            )

        return ChatResponse(
            response=lm_response,
            sources=context_docs,
            context_used=context_used,
            sources_count=len(context_docs),
            lm_provider=selected_provider,
            tool_name=None,
            tool_result=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))