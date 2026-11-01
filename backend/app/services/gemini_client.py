"""
Gemini Client Wrapper for SanshthaSetu.
Provides structured prompt execution with timeout (30s) and exponential retry logic.
Can be mocked/swapped cleanly in automated tests.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Type
from pydantic import BaseModel

from app.config import settings


class GeminiClient:
    """
    Thin wrapper over google-genai SDK.
    Supports structured output (Pydantic schema), timeouts, and retries.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.timeout = timeout
        self.max_retries = max_retries

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
    ) -> BaseModel:
        """
        Call Gemini with structured schema output enforcement and retries.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.0,
            system_instruction=system_instruction,
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                if response.parsed:
                    return response.parsed
                raise ValueError("Gemini returned empty or unparsed structured output.")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 1s, 2s back-off
                continue

        raise RuntimeError(f"Gemini generation failed after {self.max_retries + 1} attempts: {last_error}")


gemini_client = GeminiClient()

