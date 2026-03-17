#!/usr/bin/env python3
"""Bulk-import inventory from a CSV file.

CSV format:
    name,name_hindi,aliases,category,unit,selling_price,stock_quantity,shelf_location,location_notes

Usage:
    python scripts/seed_inventory.py inventory.csv
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def seed(csv_path: str) -> None:
    from munshi.db.database import get_session, init_db
    from munshi.modules.inventory.schemas import ProductInput
    from munshi.modules.inventory.service import InventoryService

    await init_db()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Importing {len(rows)} products...")
    success = 0

    async with get_session() as db:
        svc = InventoryService(db, shop_id=1)
        for row in rows:
            try:
                aliases = json.loads(row.get("aliases", "[]")) if row.get("aliases") else []
                product = ProductInput(
                    name=row["name"],
                    name_hindi=row.get("name_hindi") or None,
                    aliases=aliases,
                    category=row.get("category") or None,
                    unit=row.get("unit", "piece") or "piece",
                    selling_price=float(row["selling_price"]) if row.get("selling_price") else None,
                    initial_stock=float(row.get("stock_quantity", 0) or 0),
                    shelf_location=row.get("shelf_location") or None,
                    location_notes=row.get("location_notes") or None,
                )
                await svc.add_product(product)
                success += 1
            except Exception as e:
                print(f"  ✗ Failed to import '{row.get('name', '?')}': {e}")

    print(f"✓ Imported {success}/{len(rows)} products.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_inventory.py <csv_file>")
        sys.exit(1)
    asyncio.run(seed(sys.argv[1]))
