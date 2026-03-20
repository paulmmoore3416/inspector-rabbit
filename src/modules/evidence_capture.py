"""
Inspector Rabbit - Evidence Capture Module
Captures web page evidence with cryptographic hashing and metadata preservation.
"""

import hashlib
import json
import os
import random
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal


USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

EVIDENCE_DIR = str(Path.home() / ".inspector_rabbit_evidence")


class EvidenceCaptureThread(QThread):
    captured = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url: str, save_dir: str = ""):
        super().__init__()
        self.url = url
        self.save_dir = save_dir if save_dir else EVIDENCE_DIR

    def run(self):
        try:
            self._capture()
        except Exception as exc:
            self.error.emit(f"Evidence capture failed: {exc}")

    def _capture(self):
        url = self.url
        self.progress.emit(f"Starting capture of: {url}")

        # Parse domain for case_id
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            domain = domain.replace(":", "_").replace(".", "_")
        except Exception:
            domain = "unknown"

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        case_id = f"{timestamp}_{domain}"
        case_dir = os.path.join(self.save_dir, case_id)

        self.progress.emit(f"Creating evidence directory: {case_dir}")
        os.makedirs(case_dir, exist_ok=True)

        # Fetch the URL
        self.progress.emit("Fetching page content...")
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=True,
            verify=False,
        )
        raw_bytes = response.content

        self.progress.emit(f"Received {len(raw_bytes):,} bytes  (HTTP {response.status_code})")

        # Save raw HTML
        html_path = os.path.join(case_dir, "page.html")
        with open(html_path, "wb") as fh:
            fh.write(raw_bytes)
        self.progress.emit(f"Saved raw HTML: {html_path}")

        # Compute hashes
        self.progress.emit("Computing cryptographic hashes...")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        md5 = hashlib.md5(raw_bytes).hexdigest()

        # Extract <title>
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
        except Exception:
            title = ""
        self.progress.emit(f"Page title: {title or '(none)'}")

        # Build headers dict (convert to plain strings)
        headers_dict = dict(response.headers)
        content_type = headers_dict.get("Content-Type", "")

        # Save headers
        headers_path = os.path.join(case_dir, "headers.json")
        with open(headers_path, "w", encoding="utf-8") as fh:
            json.dump(headers_dict, fh, indent=2, default=str)
        self.progress.emit(f"Saved HTTP headers: {headers_path}")

        # Build metadata
        metadata = {
            "url": url,
            "final_url": response.url,
            "timestamp": timestamp,
            "sha256": sha256,
            "md5": md5,
            "status_code": response.status_code,
            "content_type": content_type,
            "size_bytes": len(raw_bytes),
            "title": title,
            "case_id": case_id,
            "save_path": case_dir,
            "screenshot_path": "",
            "html_path": html_path,
            "headers_path": headers_path,
        }

        # Save metadata
        metadata_path = os.path.join(case_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, default=str)
        self.progress.emit(f"Saved metadata: {metadata_path}")

        # Build full result dict (includes headers for the GUI)
        result = dict(metadata)
        result["headers"] = headers_dict

        self.progress.emit("Evidence capture complete.")
        self.captured.emit(result)


def list_evidence(evidence_dir: str = "") -> list:
    """Scan evidence directory and return list of metadata.json contents."""
    base = evidence_dir if evidence_dir else EVIDENCE_DIR
    results = []
    if not os.path.isdir(base):
        return results
    for case_dir in sorted(os.listdir(base), reverse=True):
        meta_path = os.path.join(base, case_dir, "metadata.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    results.append(data)
            except Exception:
                pass
    return results
