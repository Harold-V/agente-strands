"""
core/config.py
==============
Configuración centralizada del agente.
Único lugar donde se menciona Ollama o Bedrock.
Cambiar LLM_PROVIDER en el entorno es suficiente para migrar.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data" / "raw"
POLICIES_DIR = ROOT_DIR / "policies"

# ---------------------------------------------------------------------------
# Provider del modelo
# ---------------------------------------------------------------------------

# Valores válidos: "ollama" | "bedrock"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

# --- Ollama ---
OLLAMA_MODEL_ID: str = os.getenv("OLLAMA_MODEL_ID", "qwen2.5:7b")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# --- Bedrock ---
BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "us-east-1")

# ---------------------------------------------------------------------------
# Parámetros del agente
# ---------------------------------------------------------------------------

AGENT_MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "1024"))
AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.1"))

# ---------------------------------------------------------------------------
# Factory del modelo — única función que importa librerías de providers
# ---------------------------------------------------------------------------

def get_model():
    """
    Retorna el objeto de modelo configurado según LLM_PROVIDER.
    agent.py llama esta función; nunca importa ollama/bedrock directamente.

    Returns:
        Objeto de modelo compatible con Strands Agent.

    Raises:
        ValueError: Si LLM_PROVIDER no es reconocido.
        ImportError: Si las dependencias del provider no están instaladas.
    """
    if LLM_PROVIDER == "ollama":
        return _get_ollama_model()
    elif LLM_PROVIDER == "bedrock":
        return _get_bedrock_model()
    else:
        raise ValueError(
            f"LLM_PROVIDER='{LLM_PROVIDER}' no reconocido. "
            "Valores válidos: 'ollama', 'bedrock'."
        )


def _get_ollama_model():
    """
    Construye modelo Ollama compatible con Strands.
    """
    try:
        # Intento 1: API nativa de Strands para Ollama (si existe)
        from strands.models.ollama import OllamaModel  # type: ignore
        return OllamaModel(
            model_id=OLLAMA_MODEL_ID,
            base_url=OLLAMA_BASE_URL,
            temperature=AGENT_TEMPERATURE,
            max_tokens=AGENT_MAX_TOKENS,
        )
    except ImportError:
        # Intento 2: wrapper OpenAI-compatible (Ollama expone /v1)
        from strands.models.openai import OpenAIModel  # type: ignore
        return OpenAIModel(
            client_args={
                "base_url": OLLAMA_BASE_URL,
                "api_key": "ollama",
            },
            model_id=OLLAMA_MODEL_ID,
            params={
                "temperature": AGENT_TEMPERATURE,
                "max_tokens": AGENT_MAX_TOKENS,
            },
        )


def _get_bedrock_model():
    """
    Construye modelo Bedrock compatible con Strands.
    Requiere credenciales AWS configuradas en el entorno.
    """
    from strands.models import BedrockModel  # type: ignore
    return BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=BEDROCK_REGION,
        temperature=AGENT_TEMPERATURE,
        max_tokens=AGENT_MAX_TOKENS,
    )
