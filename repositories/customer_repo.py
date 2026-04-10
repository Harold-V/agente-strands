"""
repositories/customer_repo.py
==============================
Implementación CSV del repositorio de clientes.
Lee customers.csv al inicializar y mantiene los datos en memoria.

TODO (migración Bedrock): Reemplazar esta clase por DynamoDBCustomerRepository
que implemente el mismo CustomerRepositoryBase. Las tools/ no cambian.
"""

import csv
from functools import lru_cache
from pathlib import Path

from repositories.base import CustomerRepositoryBase
from core.config import DATA_DIR


class CSVCustomerRepository(CustomerRepositoryBase):
    """
    Repositorio de clientes basado en archivos CSV locales.
    Carga los datos una sola vez en memoria para minimizar latencia (TTFT).
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self._data_dir = data_dir
        self._customers: dict[str, dict] = {}   # customer_id → row
        self._by_dni: dict[str, str] = {}        # dni → customer_id
        self._by_phone: dict[str, str] = {}      # phone → customer_id
        self._load()

    def _load(self) -> None:
        customers_path = self._data_dir / "customers.csv"
        if not customers_path.exists():
            print(f"[WARNING] customers.csv no encontrado en {customers_path}")
            return

        with open(customers_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = str(row["customer_id"]).strip()
                self._customers[cid] = row

                dni = str(row.get("dni", "")).strip()
                if dni:
                    self._by_dni[dni] = cid

                phone = str(row.get("phone", "")).strip()
                if phone:
                    self._by_phone[phone] = cid

    def find_by_dni(self, dni: str) -> dict | None:
        """Match exacto. No normaliza. El reto especifica validación exacta."""
        cid = self._by_dni.get(str(dni).strip())
        if cid is None:
            return None
        return dict(self._customers[cid])

    def find_by_phone(self, phone: str) -> dict | None:
        """Match exacto."""
        cid = self._by_phone.get(str(phone).strip())
        if cid is None:
            return None
        return dict(self._customers[cid])

    def find_by_id(self, customer_id: str) -> dict | None:
        row = self._customers.get(str(customer_id).strip())
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Singleton del repositorio — una sola carga al arrancar
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_customer_repo() -> CSVCustomerRepository:
    """
    Retorna la instancia singleton del repositorio de clientes.
    lru_cache garantiza una sola carga de CSV en todo el proceso.
    """
    return CSVCustomerRepository()
