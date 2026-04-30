"""Download the latest World Bank Remittance Prices Worldwide xlsx.

Source: https://remittanceprices.worldbank.org/data-download
Direct file URL discovered by inspecting the page network calls on
**2026-04-30** — the catalog only exposes a single canonical file at a time
even though the report covers multiple quarters. Both the World Bank Data
Catalog CDN and the remittanceprices.worldbank.org `sites/default/files`
mirror serve the same blob; primary URL is the catalog CDN since it ships
ETag/Last-Modified headers we can use for caching.

Run as a module:
    uv run python -m pipeline.ingest
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline.config import (
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


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Download the latest RPW xlsx.")
    p.add_argument("--force", action="store_true", help="re-download even if file exists")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    download_rpw(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
