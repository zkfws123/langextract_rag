import io
import os
import ssl
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests
import urllib3
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

        print(f"\n[MinerU] Downloading result...")
        zip_content = None
        
        # Method 1: Try with requests (SSL bypass)
        for attempt in range(3):
            try:
                zip_response = self.session.get(full_zip_url, timeout=120)
                zip_response.raise_for_status()
                zip_content = zip_response.content
                break
            except requests.exceptions.SSLError as e:
                print(f"[MinerU]   SSL error (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    print(f"[MinerU]   Trying curl as fallback...")
                time.sleep(2)
        
        # Method 2: Fallback to curl if requests fails
        if zip_content is None:
            import subprocess
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp_path = tmp.name
            
            try:
                # curl with SSL bypass and retry
                result = subprocess.run(
                    ["curl", "-k", "-L", "-o", tmp_path, "--retry", "3", "--retry-delay", "2", full_zip_url],
                    capture_output=True,
                    timeout=120
                )
                if result.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    with open(tmp_path, "rb") as f:
                        zip_content = f.read()
                    print(f"[MinerU]   Downloaded via curl: {len(zip_content)} bytes")
                else:
                    print(f"[MinerU]   curl failed: {result.stderr.decode()}")
            except Exception as e:
                print(f"[MinerU]   curl exception: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
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
