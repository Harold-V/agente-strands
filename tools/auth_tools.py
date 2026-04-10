"""
tools/auth_tools.py
===================
Herramienta de verificación de identidad del cliente.

CRÍTICO: Esta es la única herramienta que puede llamar set_session_customer().
Toda herramienta de datos sensibles debe verificar is_authenticated() antes
de ejecutar. El gate de autenticación vive aquí y en el system prompt.
"""

from strands import tool  # type: ignore

from core import session_context
from repositories.customer_repo import get_customer_repo


@tool
def verify_customer(identifier: str, id_type: str) -> str:
    """
    Verifica la identidad de un cliente por número de documento (DNI/CC) o teléfono.
    Debe llamarse ANTES de cualquier consulta sobre pedidos, historial o montos.

    Args:
        identifier: El valor exacto del documento o teléfono proporcionado por el usuario.
        id_type:    Tipo de identificador: "dni" para cédula/documento, "phone" para teléfono.

    Returns:
        Mensaje de éxito con el nombre del cliente, o mensaje de error si no se encontró.
    """
    input_data = {"identifier": identifier, "id_type": id_type}

    # Validar id_type
    if id_type not in ("dni", "phone"):
        result = {
            "status": "error",
            "message": "id_type debe ser 'dni' o 'phone'.",
        }
        session_context.add_tool_trace("verify_customer", input_data, result)
        return result["message"]

    # Buscar en el repositorio
    repo = get_customer_repo()
    customer = None

    if id_type == "dni":
        customer = repo.find_by_dni(identifier)
    elif id_type == "phone":
        customer = repo.find_by_phone(identifier)

    # Cliente no encontrado
    if customer is None:
        result = {"status": "not_found"}
        session_context.add_tool_trace("verify_customer", input_data, result)
        # No revelar si el cliente existe o no (seguridad)
        return (
            "No pude verificar tu identidad con los datos proporcionados. "
            "Por favor revisa que el número de documento o teléfono sea correcto."
        )

    # Cliente suspendido
    account_status = str(customer.get("status", "active")).lower()
    if account_status == "suspended":
        result = {"status": "suspended", "customer_id": customer["customer_id"]}
        session_context.add_tool_trace("verify_customer", input_data, result)
        return (
            "Tu cuenta está actualmente suspendida. "
            "Por favor contacta a nuestro equipo de soporte para más información."
        )

    # Autenticación exitosa
    customer_id = str(customer["customer_id"]).strip()
    # Usar nombre del cliente (el CSV puede tener errores tipográficos — se muestra tal cual)
    first_name = str(customer.get("first_name", customer.get("name", "Cliente"))).strip()

    session_context.set_session_customer(customer_id, first_name)

    result = {
        "status": "authenticated",
        "customer_id": customer_id,
        "display_name": first_name,
    }
    session_context.add_tool_trace("verify_customer", input_data, result)

    return (
        f"Identidad verificada correctamente. ¡Bienvenido/a, {first_name}! "
        "Ahora puedo ayudarte con tus pedidos e historial de compras."
    )
