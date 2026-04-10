"""
tools/catalog_tools.py
======================
Herramientas para consultas de catálogo: productos, stock y promociones.
No requieren autenticación — datos públicos.
Todas registran traza con add_tool_trace.
"""

from strands import tool  # type: ignore

from core import session_context
from repositories.catalog_repo import get_catalog_repo


@tool
def search_products(query: str) -> str:
    """
    Busca productos en el catálogo por nombre, marca o categoría.
    No requiere autenticación. Retorna precio, disponibilidad básica y descripción.

    Args:
        query: Término de búsqueda (ej. "Samsung Galaxy", "zapatos Nike", "televisor").

    Returns:
        Lista de productos encontrados con precio en COP y estado de stock.
    """
    input_data = {"query": query}
    repo = get_catalog_repo()
    products = repo.search_products(query, limit=5)

    result = {"status": "found", "count": len(products), "products": products}
    session_context.add_tool_trace("search_products", input_data, result)

    if not products:
        return f"No encontré productos que coincidan con '{query}'."

    lines = [f"Encontré {len(products)} producto(s) para '{query}':"]
    for p in products:
        lines.append(
            f"- [{p.get('product_id')}] {p.get('product_name', 'N/A')} "
            f"— ${p.get('price', 'N/A')} COP "
            f"| {p.get('brand_name', p.get('brand', 'N/A'))} "
            f"| Envío gratis: {'Sí' if str(p.get('free_shipping','')).lower() in ('true','1','yes') else 'No'}"
        )
    return "\n".join(lines)


@tool
def get_product_detail(product_id: str) -> str:
    """
    Retorna información detallada de un producto específico.
    Incluye precio, garantía, plazo de devolución, categoría y si tiene envío gratis.

    Args:
        product_id: ID del producto (ej. "5001").

    Returns:
        Detalle completo del producto.
    """
    input_data = {"product_id": product_id}
    repo = get_catalog_repo()
    product = repo.get_product_by_id(product_id)

    result = {"status": "found" if product else "not_found", "product": product}
    session_context.add_tool_trace("get_product_detail", input_data, result)

    if product is None:
        return f"No encontré el producto con ID {product_id}."

    warranty_months = product.get("warranty_months", product.get("warranty_days", "N/A"))
    return_days = product.get("return_days", "N/A")
    is_final_sale = str(product.get("is_final_sale", "false")).lower() in ("true", "1")

    lines = [
        f"**{product.get('product_name', 'N/A')}** (ID: {product_id})",
        f"Precio: ${product.get('price', 'N/A')} COP",
        f"Marca: {product.get('brand_name', product.get('brand', 'N/A'))}",
        f"Categoría: {product.get('category_name', product.get('category', 'N/A'))}",
        f"Garantía: {warranty_months} mes(es)",
        f"Plazo de devolución: {'Sin devolución (venta final)' if is_final_sale else f'{return_days} días'}",
        f"Envío gratis: {'Sí' if str(product.get('free_shipping','')).lower() in ('true','1','yes') else 'No'}",
        f"Estado: {'Activo' if str(product.get('status','active')).lower() == 'active' else 'Inactivo'}",
    ]
    return "\n".join(lines)


@tool
def check_stock(product_id: str) -> str:
    """
    Consulta el stock disponible de un producto.
    Stock disponible = stock_qty - reserved_qty.

    Args:
        product_id: ID del producto (ej. "5001").

    Returns:
        Disponibilidad del producto y fecha de reabastecimiento si aplica.
    """
    input_data = {"product_id": product_id}
    repo = get_catalog_repo()
    stock = repo.get_stock(product_id)

    result = {"status": "found" if stock else "not_found", "stock": stock}
    session_context.add_tool_trace("check_stock", input_data, result)

    if stock is None:
        return f"No encontré información de stock para el producto {product_id}."

    available = stock["available"]
    if available > 0:
        msg = f"Producto {product_id}: **{available} unidades disponibles**."
    else:
        restock = stock.get("restocking_date")
        msg = (
            f"Producto {product_id}: **Sin stock disponible** en este momento."
            + (f" Reabastecimiento estimado: {restock}." if restock else "")
        )
    return msg


@tool
def get_active_promotions() -> str:
    """
    Retorna las promociones activas disponibles en la tienda.
    No requiere autenticación.

    Returns:
        Lista de promociones vigentes con su descripción y descuento.
    """
    input_data = {}
    repo = get_catalog_repo()
    promotions = repo.get_active_promotions()

    result = {"status": "found", "count": len(promotions), "promotions": promotions}
    session_context.add_tool_trace("get_active_promotions", input_data, result)

    if not promotions:
        return "No hay promociones activas en este momento."

    lines = [f"Hay {len(promotions)} promoción(es) activa(s):"]
    for p in promotions:
        discount = p.get("discount_value", p.get("discount_percent", "N/A"))
        discount_type = p.get("discount_type", "porcentaje")
        applies_to = p.get("category_name", p.get("product_id", "toda la tienda"))
        lines.append(
            f"- {p.get('promotion_name', p.get('name', 'Promoción'))}: "
            f"{discount} {discount_type} en {applies_to}"
        )
    return "\n".join(lines)
