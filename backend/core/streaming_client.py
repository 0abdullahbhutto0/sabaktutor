"""
Streaming LLM Client Module
=============================
OpenRouter client with SSE streaming support.
Yields tokens as they arrive for real-time UX.
"""

import json
import time
from typing import Iterator, Optional, Callable
import requests




class StreamingLLMClient:
    """
    OpenRouter client with streaming support via Server-Sent Events (SSE).
    
    Features:
    - Token-by-token streaming for real-time responses
    - Automatic retry with exponential backoff
    - Performance logging per request
    - Request cancellation support
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.0-flash-001",
        base_url: str = "https://openrouter.ai/api/v1",
        max_retries: int = 3,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self._session = requests.Session()
        
    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = False,
    ) -> str:
        """
        Non-streaming completion. Returns full response.
        
        Args:
            prompt: User prompt
            system: System message
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: If True, raises ValueError (use stream_complete instead)
            
        Returns:
            Complete response text
        """
        if stream:
            raise ValueError("Use stream_complete() for streaming. complete() is non-streaming only.")
      
        for attempt in range(self.max_retries):
            try:
                response = self._make_request(
                    prompt, system, temperature, max_tokens, stream=False
                )
                result = response["choices"][0]["message"]["content"] 
                return result
                    
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue 
                raise
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Max retries exceeded: {e}")
                time.sleep(2 ** attempt)
            
        raise RuntimeError("Max retries exceeded")
    
    def stream_complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Iterator[str]:
        """
        Streaming completion yielding tokens as they arrive.
        
        Args:
            prompt: User prompt
            system: System message
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            on_token: Optional callback for each token (for side effects like UI updates)
            
        Yields:
            Token strings (may be partial words)
        """
            
        start_time = time.time()
        total_tokens = 0
        full_response = []
            
        try:
            response = self._make_request(
                prompt, system, temperature, max_tokens, stream=True
            )
                
            for line in response.iter_lines():
                if not line:
                    continue    
                line = line.decode("utf-8")
                if line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    data = line[6:]  
                        
                    if data == "[DONE]":
                        break
                        
                    try:
                        chunk = json.loads(data)
                        
                        if "error" in chunk:
                            error_msg = chunk["error"].get("message", "Unknown error")
                            raise RuntimeError(f"Stream error: {error_msg}")
                            
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                            
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                            
                        if token:
                            total_tokens += 1
                            full_response.append(token)
                            if on_token:
                                on_token(token) 
                            yield token
                                
                    except json.JSONDecodeError:
                        continue
                
            duration = (time.time() - start_time) * 1000
        except Exception as e:
                
            raise
    
    def _make_request(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> requests.Response:
        """Make the actual HTTP request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Sindh Board Quiz System",
        }
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        
        
        response = self._session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
            stream=stream,
        )
        
        
        response.raise_for_status()
        
        if stream:
            return response
        else:
            return response.json()
    
    def close(self):
        """Close the HTTP session."""
        self._session.close()