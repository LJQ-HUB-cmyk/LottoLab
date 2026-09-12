import argparse
import json

from alembic import command
from alembic.config import Config

from .config import get_settings
from .db import make_engine, make_session_factory
from .ingestion import canonical, ingest_records, synthetic_records


def main():
    parser = argparse.ArgumentParser(description="LottoLab local tools")
    parser.add_argument("action", choices=["migrate", "sync", "demo", "serve", "worker"])
    parser.add_argument("--lottery", choices=["ssq", "dlt"], default="ssq")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.action == "migrate":
        command.upgrade(Config("alembic.ini"), "head")
        return
    if args.action == "serve":
        import uvicorn

        uvicorn.run(
            "lottolab.app:create_app", factory=True, host="127.0.0.1", port=args.port, proxy_headers=False
        )
        return
    if args.action == "worker":
        from .worker import run_worker

        run_worker()
        return
    if not 30 <= args.count <= 3000:
        parser.error("--count must be between 30 and 3000")
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    try:
        if args.action == "demo":
            records = synthetic_records(args.lottery, args.count, args.seed)
            with factory() as db:
                result = ingest_records(
                    db,
                    records,
                    lottery=args.lottery,
                    dataset_kind="synthetic",
                    source="均匀随机演示数据",
                    source_url=f"synthetic://seed/{args.seed}",
                    raw=canonical(records),
                    data_dir=settings.data_dir,
                    store_in_database=settings.snapshot_storage == "database",
                )
            print(json.dumps(result, ensure_ascii=False))
        else:
            from .sources import fetch_source

            batches, warnings = fetch_source(args.lottery, args.count, settings.source_timeout_seconds)
            results = []
            for batch in batches:
                with factory() as db:
                    results.append(
                        ingest_records(
                            db,
                            batch.records,
                            lottery=args.lottery,
                            dataset_kind="real",
                            source=batch.source,
                            source_url=batch.url,
                            raw=batch.raw,
                            data_dir=settings.data_dir,
                            store_in_database=settings.snapshot_storage == "database",
                        )
                    )
            print(json.dumps({"runs": results, "warnings": warnings}, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
