from src.config import Settings
from src.services.ollama.client import OllamaClient

def make_ollama_client(settings: Settings) -> OllamaClient:
    """Create an Ollama client using settings from the application state."""
    return OllamaClient(host=settings.ollama.host, model=settings.ollama.model)