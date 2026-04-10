"""
tools/policy_tools.py
=====================
Herramienta para búsqueda en documentos de política de la empresa.

El agente DEBE llamar esta herramienta antes de responder cualquier
pregunta sobre devoluciones, garantías o envíos. No puede responder
desde conocimiento interno del modelo.
"""

from strands import tool  # type: ignore

from core import session_context
from policies.retriever import search_policy as _search_policy


@tool
def search_policy(query: str) -> str:
    """
    Busca información relevante en los documentos de política de la empresa.
    Usar OBLIGATORIAMENTE para preguntas sobre: devoluciones, garantías, envíos,
    plazos, cambios, cancelaciones, cobertura de entrega y condiciones de compra.
    Nunca respondas estas preguntas desde tu conocimiento interno.

    Args:
        query: La pregunta o tema a buscar en las políticas
               (ej. "plazo de devolución", "garantía de electrónicos",
               "tiempos de entrega Bogotá", "cómo cancelar un pedido").

    Returns:
        Secciones relevantes de las políticas de la empresa.
    """
    input_data = {"query": query}
    result_text = _search_policy(query)

    session_context.add_tool_trace(
        "search_policy",
        input_data,
        {"retrieved_sections": result_text[:200] + "..." if len(result_text) > 200 else result_text},
    )
    return result_text
