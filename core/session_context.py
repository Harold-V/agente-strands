"""
core/session_context.py
=======================
Módulo de estado de sesión del agente. Singleton a nivel de proceso.

CRÍTICO: Este módulo usa variables de módulo simples (no threading.local,
no contextvars, no async-local). El evaluador llama get_tool_trace() desde
el mismo proceso y espera encontrar las trazas registradas por las herramientas.
Cualquier aislamiento por hilo o contexto async devolvería lista vacía → hard fail.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Estado global del proceso — NO mover a clase con instancias separadas
# ---------------------------------------------------------------------------

_tool_trace: list[dict] = []
_current_customer_id: str | None = None
_current_display_name: str | None = None


# ---------------------------------------------------------------------------
# API pública requerida por el reto
# ---------------------------------------------------------------------------

def add_tool_trace(tool_name: str, input_data: Any, output_data: Any) -> None:
    """
    Registra una llamada a herramienta en la traza de la sesión.
    Debe llamarse dentro de cada herramienta ANTES de retornar su resultado.

    Args:
        tool_name:   Nombre de la herramienta invocada (ej. "verify_customer").
        input_data:  Parámetros de entrada tal como los recibió la herramienta.
        output_data: Resultado retornado por la herramienta.
    """
    _tool_trace.append({
        "tool": tool_name,
        "input": input_data,
        "output": output_data,
    })


def set_session_customer(customer_id: str, display_name: str) -> None:
    """
    Registra la identidad del cliente autenticado en la sesión actual.
    Solo debe llamarse desde verify_customer tras validación exitosa.

    Args:
        customer_id:  ID único del cliente (ej. "1001").
        display_name: Nombre para mostrar al usuario (ej. "Carlos").
    """
    global _current_customer_id, _current_display_name
    _current_customer_id = customer_id
    _current_display_name = display_name


def reset_session() -> None:
    """
    Limpia completamente el estado de la sesión.
    Debe llamarse al iniciar una nueva conversación o cuando el CLI
    recibe el comando 'reset'.
    """
    global _tool_trace, _current_customer_id, _current_display_name
    _tool_trace = []
    _current_customer_id = None
    _current_display_name = None


def get_tool_trace() -> list[dict]:
    """
    Retorna la lista completa de trazas de herramientas de la sesión actual.
    Usada por el evaluador automatizado para verificar anti-alucinación.

    Returns:
        Lista de dicts con claves: tool, input, output.
    """
    return list(_tool_trace)


def get_tool_trace_length() -> int:
    """
    Retorna el número de herramientas llamadas en la sesión actual.

    Returns:
        Entero >= 0.
    """
    return len(_tool_trace)


def get_tool_trace_since(index: int) -> list[dict]:
    """
    Retorna las trazas registradas desde la posición `index` en adelante.
    Útil para aislar las herramientas usadas en el turno actual.

    Args:
        index: Posición inicial (0-based). Típicamente = longitud antes del turno.

    Returns:
        Sub-lista de trazas desde index hasta el final.
    """
    return list(_tool_trace[index:])


# ---------------------------------------------------------------------------
# Helpers internos (usados por las herramientas, no por el evaluador)
# ---------------------------------------------------------------------------

def get_current_customer() -> dict | None:
    """
    Retorna los datos del cliente autenticado en la sesión, o None si no hay.
    Las herramientas de datos sensibles deben consultar esto antes de ejecutar.

    Returns:
        Dict con customer_id y display_name, o None.
    """
    if _current_customer_id is None:
        return None
    return {
        "customer_id": _current_customer_id,
        "display_name": _current_display_name,
    }


def is_authenticated() -> bool:
    """
    Retorna True si hay un cliente autenticado en la sesión actual.
    """
    return _current_customer_id is not None
