import io
import re
import os
import socket
import ssl
import time
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse
import ipaddress

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context
from dotenv import load_dotenv

load_dotenv()

MINERU_API_KEY = os.getenv("MINERU_API_KEY", "")
MINERU_BASE_URL = os.getenv("MINERU_BASE_URL", "https://mineru.net")

# 禁用 SSL 警告（VPN 环境下需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SSLAdapter(HTTPAdapter):
    """Custom SSL adapter to handle VPN/proxy SSL issues."""
    
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # 尝试允许旧版 SSL 连接（Python 3.12+ 才有 OP_LEGACY_SERVER_CONNECT）
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_session_with_retries(retries: int = 3, backoff_factor: float = 0.5, skip_ssl_verify: bool = False) -> requests.Session:
    """Create a requests session with retry and timeout settings."""
    session = requests.Session()
    
    # 禁用环境变量代理（避免梯子干扰）
    session.trust_env = False
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT"],
    )
    
    if skip_ssl_verify:
        # Use custom SSL adapter for VPN environments
        adapter = SSLAdapter(max_retries=retry_strategy)
        session.verify = False
    else:
        adapter = HTTPAdapter(max_retries=retry_strategy)
    
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class MinerUParser:
    """
    MinerU PDF parser with full API workflow:
    1. Request presigned upload URL
    2. Upload PDF file
    3. Poll for parsing completion
    4. Download and extract Markdown
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, skip_ssl_verify: bool = True):
        self.api_key = api_key or MINERU_API_KEY
        self.base_url = base_url or MINERU_BASE_URL
        self.skip_ssl_verify = skip_ssl_verify
        if not self.api_key:
            raise ValueError("MINERU_API_KEY is required. Set it in .env file.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.session = create_session_with_retries(retries=3, backoff_factor=1.0, skip_ssl_verify=skip_ssl_verify)

    def parse_pdf(
        self,
        pdf_path: Path,
        model_version: str = "vlm",
        max_wait: int = 600,
        poll_interval: int = 3,
    ) -> Optional[str]:
        """
        Parse PDF file to Markdown using MinerU API.
        
        Args:
            pdf_path: Path to local PDF file
            model_version: Model version ("vlm" for visual language model)
            max_wait: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Markdown text if successful, None otherwise
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        parse_start_time = time.time()

        # Step 1: Request presigned upload URL
        print(f"[MinerU] Requesting upload URL for {pdf_file.name}...")
        response = self.session.post(
            f"{self.base_url}/api/v4/file-urls/batch",
            headers=self.headers,
            json={
                "files": [{"name": pdf_file.name, "data_id": pdf_file.name}],
                "model_version": model_version,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()["data"]
        batch_id = data["batch_id"]
        upload_url = data["file_urls"][0]
        print(f"[MinerU]   Batch ID: {batch_id}")

        # Step 2: Upload PDF file
        print(f"[MinerU] Uploading PDF...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
            upload_response = self.session.put(upload_url, data=file_content, timeout=120)
            upload_response.raise_for_status()
        upload_time = time.time() - parse_start_time
        print(f"[MinerU]   Uploaded {len(file_content)/1024:.1f} KB in {upload_time:.1f}s")

        # Step 3: Poll for parsing completion
        print(f"[MinerU] Waiting for parsing...")
        elapsed = 0
        full_zip_url = None

        while elapsed < max_wait:
            status_response = self.session.get(
                f"{self.base_url}/api/v4/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            result = status_response.json()["data"]["extract_result"][0]
            state = result["state"]

            if state == "done":
                full_zip_url = result["full_zip_url"]
                print(f"[MinerU]   Parsing complete ({elapsed}s)")
                break
            elif state == "failed":
                error_msg = result.get("err_msg", "Unknown error")
                print(f"[MinerU]   Parsing failed: {error_msg}")
                return None
            elif state == "running":
                progress = result.get("extract_progress", {})
                extracted = progress.get("extracted_pages", 0)
                total = progress.get("total_pages", "?")
                print(f"[MinerU]   Progress: {extracted}/{total} pages ({elapsed}s)", end="\r")

            time.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= max_wait:
            print(f"\n[MinerU]   Timeout ({max_wait}s)")
            return None

        # Step 4: Download and extract Markdown
        if not full_zip_url:
            return None

        def _candidate_download_urls(url: str) -> list[str]:
            candidates = [url]
            try:
                parsed = urlparse(url)
                base = urlparse(self.base_url)
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    # If MinerU returns a CDN URL, also try the origin host (same path).
                    # This helps when the CDN domain is blocked/mitm-ed by VPN.
                    if "cdn" in parsed.netloc and base.netloc and base.netloc != parsed.netloc:
                        candidates.append(
                            urlunparse(parsed._replace(netloc=base.netloc))
                        )
            except Exception:
                pass
            # Dedup while preserving order
            deduped: list[str] = []
            for c in candidates:
                if c not in deduped:
                    deduped.append(c)
            return deduped

        def _resolve_public_ips_for_host(host: str) -> list[str]:
            """Return public-looking IPv4s for a host.

            If local DNS is hijacked (e.g. Clash fake-ip -> 198.18.0.0/15),
            fall back to DoH (doh.pub) to get real A records.
            """

            def _is_bad_ipv4(ip: str) -> bool:
                try:
                    addr = ipaddress.ip_address(ip)
                    fake_ip_net = ipaddress.ip_network("198.18.0.0/15")
                    return (
                        addr.version != 4
                        or addr in fake_ip_net
                        or addr.is_private
                        or addr.is_loopback
                        or addr.is_link_local
                        or addr.is_reserved
                    )
                except Exception:
                    return True

            try:
                local_ip = socket.gethostbyname(host)
                if local_ip and not _is_bad_ipv4(local_ip):
                    return [local_ip]
            except Exception:
                pass

            # DoH fallback (Tencent public DoH; tends to be reachable in CN)
            try:
                doh_url = f"https://doh.pub/resolve?name={host}&type=A"
                doh_resp = self.session.get(doh_url, timeout=10, verify=False)
                doh_resp.raise_for_status()
                payload = doh_resp.json()
                answers = payload.get("Answer") or []
                ips: list[str] = []
                for ans in answers:
                    if ans.get("type") == 1 and isinstance(ans.get("data"), str):
                        ip = ans["data"].strip()
                        if ip and not _is_bad_ipv4(ip):
                            ips.append(ip)
                # Dedup
                deduped: list[str] = []
                for ip in ips:
                    if ip not in deduped:
                        deduped.append(ip)
                return deduped
            except Exception:
                return []

        download_urls = _candidate_download_urls(full_zip_url)

        print(f"\n[MinerU] Downloading result...")
        zip_content = None
        
        # 直接使用 curl 下载（绕过梯子干扰）
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = tmp.name
        
        try:
            print(f"[MinerU]   Using curl (bypass proxy)...")
            for candidate_url in download_urls:
                parsed_url = urlparse(candidate_url)
                host = parsed_url.hostname
                port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                resolved_ips = _resolve_public_ips_for_host(host) if host and port == 443 else []

                # curl: force direct (no proxy), be lenient on cert, and reduce TLS/HTTP quirks.
                curl_base = [
                    "curl",
                    "-k",
                    "-L",
                    "--noproxy",
                    "*",
                    "--http1.1",
                    "--retry",
                    "3",
                    "--retry-delay",
                    "2",
                    "--retry-all-errors",
                    "--connect-timeout",
                    "15",
                    "--max-time",
                    "120",
                    "-o",
                    tmp_path,
                ]

                attempt_urls: list[tuple[str, Optional[str]]] = []
                if host and resolved_ips:
                    # Prefer real IPs from DoH when local DNS is fake-ip.
                    for ip in resolved_ips:
                        attempt_urls.append((candidate_url, f"{host}:{port}:{ip}"))
                else:
                    attempt_urls.append((candidate_url, None))

                for url_to_fetch, resolve_entry in attempt_urls:
                    cmd = curl_base.copy()
                    if resolve_entry:
                        cmd.extend(["--resolve", resolve_entry])
                    cmd.append(url_to_fetch)
                    result = subprocess.run(cmd, capture_output=True, timeout=150)

                    if result.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        with open(tmp_path, "rb") as f:
                            zip_content = f.read()
                        print(f"[MinerU]   Downloaded: {len(zip_content)/1024:.1f} KB")
                        break

                    stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
                    hint = f" (url={candidate_url})" if candidate_url != full_zip_url else ""
                    if resolve_entry:
                        hint += f" (resolve={resolve_entry})"
                    print(f"[MinerU]   curl failed{hint}: {stderr.strip() or 'No error output'}")

                if zip_content is not None:
                    break
        except Exception as e:
            print(f"[MinerU]   curl exception: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        # Fallback: Try with requests if curl fails
        if zip_content is None:
            print(f"[MinerU]   Trying requests as fallback...")
            for candidate_url in download_urls:
                for attempt in range(3):
                    try:
                        zip_response = self.session.get(candidate_url, timeout=120, verify=False)
                        zip_response.raise_for_status()
                        zip_content = zip_response.content
                        print(f"[MinerU]   Downloaded via requests: {len(zip_content)/1024:.1f} KB")
                        break
                    except Exception as e:
                        hint = f" (url={candidate_url})" if candidate_url != full_zip_url else ""
                        print(f"[MinerU]   Requests error{hint} (attempt {attempt+1}/3): {e}")
                        if attempt < 2:
                            time.sleep(2)
                if zip_content is not None:
                    break
        
        if zip_content is None:
            raise RuntimeError(f"Failed to download ZIP from CDN. URL: {full_zip_url}")

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            md_files = [f for f in zf.namelist() if f.endswith(".md")]
            if not md_files:
                print(f"[MinerU]   No .md files found in ZIP")
                return None

            target_file = next((f for f in md_files if "full" in f.lower()), md_files[0])
            with zf.open(target_file) as f:
                markdown_text = f.read().decode("utf-8")

        total_time = time.time() - parse_start_time
        print(f"[MinerU]   Extracted {len(markdown_text):,} chars in {total_time:.1f}s total")

        return markdown_text
    # ----------------------------------------------------------------
    # New API: parse_pdf_to_pages => per-page MD + offsets + raw zip
    # ----------------------------------------------------------------
    def parse_pdf_to_pages(
        self,
        pdf_path: Path,
        model_version: str = "vlm",
        max_wait: int = 600,
        poll_interval: int = 3,
    ) -> tuple[list[str], list[int], bytes, str]:
        """Parse PDF and return per-page Markdown list.

        Returns:
            (pages, offsets, zip_bytes, full_markdown)
            - pages: list[str] where pages[i] is MD for page i+1
            - offsets: list[int] char start of each page in full_markdown
            - zip_bytes: raw ZIP for caching
            - full_markdown: concatenated '\\n'.join(pages)

        Raises:
            FileNotFoundError: PDF not found
            RuntimeError: If MinerU ZIP lacks per-page markdown files or download fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        parse_start_time = time.time()

        # --- Step 1: Request presigned upload URL ---
        print(f"[MinerU] Requesting upload URL for {pdf_file.name}...")
        response = self.session.post(
            f"{self.base_url}/api/v4/file-urls/batch",
            headers=self.headers,
            json={
                "files": [{"name": pdf_file.name, "data_id": pdf_file.name}],
                "model_version": model_version,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()["data"]
        batch_id = data["batch_id"]
        upload_url = data["file_urls"][0]
        print(f"[MinerU]   Batch ID: {batch_id}")

        # --- Step 2: Upload PDF ---
        print(f"[MinerU] Uploading PDF...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
            upload_response = self.session.put(upload_url, data=file_content, timeout=120)
            upload_response.raise_for_status()
        upload_time = time.time() - parse_start_time
        print(f"[MinerU]   Uploaded {len(file_content)/1024:.1f} KB in {upload_time:.1f}s")

        # --- Step 3: Poll for completion ---
        print(f"[MinerU] Waiting for parsing...")
        elapsed = 0
        full_zip_url = None

        while elapsed < max_wait:
            status_response = self.session.get(
                f"{self.base_url}/api/v4/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            result = status_response.json()["data"]["extract_result"][0]
            state = result["state"]

            if state == "done":
                full_zip_url = result["full_zip_url"]
                print(f"[MinerU]   Parsing complete ({elapsed}s)")
                break
            elif state == "failed":
                error_msg = result.get("err_msg", "Unknown error")
                raise RuntimeError(f"MinerU parsing failed: {error_msg}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        if not full_zip_url:
            raise RuntimeError(f"MinerU: Timeout waiting for parsing ({max_wait}s)")

        # --- Step 4: Download ZIP using existing helper logic ---
        zip_content = self._download_zip(full_zip_url)
        if zip_content is None:
            raise RuntimeError(f"Failed to download ZIP from CDN. URL: {full_zip_url}")

        # --- Step 5: Extract per-page markdown files ---
        # First, get PDF page count for intelligent splitting
        try:
            import pymupdf
            pdf_doc = pymupdf.open(pdf_path)
            pdf_page_count = len(pdf_doc)
            pdf_doc.close()
        except Exception as e:
            print(f"[MinerU]   Warning: Could not read PDF page count ({e}), using fallback")
            pdf_page_count = None

        pages, offsets, full_md = self._extract_pages_from_zip(zip_content, pdf_page_count)

        total_time = time.time() - parse_start_time
        print(f"[MinerU]   Extracted {len(pages)} pages, {len(full_md):,} chars in {total_time:.1f}s")

        return pages, offsets, zip_content, full_md

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------
    def _download_zip(self, full_zip_url: str) -> Optional[bytes]:
        """Download ZIP with curl first, requests fallback."""

        def _candidate_download_urls(url: str) -> list[str]:
            candidates = [url]
            try:
                parsed = urlparse(url)
                base = urlparse(self.base_url)
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    if "cdn" in parsed.netloc and base.netloc and base.netloc != parsed.netloc:
                        candidates.append(urlunparse(parsed._replace(netloc=base.netloc)))
            except Exception:
                pass
            return list(dict.fromkeys(candidates))

        def _resolve_ips(host: str) -> list[str]:
            """Resolve with DoH fallback for fake-ip scenarios."""

            def _bad(ip: str) -> bool:
                try:
                    addr = ipaddress.ip_address(ip)
                    fake = ipaddress.ip_network("198.18.0.0/15")
                    return addr.version != 4 or addr in fake or addr.is_private or addr.is_loopback
                except Exception:
                    return True

            try:
                local = socket.gethostbyname(host)
                if local and not _bad(local):
                    return [local]
            except Exception:
                pass
            try:
                resp = self.session.get(f"https://doh.pub/resolve?name={host}&type=A", timeout=10, verify=False)
                resp.raise_for_status()
                ips = [
                    a["data"] for a in (resp.json().get("Answer") or [])
                    if a.get("type") == 1 and not _bad(a.get("data", ""))
                ]
                return list(dict.fromkeys(ips))
            except Exception:
                return []

        download_urls = _candidate_download_urls(full_zip_url)
        print(f"\n[MinerU] Downloading result...")

        import subprocess
        import tempfile

        zip_content: Optional[bytes] = None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = tmp.name

        try:
            print(f"[MinerU]   Using curl (bypass proxy)...")
            for candidate_url in download_urls:
                parsed_url = urlparse(candidate_url)
                host = parsed_url.hostname
                port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                ips = _resolve_ips(host) if host and port == 443 else []

                curl_base = [
                    "curl", "-k", "-L", "--noproxy", "*", "--http1.1",
                    "--retry", "3", "--retry-delay", "2", "--retry-all-errors",
                    "--connect-timeout", "15", "--max-time", "120", "-o", tmp_path,
                ]

                attempts = [(candidate_url, f"{host}:{port}:{ip}") for ip in ips] if ips else [(candidate_url, None)]
                for url_to_fetch, resolve_entry in attempts:
                    cmd = curl_base.copy()
                    if resolve_entry:
                        cmd.extend(["--resolve", resolve_entry])
                    cmd.append(url_to_fetch)
                    result = subprocess.run(cmd, capture_output=True, timeout=150)
                    if result.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        with open(tmp_path, "rb") as f:
                            zip_content = f.read()
                        print(f"[MinerU]   Downloaded: {len(zip_content)/1024:.1f} KB")
                        break
                    stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
                    print(f"[MinerU]   curl failed: {stderr.strip() or 'No output'}")
                if zip_content:
                    break
        except Exception as e:
            print(f"[MinerU]   curl exception: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Fallback
        if zip_content is None:
            print(f"[MinerU]   Trying requests as fallback...")
            for candidate_url in download_urls:
                for attempt in range(3):
                    try:
                        r = self.session.get(candidate_url, timeout=120, verify=False)
                        r.raise_for_status()
                        zip_content = r.content
                        print(f"[MinerU]   Downloaded via requests: {len(zip_content)/1024:.1f} KB")
                        break
                    except Exception as e:
                        print(f"[MinerU]   Requests error (attempt {attempt+1}/3): {e}")
                        if attempt < 2:
                            time.sleep(2)
                if zip_content:
                    break

        return zip_content

    def _extract_pages_from_zip(
        self, zip_bytes: bytes, pdf_page_count: int = None
    ) -> tuple[list[str], list[int], str]:
        """Extract per-page markdown from MinerU ZIP.

        Expected file pattern inside ZIP: <name>/<page_0001>.md, <page_0002>.md, ...
        If per-page not found, falls back to splitting full.md by PDF page count or heuristics.

        Args:
            zip_bytes: raw ZIP content from MinerU
            pdf_page_count: original PDF page count (for intelligent splitting)
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            md_files = sorted([n for n in zf.namelist() if n.endswith(".md")])

            # Check for per-page pattern: filename contains page_XXXX or similar
            page_file_pattern = re.compile(r"page[_-]?(\d+)\.md$", re.IGNORECASE)
            per_page_files: dict[int, str] = {}

            for name in md_files:
                base = name.split("/")[-1]
                m = page_file_pattern.search(base)
                if m:
                    per_page_files[int(m.group(1))] = name

            if not per_page_files:
                # Try alternative: numbered files without explicit page_ prefix
                numbered_pattern = re.compile(r"(\d+)\.md$")
                for name in md_files:
                    base = name.split("/")[-1]
                    m = numbered_pattern.match(base)
                    if m:
                        per_page_files[int(m.group(1))] = name

            if per_page_files:
                # Build pages list ordered by page number
                pages: list[str] = []
                for pg in sorted(per_page_files.keys()):
                    with zf.open(per_page_files[pg]) as f:
                        page_content = f.read().decode("utf-8")
                        # Convert HTML tables to Markdown
                        page_content = self._convert_html_tables_to_markdown(page_content)
                        pages.append(page_content)

                # Build offsets and full_md
                offsets: list[int] = []
                parts: list[str] = []
                cur = 0
                for p in pages:
                    offsets.append(cur)
                    parts.append(p)
                    cur += len(p) + 1  # +1 for joining '\n'

                full_md = "\n".join(parts)
                return pages, offsets, full_md

            # Fallback: no per-page files; try extracting full md and split heuristically
            if not md_files:
                raise RuntimeError("[MinerU] ZIP 中没有任何 .md 文件")

            # Pick the full.md or largest md file
            target_file = next((f for f in md_files if "full" in f.lower()), md_files[0])
            with zf.open(target_file) as f:
                full_md = f.read().decode("utf-8")
            
            # Convert HTML tables to Markdown before splitting
            full_md = self._convert_html_tables_to_markdown(full_md)

            # Strategy 1: If we know PDF page count, split evenly by character count
            if pdf_page_count and pdf_page_count > 1:
                total_chars = len(full_md)
                chars_per_page = total_chars // pdf_page_count
                pages = []
                offsets = []
                for i in range(pdf_page_count):
                    start = i * chars_per_page
                    # Last page takes remainder
                    end = total_chars if i == pdf_page_count - 1 else (i + 1) * chars_per_page
                    pages.append(full_md[start:end])
                    offsets.append(start)
                return pages, offsets, full_md

            # Strategy 2: Try splitting on '# Page N' or '---' markers
            page_split_pattern = re.compile(r"(?m)^# Page \d+\s*$", re.IGNORECASE)
            matches = list(page_split_pattern.finditer(full_md))
            if matches:
                # split by Page markers
                splits = []
                offsets = []
                last_end = 0
                for m in matches:
                    if m.start() > last_end:
                        splits.append(full_md[last_end : m.start()].strip())
                        offsets.append(last_end)
                    last_end = m.end()
                    splits.append(full_md[m.start() : m.end()].strip() + "\n")
                    offsets.append(m.start())
                if last_end < len(full_md):
                    splits.append(full_md[last_end:].strip())
                    offsets.append(last_end)
                return splits, offsets, full_md

            # Last resort: treat entire full.md as single page
            return [full_md], [0], full_md

    def _convert_html_tables_to_markdown(self, text: str) -> str:
        """Convert HTML tables in text to Markdown format.
        
        Handles simple tables by converting to pipe-separated format.
        Complex tables with rowspan/colspan are flattened with notes.
        """
        print(f"[MinerU] Converting HTML tables (input: {len(text)} chars)...")
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table")
        
        if not tables:
            print(f"[MinerU]   No HTML tables found")
            return text
        
        print(f"[MinerU]   Found {len(tables)} HTML tables")
        result = text
        converted_count = 0
        
        for idx, table in enumerate(tables):
            try:
                # Extract all rows
                rows = table.find_all("tr")
                if not rows:
                    print(f"[MinerU]   Table {idx+1}: No rows, skipping")
                    continue
                
                print(f"[MinerU]   Table {idx+1}: {len(rows)} rows")
                
                # Build 2D grid (handling rowspan/colspan is complex, so flatten)
                markdown_rows = []
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    cell_texts = []
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        # Add note if cell has span attributes
                        if cell.get("rowspan") or cell.get("colspan"):
                            span_info = []
                            if cell.get("colspan"):
                                span_info.append(f"跨{cell['colspan']}列")
                            if cell.get("rowspan"):
                                span_info.append(f"跨{cell['rowspan']}行")
                            cell_text += f"[{','.join(span_info)}]"
                        cell_texts.append(cell_text)
                    markdown_rows.append(cell_texts)
                
                # Convert to Markdown table
                if not markdown_rows:
                    print(f"[MinerU]   Table {idx+1}: No cell data, skipping")
                    continue
                
                # Determine column count (max cells in any row)
                max_cols = max(len(row) for row in markdown_rows)
                print(f"[MinerU]   Table {idx+1}: {max_cols} columns")
                
                # Pad rows to same column count
                for row in markdown_rows:
                    while len(row) < max_cols:
                        row.append("")
                
                # Build Markdown table
                md_lines = []
                for i, row in enumerate(markdown_rows):
                    md_lines.append("| " + " | ".join(row) + " |")
                    # Add header separator after first row
                    if i == 0:
                        md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
                
                markdown_table = "\n".join(md_lines)
                
                # Replace original HTML table with Markdown
                result = result.replace(str(table), f"\n\n{markdown_table}\n\n")
                converted_count += 1
                print(f"[MinerU]   Table {idx+1}: Converted successfully")
            
            except Exception as e:
                # If conversion fails, leave HTML as-is
                print(f"[MinerU]   Table {idx+1}: Conversion failed: {e}")
                continue
        
        print(f"[MinerU]   Converted {converted_count}/{len(tables)} tables")
        return result