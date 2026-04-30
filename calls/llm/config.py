import os

class LLMConfig:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not set")
