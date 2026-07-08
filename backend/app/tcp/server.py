from __future__ import annotations

import asyncio
import json
from contextlib import suppress

from app.core.config import settings
from app.db.schema import ensure_database_schema
from app.db.session import SessionLocal
from app.services.hj212 import build_data_ack, parse_message
from app.services.protocol_logs import create_protocol_log
from app.services.telemetry_ingestion import ingest_payload, normalize_hj212_message


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    address = writer.get_extra_info("peername")
    while not reader.at_eof():
        raw_line = await reader.readline()
        if not raw_line:
            break

        raw_text = raw_line.decode("utf-8", errors="ignore")
        db = SessionLocal()
        try:
            if raw_text.strip().startswith("##"):
                message = None
                try:
                    message = parse_message(raw_text)
                    normalized = normalize_hj212_message(message)
                    ingest_payload(db, normalized.model_dump(mode="json"))
                    ack_packet = build_data_ack(message)
                    create_protocol_log(
                        db,
                        source="tcp",
                        raw_packet=raw_text,
                        status="accepted",
                        message=message,
                        metric_count=len(message.metrics),
                        ack_packet=ack_packet,
                    )
                    writer.write(ack_packet.encode("ascii"))
                except ValueError as exc:
                    db.rollback()
                    create_protocol_log(
                        db,
                        source="tcp",
                        raw_packet=raw_text,
                        status="rejected",
                        error_message=str(exc),
                    )
                    writer.write(f"ERROR: {exc}\n".encode("utf-8"))
                except Exception as exc:
                    db.rollback()
                    create_protocol_log(
                        db,
                        source="tcp",
                        raw_packet=raw_text,
                        status="ingest_failed",
                        message=message,
                        metric_count=len(message.metrics) if message else 0,
                        error_message=str(exc),
                    )
                    writer.write(f"ERROR: {exc}\n".encode("utf-8"))
            else:
                payload = json.loads(raw_text.strip())
                result = ingest_payload(db, payload)
                writer.write((json.dumps(result) + "\n").encode("utf-8"))
            await writer.drain()
        finally:
            db.close()

    writer.close()
    with suppress(Exception):
        await writer.wait_closed()
    if address:
        print(f"Disconnected: {address}")


async def run_server() -> None:
    ensure_database_schema()
    server = await asyncio.start_server(handle_client, settings.tcp_host, settings.tcp_port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(run_server())
