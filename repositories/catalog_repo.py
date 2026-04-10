"""
repositories/catalog_repo.py
=============================
Implementación CSV del repositorio de catálogo de productos.
No requiere autenticación — datos públicos.

TODO (migración Bedrock): Reemplazar por DynamoDBCatalogRepository.
"""

import csv
from functools import lru_cache
from pathlib import Path

from repositories.base import CatalogRepositoryBase
from core.config import DATA_DIR


class CSVCatalogRepository(CatalogRepositoryBase):
    """
    Repositorio de catálogo basado en archivos CSV.
    Carga products, stock, categories, brands, promotions en memoria.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self._data_dir = data_dir
        self._products: dict[str, dict] = {}       # product_id → product
        self._stock: dict[str, dict] = {}          # product_id → stock
        self._categories: dict[str, dict] = {}     # category_id → category
        self._brands: dict[str, dict] = {}         # brand_id → brand
        self._promotions: list[dict] = []
        self._load()

    def _load_csv(self, filename: str) -> list[dict]:
        path = self._data_dir / filename
        if not path.exists():
            print(f"[WARNING] {filename} no encontrado en {path}")
            return []
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load(self) -> None:
        for row in self._load_csv("products.csv"):
            pid = str(row.get("product_id", "")).strip()
            if pid:
                self._products[pid] = row

        for row in self._load_csv("stock.csv"):
            pid = str(row.get("product_id", "")).strip()
            if pid:
                self._stock[pid] = row

        for row in self._load_csv("categories.csv"):
            cid = str(row.get("category_id", "")).strip()
            if cid:
                self._categories[cid] = row

        for row in self._load_csv("brands.csv"):
            bid = str(row.get("brand_id", "")).strip()
            if bid:
                self._brands[bid] = row

        self._promotions = self._load_csv("promotions.csv")

    # ------------------------------------------------------------------
    # Implementación del contrato
    # ------------------------------------------------------------------

    def get_product_by_id(self, product_id: str) -> dict | None:
        p = self._products.get(str(product_id).strip())
        return dict(p) if p else None

    def search_products(self, query: str, limit: int = 5) -> list[dict]:
        """
        Búsqueda simple por nombre, marca o categoría.
        Case-insensitive, coincidencia parcial.
        """
        q = query.lower().strip()
        results = []
        for product in self._products.values():
            status = str(product.get("status", "active")).lower()
            if status != "active":
                continue
            searchable = " ".join([
                str(product.get("product_name", "")),
                str(product.get("brand_name", "")),
                str(product.get("category_name", "")),
                str(product.get("description", "")),
            ]).lower()
            if q in searchable:
                results.append(dict(product))
            if len(results) >= limit:
                break
        return results

    def get_stock(self, product_id: str) -> dict | None:
        """
        Retorna stock disponible = stock_qty - reserved_qty.
        """
        s = self._stock.get(str(product_id).strip())
        if s is None:
            return None
        try:
            total = int(s.get("stock_qty", 0))
            reserved = int(s.get("reserved_qty", 0))
            available = max(0, total - reserved)
        except (ValueError, TypeError):
            available = 0
            total = 0
            reserved = 0

        return {
            "product_id": product_id,
            "available": available,
            "stock_qty": total,
            "reserved_qty": reserved,
            "restocking_date": s.get("restocking_date", None),
        }

    def get_active_promotions(self) -> list[dict]:
        """Retorna promociones activas."""
        active = []
        for promo in self._promotions:
            status = str(promo.get("status", "active")).lower()
            if status == "active":
                active.append(dict(promo))
        return active


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_catalog_repo() -> CSVCatalogRepository:
    return CSVCatalogRepository()
