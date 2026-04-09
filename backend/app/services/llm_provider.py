import os
from langchain_core.language_models.chat_models import BaseChatModel

class LLMProviderFactory:
    """
    Factory pattern to generate LLM models dynamically
    based on the configuration in the Chat Settings.
    This architecture mimics Antigravity/Claude Code agent loops by ensuring
    that prompts and logic remain completely agnostic to the underlying provider.

    Args:
        provider: LLM provider name ('openai', 'gemini', 'claude', 'ollama').
        api_key: Provider API key; falls back to environment variable if None.
        temperature: Sampling temperature (default 0.7).
        max_tokens: Maximum tokens in response (default 1000).
        streaming: Enable streaming mode for astream() support (default True).
    """
    @staticmethod
    def get_llm(
        provider: str,
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        streaming: bool = True,
    ) -> BaseChatModel:
        if provider == 'openai':
            from langchain_openai import ChatOpenAI
            # Use provided API key or fallback to environment variable
            key = api_key or os.getenv('OPENAI_API_KEY')
            return ChatOpenAI(
                model_name='gpt-4o-mini',
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=key,
                streaming=streaming,
            )

        elif provider == 'gemini':
            from langchain_google_genai import ChatGoogleGenerativeAI
            key = api_key or os.getenv('GOOGLE_API_KEY')
            return ChatGoogleGenerativeAI(
                model='gemini-1.5-pro',
                temperature=temperature,
                max_tokens=max_tokens,
                google_api_key=key,
            )

        elif provider == 'claude':
            from langchain_anthropic import ChatAnthropic
            key = api_key or os.getenv('ANTHROPIC_API_KEY')
            return ChatAnthropic(
                model='claude-3-haiku-20240307',
                temperature=temperature,
                max_tokens=max_tokens,
                anthropic_api_key=key,
                streaming=streaming,
            )

        elif provider == 'ollama':
            from langchain_community.chat_models import ChatOllama
            # ollama doesn't typically need an API key
            base_url = api_key or 'http://localhost:11434'
            return ChatOllama(
                model='llama3',
                temperature=temperature,
                base_url=base_url,
            )

        else:
            raise ValueError(f'Unsupported LLM provider: {provider}')
