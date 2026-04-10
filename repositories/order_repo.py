"""
repositories/order_repo.py
===========================
Implementación CSV del repositorio de pedidos, items, envíos y tracking.

TODO (migración Bedrock): Reemplazar por DynamoDBOrderRepository que implemente
OrderRepositoryBase. El guard de customer_id en get_order_by_id es obligatorio
y debe mantenerse en la versión DynamoDB también.
"""

import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from repositories.base import OrderRepositoryBase
from core.config import DATA_DIR


class CSVOrderRepository(OrderRepositoryBase):
    """
    Repositorio de pedidos basado en archivos CSV.
    Carga todos los datasets de pedidos en memoria al inicializar.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self._data_dir = data_dir

        # Índices en memoria
        self._orders: dict[str, dict] = {}                    # order_id → order
        self._orders_by_customer: dict[str, list[str]] = defaultdict(list)  # customer_id → [order_ids]
        self._items_by_order: dict[str, list[dict]] = defaultdict(list)     # order_id → [items]
        self._shipment_by_order: dict[str, dict] = {}         # order_id → shipment
        self._tracking_by_order: dict[str, list[dict]] = defaultdict(list)  # order_id → [events]

        self._load()

    def _load(self) -> None:
        self._load_orders()
        self._load_order_items()
        self._load_shipments()
        self._load_tracking()

    def _load_csv(self, filename: str) -> list[dict]:
        """Helper: carga un CSV y retorna lista de dicts. Retorna [] si no existe."""
        path = self._data_dir / filename
        if not path.exists():
            print(f"[WARNING] {filename} no encontrado en {path}")
            return []
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load_orders(self) -> None:
        for row in self._load_csv("orders.csv"):
            oid = str(row["order_id"]).strip()
            cid = str(row["customer_id"]).strip()
            self._orders[oid] = row
            self._orders_by_customer[cid].append(oid)

    def _load_order_items(self) -> None:
        for row in self._load_csv("order_items.csv"):
            oid = str(row["order_id"]).strip()
            self._items_by_order[oid].append(row)

    def _load_shipments(self) -> None:
        for row in self._load_csv("shipments.csv"):
            oid = str(row["order_id"]).strip()
            self._shipment_by_order[oid] = row

    def _load_tracking(self) -> None:
        """Carga y ordena eventos de tracking por timestamp ascendente."""
        events = self._load_csv("tracking.csv")
        for row in events:
            oid = str(row["order_id"]).strip()
            self._tracking_by_order[oid].append(row)

        # Ordenar por timestamp si el campo existe
        for oid in self._tracking_by_order:
            try:
                self._tracking_by_order[oid].sort(
                    key=lambda r: r.get("timestamp", r.get("event_timestamp", ""))
                )
            except Exception:
                pass  # Si no se puede ordenar, dejarlo como está

    # ------------------------------------------------------------------
    # Implementación del contrato
    # ------------------------------------------------------------------

    def get_orders_by_customer(self, customer_id: str) -> list[dict]:
        """Retorna todos los pedidos del cliente. Lista vacía si no tiene pedidos."""
        order_ids = self._orders_by_customer.get(str(customer_id).strip(), [])
        return [dict(self._orders[oid]) for oid in order_ids if oid in self._orders]

    def get_order_by_id(self, order_id: str, customer_id: str) -> dict | None:
        """
        Retorna un pedido SOLO si pertenece al customer_id dado.
        Guard de seguridad: evita que un cliente vea pedidos de otro.
        """
        order = self._orders.get(str(order_id).strip())
        if order is None:
            return None
        if str(order.get("customer_id", "")).strip() != str(customer_id).strip():
            return None  # El pedido existe pero no pertenece a este cliente
        return dict(order)

    def get_items_by_order(self, order_id: str) -> list[dict]:
        return [dict(i) for i in self._items_by_order.get(str(order_id).strip(), [])]

    def get_shipment_by_order(self, order_id: str) -> dict | None:
        s = self._shipment_by_order.get(str(order_id).strip())
        return dict(s) if s else None

    def get_tracking_by_order(self, order_id: str) -> list[dict]:
        return [dict(e) for e in self._tracking_by_order.get(str(order_id).strip(), [])]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_order_repo() -> CSVOrderRepository:
    return CSVOrderRepository()
