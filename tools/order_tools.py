"""
tools/order_tools.py
====================
Herramientas para consultas sobre pedidos, historial, montos y tracking.

CRÍTICO: Todas estas herramientas verifican is_authenticated() en código
Python antes de ejecutar. No confían solo en el system prompt para el gate.
Todas registran traza con add_tool_trace.
"""

from strands import tool  # type: ignore

from core import session_context
from repositories.order_repo import get_order_repo

# Mensaje estándar cuando no hay autenticación
_AUTH_REQUIRED_MSG = (
    "Para consultar información de pedidos necesito verificar tu identidad primero. "
    "Por favor compárteme tu número de documento (cédula) o teléfono registrado."
)


@tool
def get_order_status(order_id: str) -> str:
    """
    Retorna el estado actual de un pedido específico del cliente autenticado.
    Incluye estado, fechas clave e información de envío si está disponible.

    Args:
        order_id: ID del pedido a consultar (ej. "2001").

    Returns:
        Estado detallado del pedido, o mensaje de error.
    """
    input_data = {"order_id": order_id}

    if not session_context.is_authenticated():
        result = {"status": "unauthenticated"}
        session_context.add_tool_trace("get_order_status", input_data, result)
        return _AUTH_REQUIRED_MSG

    customer = session_context.get_current_customer()
    repo = get_order_repo()
    order = repo.get_order_by_id(order_id, customer["customer_id"])

    if order is None:
        result = {"status": "not_found", "order_id": order_id}
        session_context.add_tool_trace("get_order_status", input_data, result)
        return f"No encontré el pedido {order_id} asociado a tu cuenta."

    shipment = repo.get_shipment_by_order(order_id)
    tracking_events = repo.get_tracking_by_order(order_id)
    last_event = tracking_events[-1] if tracking_events else None

    result = {
        "status": "found",
        "order_id": order_id,
        "order_status": order.get("status"),
        "total_amount": order.get("total_amount"),
        "created_at": order.get("order_date", order.get("created_at")),
        "delivered_at": order.get("delivered_at"),
        "tracking_number": shipment.get("tracking_number") if shipment else None,
        "carrier": shipment.get("carrier") if shipment else None,
        "last_event": last_event,
    }
    session_context.add_tool_trace("get_order_status", input_data, result)

    lines = [
        f"**Pedido {order_id}**",
        f"Estado: {order.get('status', 'desconocido')}",
        f"Fecha de pedido: {order.get('order_date', order.get('created_at', 'N/A'))}",
    ]
    if order.get("delivered_at"):
        lines.append(f"Entregado: {order['delivered_at']}")
    if shipment:
        lines.append(f"Transportadora: {shipment.get('carrier', 'N/A')}")
        lines.append(f"Guía: {shipment.get('tracking_number', 'N/A')}")
    if last_event:
        lines.append(f"Último evento: {last_event.get('status', last_event.get('event_type', 'N/A'))}")

    return "\n".join(lines)


@tool
def get_order_history(limit: int = 5) -> str:
    """
    Retorna el historial de pedidos del cliente autenticado.

    Args:
        limit: Número máximo de pedidos a retornar (default 5, máximo 10).

    Returns:
        Lista de pedidos recientes con estado y total.
    """
    input_data = {"limit": limit}

    if not session_context.is_authenticated():
        result = {"status": "unauthenticated"}
        session_context.add_tool_trace("get_order_history", input_data, result)
        return _AUTH_REQUIRED_MSG

    customer = session_context.get_current_customer()
    repo = get_order_repo()
    orders = repo.get_orders_by_customer(customer["customer_id"])

    # Limitar resultados
    limit = min(limit, 10)
    orders = orders[:limit]

    result = {
        "status": "found",
        "customer_id": customer["customer_id"],
        "total_orders": len(orders),
        "orders": [
            {"order_id": o.get("order_id"), "status": o.get("status"), "total": o.get("total_amount")}
            for o in orders
        ],
    }
    session_context.add_tool_trace("get_order_history", input_data, result)

    if not orders:
        return "No encontré pedidos registrados en tu cuenta."

    lines = [f"Tus últimos {len(orders)} pedido(s):"]
    for o in orders:
        lines.append(
            f"- Pedido {o.get('order_id')}: "
            f"{o.get('status', 'N/A')} — "
            f"${o.get('total_amount', 'N/A')} COP"
        )
    return "\n".join(lines)


