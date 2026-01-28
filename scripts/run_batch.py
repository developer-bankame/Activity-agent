#!/usr/bin/env python3
"""
Batch runner: lee scripts/activities.csv (columna: client_id) y llama al endpoint
POST {base_url}{endpoint} con body {"client_id": <id>, "trace_id": "..."}.

Escribe un CSV de salida con columnas: client_id, field, role
en scripts/outputs/results.csv (o el path que pases por --out).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


def post_json(url: str, payload: Dict, timeout: float) -> Tuple[int, str]:
    """POST JSON -> (status_code, response_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8", errors="replace")
            return status, body
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return e.code, body
    except URLError as e:
        return 0, f"URLError: {e}"
    except Exception as e:
        return 0, f"Exception: {e}"


def extract_field_role(resp_json: Dict) -> Tuple[str, str]:
    """
    Intenta extraer field/role de varias formas posibles.
    Esperado ideal:
      {"field": "...", "role": "..."}
    """
    field = resp_json.get("field")
    role = resp_json.get("role")

    # Si vienen anidados (por si luego cambias contrato)
    if isinstance(field, dict):
        field = field.get("label") or field.get("name") or field.get("value")
    if isinstance(role, dict):
        role = role.get("label") or role.get("name") or role.get("value")

    field = str(field).strip() if field else ""
    role = str(role).strip() if role else ""
    return field, role


def read_ids(csv_path: Path) -> list[int]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")

    ids: list[int] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "client_id" not in [h.strip() for h in reader.fieldnames]:
            raise ValueError("activities.csv debe tener header 'client_id' (una columna). Ej:\nclient_id\n2383\n4582\n")

        for row in reader:
            raw = (row.get("client_id") or "").strip()
            if not raw:
                continue
            try:
                ids.append(int(raw))
            except ValueError:
                # si viene algo raro, lo ignoramos pero avisamos
                print(f"[WARN] client_id inválido (no int): {raw}", file=sys.stderr)

    # quitar duplicados manteniendo orden
    seen = set()
    deduped = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            deduped.append(x)
    return deduped


def worker_call(base_url: str, endpoint: str, client_id: int, timeout: float) -> Tuple[int, str, str]:
    url = base_url.rstrip("/") + endpoint
    trace_id = f"batch-{client_id}"
    payload = {"client_id": client_id, "trace_id": trace_id}

    status, body = post_json(url, payload, timeout=timeout)
    if status != 200:
        # devolvemos vacío si falla, para cumplir formato id,field,role
        print(f"[ERROR] client_id={client_id} status={status} body={body[:300]}", file=sys.stderr)
        return client_id, "", ""

    try:
        resp_json = json.loads(body)
    except json.JSONDecodeError:
        print(f"[ERROR] client_id={client_id} respuesta no es JSON: {body[:300]}", file=sys.stderr)
        return client_id, "", ""

    field, role = extract_field_role(resp_json)
    return client_id, field, role


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8015", help="Ej: http://localhost:8015")
    parser.add_argument("--endpoint", default="/agent/scan", help="Ej: /agent/scan")
    parser.add_argument("--in", dest="in_path", default="scripts/activities.csv", help="CSV input con columna 'client_id'")
    parser.add_argument("--out", dest="out_path", default="", help="CSV output. Default: scripts/outputs/results_YYYYMMDD_HHMMSS.csv")
    parser.add_argument("--workers", type=int, default=8, help="Concurrencia (threads)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout por request (segundos)")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    ids = read_ids(in_path)
    if not ids:
        print("[INFO] No hay ids en el CSV.", file=sys.stderr)
        return 0

    outputs_dir = Path("scripts/outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)

    if args.out_path:
        out_path = Path(args.out_path)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = outputs_dir / f"results_{ts}.csv"

    base_url = args.base_url
    endpoint = args.endpoint

    print(f"[INFO] ids={len(ids)} base_url={base_url} endpoint={endpoint} workers={args.workers}", file=sys.stderr)
    t0 = time.time()

    results: list[Tuple[int, str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(worker_call, base_url, endpoint, cid, args.timeout) for cid in ids]
        for fut in as_completed(futures):
            results.append(fut.result())

    # ordenar por client_id original (mantener el orden del input)
    order = {cid: i for i, cid in enumerate(ids)}
    results.sort(key=lambda x: order.get(x[0], 10**12))

    # escribir CSV final con SOLO: client_id, field, role
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["client_id", "field", "role"])
        for cid, field, role in results:
            w.writerow([cid, field, role])

    dt = time.time() - t0
    print(f"[INFO] Output escrito en: {out_path} (secs={dt:.2f})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
