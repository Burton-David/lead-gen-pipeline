#!/usr/bin/env python3
"""Benchmark bulk lead-insertion throughput against a temporary SQLite database.

Usage:
    python scripts/benchmark_bulk_db.py [num_records]

Inserts synthetic, deduplicated business records through the same
:class:`~lead_gen_pipeline.bulk_database.BulkDatabaseProcessor` the pipeline uses and
reports records/second. Reproducible on any machine; no model or network required.
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from lead_gen_pipeline import database
from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
from lead_gen_pipeline.config import settings


async def run(num_records: int) -> None:
    db_path = Path(tempfile.mkdtemp(prefix="leadgen-bench-")) / "bench.db"
    settings.database.DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
    database._reset_db_state_for_testing()
    await database.init_db()

    businesses = [
        {
            "name": f"Business {i}",
            "website": f"https://business-{i}.example",
            "phone": f"+1303556{i % 10000:04d}",
            "email": f"contact{i}@business-{i}.example",
            "industry": "Professional Services",
            "source_url": "https://chamber.example/members",
        }
        for i in range(num_records)
    ]
    chamber_info = {"name": "Benchmark Chamber", "website": "https://chamber.example"}

    processor = BulkDatabaseProcessor(batch_size=500)
    start = time.perf_counter()
    stats = await processor.bulk_insert_businesses(businesses, chamber_info)
    elapsed = time.perf_counter() - start

    rate = stats.successful_inserts / elapsed if elapsed else 0.0
    print(f"Records attempted : {stats.total_attempted:,}")
    print(f"Inserted          : {stats.successful_inserts:,}")
    print(f"Elapsed           : {elapsed:.2f}s")
    print(f"Throughput        : {rate:,.0f} records/sec")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    asyncio.run(run(count))
