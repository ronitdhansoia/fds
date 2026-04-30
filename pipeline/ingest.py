"""Download the latest source data: RPW xlsx + bilateral remittance matrix.

RPW (Remittance Prices Worldwide):
    https://remittanceprices.worldbank.org/data-download
    Direct file URL discovered by inspecting the page network calls on
    **2026-04-30**. Both the World Bank Data Catalog CDN and the
    remittanceprices.worldbank.org/sites/default/files mirror serve the
    same blob; primary URL is the catalog CDN since it ships
    ETag/Last-Modified headers we can use for caching.

Bilateral Remittance Matrix (KNOMAD WB_KNOMAD_BRE):
    The legacy direct-download xlsx at
    knomad.org/sites/default/files/2022-12/bilateral_remittance_matrix_2021_0.xlsx
    was retired in early 2025 and now 302-redirects to a landing page.
    The Data360 API at data360api.worldbank.org/data360/data is the
    canonical replacement. We page through it (1000 records per page,
    ~11 pages for the full ~10.6k bilateral pairs) and persist the
    flattened JSON to data/raw/bilateral_remittances_2021.json.

Run as a module:
    uv run python -m pipeline.ingest                # both
    uv run python -m pipeline.ingest --only rpw     # RPW only
    uv run python -m pipeline.ingest --only brm     # BRM only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline.config import (
    BRM_API_URL,
    BRM_LATEST_YEAR,
    RAW_BRM_PATH,
    RAW_RPW_PATH,
    RPW_FALLBACK_URL,
    RPW_PRIMARY_URL,
    ensure_dirs,
)

logger = logging.getLogger(__name__)

CHUNK_BYTES = 1 << 16  # 64 KiB
HTTP_TIMEOUT_S = (15, 300)  # connect, read
USER_AGENT = "MigrantMoney/0.1 (BITS Pilani FDS project; +https://example.invalid)"


def _stream_download(url: str, dest: Path) -> tuple[int, str]:
    """Stream a URL to disk. Returns (bytes_written, sha256)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    sha = hashlib.sha256()
    bytes_written = 0
    tmp = dest.with_suffix(dest.suffix + ".part")

    with requests.get(url, headers=headers, stream=True, timeout=HTTP_TIMEOUT_S) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        last_modified = r.headers.get("Last-Modified", "<unknown>")
        logger.info(
            "downloading %s (%s bytes, last-modified %s)",
            url,
            f"{total:,}" if total else "unknown",
            last_modified,
        )
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                fh.write(chunk)
                sha.update(chunk)
                bytes_written += len(chunk)
    tmp.replace(dest)
    return bytes_written, sha.hexdigest()


def download_rpw(dest: Path = RAW_RPW_PATH, force: bool = False) -> Path:
    """Fetch the RPW xlsx, falling back to the secondary mirror on failure."""
    ensure_dirs()
    if dest.exists() and not force:
        size_mb = dest.stat().st_size / 1_048_576
        logger.info("RPW xlsx already present at %s (%.1f MB) — skipping", dest, size_mb)
        return dest

    last_err: Exception | None = None
    for url in (RPW_PRIMARY_URL, RPW_FALLBACK_URL):
        try:
            n_bytes, digest = _stream_download(url, dest)
        except Exception as exc:  # noqa: BLE001 — try fallback URL
            logger.warning("download failed from %s: %s", url, exc)
            last_err = exc
            continue
        retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        logger.info(
            "wrote %s (%.1f MB), sha256=%s, retrieved=%s",
            dest,
            n_bytes / 1_048_576,
            digest[:16] + "…",
            retrieved_at,
        )
        return dest
    raise RuntimeError(f"all RPW download URLs failed: last error={last_err!r}")


def download_bilateral_remittances(
    dest: Path = RAW_BRM_PATH,
    force: bool = False,
    page_size: int = 1000,
) -> Path:
    """Page through the Data360 BRE indicator and dump the records to JSON.

    The API caps each response at 1000 rows; a `nextLink` is not returned,
    so we paginate via `$skip` until total records have been seen.
    """
    ensure_dirs()
    if dest.exists() and not force:
        size_kb = dest.stat().st_size / 1024
        logger.info("BRM JSON already present at %s (%.0f KB) — skipping", dest, size_kb)
        return dest

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    records: list[dict] = []
    skip = 0
    total: int | None = None

    while True:
        url = f"{BRM_API_URL}&top={page_size}&skip={skip}"
        logger.info("BRM page request: skip=%d", skip)
        r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_S)
        r.raise_for_status()
        payload = r.json()
        if total is None:
            total = int(payload.get("count", 0))
            logger.info("BRM total records: %d", total)
        page = payload.get("value", [])
        if not page:
            break
        records.extend(page)
        skip += len(page)
        if total is not None and skip >= total:
            break
        if len(page) < page_size:
            break

    if total and len(records) != total:
        logger.warning("BRM record count mismatch: expected %d got %d", total, len(records))

    out = {
        "indicator": "WB_KNOMAD_BRE",
        "source": "data360api.worldbank.org",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_year": BRM_LATEST_YEAR,
        "n_records": len(records),
        "records": records,
    }
    tmp = dest.with_suffix(dest.suffix + ".part")
    with tmp.open("w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    tmp.replace(dest)
    logger.info("wrote %s (%.0f KB, %d records)", dest, dest.stat().st_size / 1024, len(records))
    return dest


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Download RPW xlsx + bilateral remittance matrix.")
    p.add_argument(
        "--only",
        choices=["rpw", "brm", "both"],
        default="both",
        help="Which dataset to fetch (default: both).",
    )
    p.add_argument("--force", action="store_true", help="re-download even if file exists")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if args.only in ("rpw", "both"):
        download_rpw(force=args.force)
    if args.only in ("brm", "both"):
        download_bilateral_remittances(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
