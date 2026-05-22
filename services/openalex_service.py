"""OpenAlex source for SOTAi.

OpenAlex (api.openalex.org) is a free, no-auth scholarly aggregator
covering ~250M works across all disciplines. Compared to the ArXiv +
PubMed services already shipped with SOTAi, OpenAlex adds:

  - journal coverage (JASA, Nature, IEEE Trans, Elsevier, Springer, ...),
  - conference proceedings (Interspeech, ICASSP, ACL, NeurIPS, ...),
  - abstracts in the response (via inverted-index reconstruction),
  - polite-pool rate limits when you provide an email.

Reference: https://developers.openalex.org/api-entities/works
"""

import json
import time
import urllib.parse
import urllib.request


OPENALEX_BASE = "https://api.openalex.org/works"


class OpenAlexService:
    def __init__(self, mailto: str | None = None,
                 per_page: int = 100,
                 polite_delay_s: float = 0.4):
        """
        Parameters
        ----------
        mailto : str, optional
            Email address used to put requests in OpenAlex's "polite pool"
            (higher rate limits). No account creation required — they only
            ask that you identify yourself. Recommended.
        per_page : int, default 100
            Page size. OpenAlex accepts up to 200.
        polite_delay_s : float, default 0.4
            Seconds to wait between paginated requests.
        """
        self.mailto = mailto
        self.per_page = max(1, min(per_page, 200))
        self.polite_delay_s = polite_delay_s

    # ------------------------------------------------------------------
    # Public API mirrors sota.ai's other *_service.py interfaces
    # ------------------------------------------------------------------

    def search_papers(self, query: str, limit: int = 10,
                      from_year: int | None = None,
                      to_year: int | None = None,
                      language: str = "en") -> list:
        """
        Search OpenAlex for papers matching `query`.

        Returns a list of dicts with the SOTAi canonical keys:
        Title, DOI, Publication_Year, Authors, Source, URL, plus the
        extra key 'Abstract' (reconstructed from OpenAlex's inverted
        index) which downstream analyzers can use to do cheap
        title-and-abstract triage without downloading the full PDF.

        Parameters
        ----------
        query : str
            Boolean text query. OpenAlex search supports phrases
            ("vocal tract"), AND, OR, and grouping with parentheses.
        limit : int, default 10
            Approximate maximum number of records to return. The actual
            count may be slightly larger because of pagination boundaries.
        from_year, to_year : int, optional
            Publication-year filter. Use None to leave unbounded.
        language : str, default 'en'
            ISO language code for the filter, or '' / None to disable.
        """
        print(f"Searching OpenAlex for: {query}")

        filters = []
        if from_year and to_year:
            filters.append(f"publication_year:{from_year}-{to_year}")
        elif from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        elif to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")
        if language:
            filters.append(f"language:{language}")

        params_base = {
            "search": query,
            "per-page": self.per_page,
        }
        if filters:
            params_base["filter"] = ",".join(filters)
        if self.mailto:
            params_base["mailto"] = self.mailto

        results: list[dict] = []
        page = 1
        while len(results) < limit:
            params = dict(params_base, page=page)
            url = f"{OPENALEX_BASE}?{urllib.parse.urlencode(params)}"
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "SOTAi/1.0 "
                            f"(mailto:{self.mailto or 'anonymous'})"
                        ),
                    },
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
            except Exception as exc:
                print(f"OpenAlex search error on page {page}: {exc}")
                break

            page_results = data.get("results", []) or []
            if not page_results:
                break

            for w in page_results:
                results.append(self._work_to_record(w))
                if len(results) >= limit:
                    break

            if len(page_results) < self.per_page:
                break  # last page reached
            page += 1
            time.sleep(self.polite_delay_s)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict | None) -> str:
        """OpenAlex stores abstracts as {word: [positions]}. Rebuild it."""
        if not inverted_index:
            return ""
        positions = []
        for word, idxs in inverted_index.items():
            for i in idxs:
                positions.append((i, word))
        if not positions:
            return ""
        positions.sort()
        out = [""] * (positions[-1][0] + 1)
        for i, w in positions:
            out[i] = w
        return " ".join(w for w in out if w).strip()

    @staticmethod
    def _venue_of(work: dict) -> str:
        loc = work.get("primary_location") or {}
        src = loc.get("source") or {}
        return src.get("display_name") or ""

    @staticmethod
    def _authors_of(work: dict) -> str:
        return ", ".join(
            (a.get("author") or {}).get("display_name", "")
            for a in work.get("authorships", [])
            if (a.get("author") or {}).get("display_name")
        )

    @staticmethod
    def _best_url(work: dict) -> str:
        # Prefer an OA PDF if available, then the primary landing page.
        oa = work.get("best_oa_location") or {}
        if oa.get("pdf_url"):
            return oa["pdf_url"]
        pl = work.get("primary_location") or {}
        return pl.get("pdf_url") or pl.get("landing_page_url") or work.get("id") or ""

    @classmethod
    def _work_to_record(cls, work: dict) -> dict:
        doi = (work.get("doi") or "").replace("https://doi.org/", "") or "N/A"
        title = work.get("title") or work.get("display_name") or "N/A"
        venue = cls._venue_of(work)
        return {
            "Title": title,
            "DOI": doi,
            "Publication_Year": work.get("publication_year") or "N/A",
            "Authors": cls._authors_of(work) or "N/A",
            "Source": f"OpenAlex ({venue})" if venue else "OpenAlex",
            "URL": cls._best_url(work),
            # Extra fields (not yet consumed by sota.ai but cheap to keep):
            "Abstract": cls._reconstruct_abstract(work.get("abstract_inverted_index")),
            "OpenAlex_ID": work.get("id", ""),
            "Type": work.get("type", ""),
        }
