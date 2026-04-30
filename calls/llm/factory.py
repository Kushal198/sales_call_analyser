from .config import LLMConfig
from .openai_provider import OpenAIProvider

def get_llm_provider():
    config = LLMConfig()

    if config.provider == 'openai':
        return OpenAIProvider(config)

    raise ValueError(f"Unsupported provider: {config.provider}")