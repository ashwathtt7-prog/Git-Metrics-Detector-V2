
import asyncio
import logging
import sys
from unittest.mock import MagicMock, AsyncMock

# Adjust path to find app module
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm.provider_chain import LLMProviderChain
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.openrouter_provider import OpenRouterProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("Testing LLM Provider Fallback...")

    # Initialize provider instances
    gemini = GeminiProvider()
    groq = GroqProvider()
    openrouter = OpenRouterProvider()
    
    # Mock Gemini failure
    gemini.is_available = MagicMock(return_value=True)
    gemini.generate = AsyncMock(side_effect=Exception("Simulated Gemini Failure"))
    gemini.config = MagicMock(return_value=MagicMock(name="gemini-mock", max_context_tokens=100))
    
    with open("repro_output.txt", "w") as f:
        # Redirect stdout/stderr to this file or just write to it
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()

        try:
            # Check API keys (without revealing them)
            from app.config import settings
            log(f"Gemini Key Present: {bool(settings.gemini_api_key)}")
            log(f"Groq Key Present: {bool(settings.groq_api_key)}")
            log(f"OpenRouter Key Present: {bool(settings.openrouter_api_key)}")

            # Override chain availability for test if needed, but we rely on real logic for Groq
            # Actually, let's force Groq to be available if key is missing, for mocking purposes
            if not settings.groq_api_key:
                log("Forcing Groq availability (Mock)")
                groq.is_available = MagicMock(return_value=True)
                groq.generate = AsyncMock(return_value='{"status": "success", "provider": "groq"}')
                groq.config = MagicMock(return_value=MagicMock(name="groq-mock", max_context_tokens=100))
            else:
                 log(f"Using real Groq client with model: {groq.config().name}")

            # Re-create chain with potentially modified providers
            # We need to make sure the chain sees them as available
            providers = [gemini, groq, openrouter]
            chain = LLMProviderChain(providers)
            
            # Override retries
            chain.MAX_RETRIES_PER_PROVIDER = 1
            
            log("Starting generation...")
            # Test prompt does NOT include "JSON" to verify GroqProvider fixes it
            result = await chain.generate("Test prompt")
            log(f"Result: {result}")
            log("Fallback successful!")
        except Exception as e:
            import traceback
            log(f"Fallback failed with error: {str(e)}")
            log(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
