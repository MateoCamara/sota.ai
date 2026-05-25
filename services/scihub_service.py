"""Multi-mirror Sci-Hub fallback for SOTAi.

⚠️  LEGAL NOTE
---------------
Sci-Hub is a copyright-grey resource. Distribution of papers obtained
through it may breach copyright law in some jurisdictions (including
the EU and the United States) and is blocked at the DNS level in
several countries (Spain, France, Italy, the UK, India and others).

This service is **opt-in**: it must be explicitly enabled per call via
`allow_scihub=True`. The caller is responsible for evaluating whether
their jurisdiction and use case (e.g. systematic review of papers their
institution has paid access to, but cannot deliver electronically)
permit such use. SOTAi does not endorse copyright violation.

WHY THIS EXISTS
---------------
The downstream library `pypaperretriever` already shells out to
Sci-Hub, but it hardcodes `sci-hub.se`, which is the very mirror that
is most commonly DNS-blocked (e.g. in Spain by court order). This
service:

  * tries a list of resolving mirrors (`sci-hub.ren`, `sci-hub.ru`,
    `sci-hub.st`, `sci-hub.cat`, `sci.bban.top`), so institutional
    blocks of one mirror do not break the fallback;
  * parses every common embed pattern (`<iframe src=>`,
    `<embed src=>`, `<meta content=>`, `<a href=>`, JS
    `location.href=`) instead of only `iframe`;
  * uses only stdlib (`urllib`) — no extra dependency.
"""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_MIRRORS = (
    "sci-hub.ren",
    "sci-hub.ru",
    "sci-hub.st",
    "sci-hub.cat",
    "sci.bban.top",
)


_PDF_URL_RX = re.compile(
    r'(?:src|content|href)\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']',
    re.IGNORECASE,
)
_LOC_HREF_RX = re.compile(
    r"location\.(?:href|replace)\s*=?\s*\(?\s*['\"]([^'\"]+\.pdf[^'\"]*)",
    re.IGNORECASE,
)


class SciHubService:
    """Direct Sci-Hub fallback that bypasses single-mirror DNS blocks.

    Usage:
        sh = SciHubService(download_dir="downloaded_papers")
        result = sh.download(doi="10.1109/taslp.2020.2971417",
                             allow_scihub=True)
        # result == {success, filepath, source, message}
    """

    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    )

    def __init__(self, download_dir: str = "downloaded_papers",
                 mirrors: tuple[str, ...] = DEFAULT_MIRRORS,
                 mirror_delay_s: float = 0.5,
                 timeout_s: int = 30):
        self.download_dir = download_dir
        self.mirrors = tuple(mirrors)
        self.mirror_delay_s = mirror_delay_s
        self.timeout_s = timeout_s
        os.makedirs(self.download_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, doi: str, output_filename: str | None = None,
                 allow_scihub: bool = False) -> dict:
        """Try every configured mirror until one returns a PDF.

        If `allow_scihub` is False (the default), this is a no-op that
        returns success=False. The opt-in flag exists to make Sci-Hub
        use an explicit decision at every call site.
        """
        if not allow_scihub:
            return {
                "success": False, "filepath": None,
                "source": "SciHub-Disabled",
                "message": "allow_scihub=False (opt-in required; see legal note in services/scihub_service.py)",
            }
        if not doi:
            return {"success": False, "filepath": None,
                    "source": "SciHub", "message": "no DOI supplied"}

        dest = os.path.join(self.download_dir,
                            output_filename or self._sanitize_doi(doi) + ".pdf")

        for mirror in self.mirrors:
            landing = f"https://{mirror}/{urllib.parse.quote(doi, safe='/')}"
            data, ctype = self._fetch(landing)
            if data is None:
                continue
            # Sometimes the mirror just returns the PDF.
            if data.startswith(b"%PDF"):
                with open(dest, "wb") as fh:
                    fh.write(data)
                return {"success": True, "filepath": dest,
                        "source": f"SciHub-{mirror}",
                        "message": f"{len(data)} bytes (direct)"}
            if "html" not in (ctype or "").lower():
                continue
            pdf_url = self._find_pdf_url(data, landing)
            if not pdf_url:
                continue
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            pdf_data, pdf_ct = self._fetch(pdf_url)
            if pdf_data and pdf_data.startswith(b"%PDF"):
                with open(dest, "wb") as fh:
                    fh.write(pdf_data)
                return {"success": True, "filepath": dest,
                        "source": f"SciHub-{mirror}",
                        "message": f"{len(pdf_data)} bytes (via {urllib.parse.urlparse(pdf_url).netloc})"}
            time.sleep(self.mirror_delay_s)

        return {"success": False, "filepath": None,
                "source": "SciHub-AllMirrorsFailed",
                "message": f"none of {len(self.mirrors)} mirrors returned a PDF"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_doi(doi: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")[:120]

    def _fetch(self, url: str) -> tuple[bytes | None, str | None]:
        req = urllib.request.Request(
            url, headers={"User-Agent": self.USER_AGENT, "Accept": "*/*"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
            return data, ctype
        except urllib.error.HTTPError as exc:
            return None, f"HTTP {exc.code}"
        except Exception:
            return None, None

    @staticmethod
    def _find_pdf_url(html: bytes, base_url: str) -> str | None:
        text = html.decode("utf-8", errors="replace")
        for rx in (_PDF_URL_RX, _LOC_HREF_RX):
            m = rx.search(text)
            if m:
                url = m.group(1).split("#")[0]
                return urllib.parse.urljoin(base_url, url)
        return None
