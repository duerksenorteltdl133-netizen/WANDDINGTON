#!/usr/bin/env python3
"""
Query STRING-DB API for protein-protein interaction (PPI) network enrichment.
Uses stdlib only (urllib).

Usage:
  string_network.py <gene1,gene2,...> [species_id]
  string_network.py --ping
"""
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

STRING_BASE = "https://string-db.org/api/json"
DEFAULT_SPECIES = 9606  # Homo sapiens
TIMEOUT = 15


def ping() -> bool:
    try:
        urllib.request.urlopen(f"{STRING_BASE}/version", timeout=5)
        return True
    except Exception:
        return False


def ppi_enrichment(genes: list, species: int = DEFAULT_SPECIES) -> dict:
    """Query STRING PPI network enrichment for a gene list."""
    body = urllib.parse.urlencode({
        "identifiers": "\r\n".join(genes),
        "species": species,
        "caller_identity": "waddington_bio_validity",
    }).encode()
    req = urllib.request.Request(
        f"{STRING_BASE}/ppi_enrichment",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read())
    if not data:
        return {"number_of_nodes": 0, "p_value": 1.0, "number_of_edges": 0,
                "expected_number_of_edges": 0}
    return data[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: string_network.py <gene1,gene2,...> [species]"}))
        sys.exit(1)

    if sys.argv[1] == "--ping":
        print(json.dumps({"ok": ping()}))
        sys.exit(0)

    genes = [g.strip().upper() for g in sys.argv[1].split(",") if g.strip()]
    species = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SPECIES

    if not genes:
        print(json.dumps({"error": "No genes provided"}))
        sys.exit(1)

    try:
        result = ppi_enrichment(genes, species)
        print(json.dumps({"result": result, "gene_count": len(genes)}))
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"Network error: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
