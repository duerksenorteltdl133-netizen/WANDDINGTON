#!/usr/bin/env python3
"""
Query Enrichr API for GO enrichment of a gene list.
Uses only stdlib (urllib) — no external dependencies needed.

Usage:
  go_enrichment.py <gene1,gene2,...> [database]
  go_enrichment.py --ping               # connectivity check
"""
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

ENRICHR_BASE = "https://maayanlab.cloud/Enrichr"
DEFAULT_DB = "GO_Biological_Process_2023"
TIMEOUT = 12  # seconds


def ping() -> bool:
    try:
        urllib.request.urlopen(f"{ENRICHR_BASE}/datasetStatistics", timeout=5)
        return True
    except Exception:
        return False


def _multipart_body(fields: dict) -> tuple:
    """Build a minimal multipart/form-data body. Returns (bytes, boundary)."""
    boundary = "----WaddingtonBoundary7MA4YWxkTrZu0gW"
    lines = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        lines.append(b"")
        lines.append(value.encode("utf-8") if isinstance(value, str) else value)
    lines.append(f"--{boundary}--".encode())
    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def enrich_genes(genes: list, database: str = DEFAULT_DB) -> list:
    # Step 1: upload gene list (Enrichr requires multipart/form-data)
    body, ctype = _multipart_body({
        "list": "\n".join(genes),
        "description": "waddington_bio_validity",
    })
    req = urllib.request.Request(
        f"{ENRICHR_BASE}/addList",
        data=body,
        headers={"Content-Type": ctype},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        list_id = json.loads(resp.read())["userListId"]

    # Step 2: fetch enrichment results
    url = f"{ENRICHR_BASE}/enrich?userListId={list_id}&backgroundType={urllib.parse.quote(database)}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read())

    # Enrichr returns {database: [[rank, term, pval, zscore, combined, genes, ...], ...]}
    raw = data.get(database, [])
    results = []
    for r in raw[:20]:
        results.append({
            "rank": r[0],
            "term": r[1],
            "pval": r[2],
            "z_score": r[3],
            "combined_score": r[4],
            "genes": r[5] if len(r) > 5 else [],
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: go_enrichment.py <gene1,gene2,...> [database]"}))
        sys.exit(1)

    if sys.argv[1] == "--ping":
        print(json.dumps({"ok": ping()}))
        sys.exit(0)

    genes = [g.strip().upper() for g in sys.argv[1].split(",") if g.strip()]
    database = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB

    if not genes:
        print(json.dumps({"error": "No genes provided"}))
        sys.exit(1)

    try:
        results = enrich_genes(genes, database)
        print(json.dumps({"results": results, "gene_count": len(genes), "database": database}))
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"Network error: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
