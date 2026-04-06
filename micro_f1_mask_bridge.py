import os
import httpx
import json
import re
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from vault_manager import VaultManager
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARPA-F1-Bridge")

app = FastAPI(title="ARPA Micro Series: F1 Mask Bridge")

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
F1_MASK_MODEL = os.getenv("F1_MASK_MODEL", "arpacorp/micro-f1-mask")
CLOUD_LLM_URL = os.getenv("CLOUD_LLM_URL", "https://api.openai.com/v1/chat/completions")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")

# Initialize Vault
vault = VaultManager(host=os.getenv("REDIS_HOST", "localhost"), ttl=7200)

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    session_id: Optional[str] = "default-session"
    temperature: Optional[float] = 0.7

@app.post("/v1/chat/completions")
async def chat_proxy(request: ChatCompletionRequest):
    session_id = request.session_id
    logger.info(f"Incoming request for session: {session_id}")
    
    # 1. Processing Current Messages (PII Extraction)
    scrubbed_messages = []
    
    for msg in request.messages:
        if msg.role == "user":
            # Call F1 Mask to detect PII
            entities = await extract_pii(msg.content)
            
            # Mask the content using the Vault
            masked_content = msg.content
            # Sort entities by value length to avoid partial replacements (e.g., 'John' before 'John Doe')
            entities.sort(key=lambda x: len(x['val']), reverse=True)
            
            for ent in entities:
                pii_type = ent['type']
                pii_val = ent['val']
                
                # Get/Create consistent token
                token = vault.get_or_create_token(session_id, pii_type, pii_val)
                masked_content = masked_content.replace(pii_val, token)
            
            scrubbed_messages.append({"role": "user", "content": masked_content})
            logger.info(f"Masked user prompt: {masked_content}")
        else:
            scrubbed_messages.append(msg.model_dump())

    # 2. Forward to Cloud LLM
    headers = {
        "Authorization": f"Bearer {CLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": request.model, # Or force a specific cloud model
        "messages": scrubbed_messages,
        "temperature": request.temperature,
        "stream": False # Streaming requires complex trunk-based reconstruction
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(CLOUD_LLM_URL, json=payload, headers=headers)
            response.raise_for_status()
            cloud_result = response.json()
    except Exception as e:
        logger.error(f"Cloud LLM Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Cloud LLM communication failure")

    # 3. Post-Process Response (Reconstruction)
    cloud_msg = cloud_result['choices'][0]['message']['content']
    logger.info(f"Received Cloud response with tokens: {cloud_msg}")
    
    final_content = vault.reconstruct_text(session_id, cloud_msg)
    logger.info(f"Reconstructed final output: {final_content}")
    
    # Replace back in the response object
    cloud_result['choices'][0]['message']['content'] = final_content
    cloud_result['model'] = f"ARPA-F1-Mask({cloud_result['model']})"
    
    return cloud_result

async def extract_pii(text: str) -> List[Dict[str, Any]]:
    """Calls Ollama's F1 Mask model to find PII entities."""
    payload = {
        "model": F1_MASK_MODEL,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # F1 Mask outputs the 'replace_pii' function call
            # We extract the 'entities' list from the arguments
            content = result.get("message", {}).get("content", "{}")
            
            # The model might return a string or a JSON object depending on Ollama config
            if isinstance(content, str):
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback if model outputs messy text around JSON
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    data = json.loads(match.group(0)) if match else {}
            else:
                data = content
                
            return data.get("arguments", {}).get("entities", [])
            
    except Exception as e:
        logger.warning(f"Ollama Extraction Error: {str(e)}. Proceeding without extraction.")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