@tool
def get_order_amounts(order_id: str) -> str:
    """
    Retorna el desglose de montos de un pedido: subtotal, IVA (19%) y total.
    Requiere autenticación obligatoria.

    Args:
        order_id: ID del pedido.

    Returns:
        Desglose financiero del pedido.
    """
    input_data = {"order_id": order_id}

    if not session_context.is_authenticated():
        result = {"status": "unauthenticated"}
        session_context.add_tool_trace("get_order_amounts", input_data, result)
        return _AUTH_REQUIRED_MSG

    customer = session_context.get_current_customer()
    repo = get_order_repo()
    order = repo.get_order_by_id(order_id, customer["customer_id"])

    if order is None:
        result = {"status": "not_found", "order_id": order_id}
        session_context.add_tool_trace("get_order_amounts", input_data, result)
        return f"No encontré el pedido {order_id} asociado a tu cuenta."

    result = {
        "status": "found",
        "order_id": order_id,
        "subtotal": order.get("subtotal"),
        "tax": order.get("tax"),
        "shipping_cost": order.get("shipping_cost"),
        "total_amount": order.get("total_amount"),
        "payment_method": order.get("payment_method"),
    }
    session_context.add_tool_trace("get_order_amounts", input_data, result)

    lines = [
        f"**Desglose financiero — Pedido {order_id}**",
        f"Subtotal: ${order.get('subtotal', 'N/A')} COP",
        f"IVA (19%): ${order.get('tax', 'N/A')} COP",
        f"Costo de envío: ${order.get('shipping_cost', 'N/A')} COP",
        f"**Total: ${order.get('total_amount', 'N/A')} COP**",
        f"Método de pago: {order.get('payment_method', 'N/A')}",
    ]
    return "\n".join(lines)


@tool
def get_order_items(order_id: str) -> str:
    """
    Retorna los ítems de un pedido con su estado, garantía y fecha límite de devolución.

    Args:
        order_id: ID del pedido.

    Returns:
        Lista de ítems del pedido con información relevante.
    """
    input_data = {"order_id": order_id}

    if not session_context.is_authenticated():
        result = {"status": "unauthenticated"}
        session_context.add_tool_trace("get_order_items", input_data, result)
        return _AUTH_REQUIRED_MSG

    customer = session_context.get_current_customer()
    repo = get_order_repo()

    # Verificar que el pedido pertenece al cliente
    order = repo.get_order_by_id(order_id, customer["customer_id"])
    if order is None:
        result = {"status": "not_found", "order_id": order_id}
        session_context.add_tool_trace("get_order_items", input_data, result)
        return f"No encontré el pedido {order_id} asociado a tu cuenta."

    items = repo.get_items_by_order(order_id)
    result = {
        "status": "found",
        "order_id": order_id,
        "items": items,
    }
    session_context.add_tool_trace("get_order_items", input_data, result)

    if not items:
        return f"El pedido {order_id} no tiene ítems registrados."

    lines = [f"**Ítems del pedido {order_id}:**"]
    for item in items:
        lines.append(
            f"- {item.get('product_name', item.get('product_id', 'Producto'))} "
            f"x{item.get('quantity', 1)} — "
            f"${item.get('unit_price', 'N/A')} COP | "
            f"Estado: {item.get('item_status', 'N/A')} | "
            f"Devolución hasta: {item.get('return_deadline', 'N/A')}"
        )
    return "\n".join(lines)
