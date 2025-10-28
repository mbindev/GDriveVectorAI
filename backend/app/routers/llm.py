from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_google_vertexai import ChatVertexAI
from langchain.schema import HumanMessage, AIMessage
from app.services.embedding_service import get_text_embedding
from app.services.vector_db_service import search_documents
from app.main import settings
import vertexai

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    enable_rag: bool = True

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[dict]] = None

class ModelsResponse(BaseModel):
    models: List[str]

def get_llm(model_name: str = "gemini-1.5-pro"):
    """Initialize Vertex AI LLM."""
    vertexai.init(project=settings.google_project_id, location="us-central1")
    return ChatVertexAI(model_name=model_name, temperature=0.7)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    """Chat with LLM, optionally using RAG."""
    try:
        llm = get_llm()
        sources = None

        if request.enable_rag:
            # Generate embedding for user message
            query_embedding = get_text_embedding(request.message)

            # Search for relevant documents
            search_results = search_documents(query_embedding, limit=3)
            sources = search_results

            # Build context from search results
            context = "\n\n".join([
                f"Document: {doc['file_name']}\nContent: {doc['extracted_text_snippet']}"
                for doc in search_results
            ])

            # Create RAG prompt
            rag_prompt = f"""Based on the following context from documents, answer the user's question. If the context doesn't contain enough information to answer the question, say so and provide a general response.

Context:
{context}

User Question: {request.message}

Answer:"""

            messages = [HumanMessage(content=rag_prompt)]
        else:
            messages = [HumanMessage(content=request.message)]

        # Add conversation history if provided
        if request.history:
            for msg in request.history[-6:]:  # Keep last 6 messages for context
                if msg.get('role') == 'user':
                    messages.insert(-1, HumanMessage(content=msg['content']))
                elif msg.get('role') == 'assistant':
                    messages.insert(-1, AIMessage(content=msg['content']))

        # Get LLM response
        response = llm.invoke(messages)

        return ChatResponse(
            response=response.content,
            sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.get("/models", response_model=ModelsResponse)
async def get_available_models():
    """Get list of available Vertex AI models."""
    # This is a simplified list - in production, you might want to fetch from Vertex AI API
    models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]

    return ModelsResponse(models=models)
