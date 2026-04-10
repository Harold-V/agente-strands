"""
repositories/base.py
====================
Contratos abstractos para todos los repositorios.

Al migrar de CSV a DynamoDB, solo se reemplaza la implementación concreta
de cada repo. Las herramientas (tools/) nunca cambian porque dependen
de estas interfaces, no de la implementación.

Patrón: Repository Pattern ligero — sin ORM, sin abstracción excesiva.
"""

from abc import ABC, abstractmethod
from typing import Any


class CustomerRepositoryBase(ABC):
    """Contrato para acceso a datos de clientes."""

    @abstractmethod
    def find_by_dni(self, dni: str) -> dict | None:
        """
        Busca un cliente por número de documento (DNI/CC/CE/NIT/PA).
        Match exacto. No normaliza ni tolera errores tipográficos.

        Args:
            dni: Número de documento tal como lo ingresó el usuario.

        Returns:
            Dict con campos del cliente, o None si no existe.
        """
        ...

    @abstractmethod
    def find_by_phone(self, phone: str) -> dict | None:
        """
        Busca un cliente por número de teléfono.
        Match exacto sobre el campo 'phone' de customers.csv.

        Args:
            phone: Teléfono tal como lo ingresó el usuario.

        Returns:
            Dict con campos del cliente, o None si no existe.
        """
        ...

    @abstractmethod
    def find_by_id(self, customer_id: str) -> dict | None:
        """
        Busca un cliente por su customer_id (ej. "1001").

        Returns:
            Dict con campos del cliente, o None si no existe.
        """
        ...


class OrderRepositoryBase(ABC):
    """Contrato para acceso a pedidos, items, envíos y tracking."""

    @abstractmethod
    def get_orders_by_customer(self, customer_id: str) -> list[dict]:
        """
        Retorna todos los pedidos de un cliente.

        Args:
            customer_id: ID del cliente autenticado.

        Returns:
            Lista de dicts de pedidos (puede ser vacía). Nunca None.
        """
        ...

    @abstractmethod
    def get_order_by_id(self, order_id: str, customer_id: str) -> dict | None:
        """
        Retorna un pedido específico, SOLO si pertenece al customer_id dado.
        Esto evita acceso cruzado entre clientes.

        Args:
            order_id:    ID del pedido.
            customer_id: ID del cliente autenticado (guard de seguridad).

        Returns:
            Dict del pedido, o None si no existe o no pertenece al cliente.
        """
        ...

    @abstractmethod
    def get_items_by_order(self, order_id: str) -> list[dict]:
        """
        Retorna los ítems de un pedido.

        Returns:
            Lista de dicts de ítems. Nunca None.
        """
        ...

    @abstractmethod
    def get_shipment_by_order(self, order_id: str) -> dict | None:
        """
        Retorna la información de envío de un pedido.

        Returns:
            Dict de envío, o None si no hay registro.
        """
        ...

    @abstractmethod
    def get_tracking_by_order(self, order_id: str) -> list[dict]:
        """
        Retorna el historial de eventos de trazabilidad de un pedido.

        Returns:
            Lista de eventos ordenados por timestamp. Nunca None.
        """
        ...


class CatalogRepositoryBase(ABC):
    """Contrato para acceso al catálogo público (no requiere autenticación)."""

    @abstractmethod
    def get_product_by_id(self, product_id: str) -> dict | None:
        """Retorna un producto por su ID, o None."""
        ...

    @abstractmethod
    def search_products(self, query: str, limit: int = 5) -> list[dict]:
        """
        Busca productos por nombre, marca o categoría.

        Args:
            query: Texto de búsqueda.
            limit: Máximo de resultados.

        Returns:
            Lista de productos relevantes (puede ser vacía).
        """
        ...

    @abstractmethod
    def get_stock(self, product_id: str) -> dict | None:
        """
        Retorna el stock disponible de un producto.
        Stock disponible = stock_qty - reserved_qty.

        Returns:
            Dict con product_id, available, restocking_date (si aplica). O None.
        """
        ...

    @abstractmethod
    def get_active_promotions(self) -> list[dict]:
        """
        Retorna todas las promociones activas.

        Returns:
            Lista de promociones activas. Nunca None.
        """
        ...
