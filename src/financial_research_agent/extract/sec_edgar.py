"""SEC EDGAR extractor and client for fetching company filings."""

import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any

import httpx

from financial_research_agent.extract.schemas import RawDocumentMetadata, RawSECFiling


class SECEdgarError(Exception):
    """Base exception for SEC EDGAR extraction errors."""


class FilingNotFoundError(SECEdgarError):
    """Raised when a requested filing or company cannot be located."""


class InvalidUserAgentError(SECEdgarError):
    """Raised when the provided user agent does not meet SEC guidelines."""


class SECEdgarClient:
    """Client for querying SEC EDGAR submissions and retrieving raw filing documents."""

    def __init__(
        self,
        user_agent: str,
        http_client: httpx.Client | None = None,
        base_data_url: str = "https://data.sec.gov",
        base_sec_url: str = "https://www.sec.gov",
    ) -> None:
        self.user_agent = self._validate_user_agent(user_agent)
        self.base_data_url = base_data_url.rstrip("/")
        self.base_sec_url = base_sec_url.rstrip("/")
        self._owned_client = http_client is None
        self._client = http_client or httpx.Client(
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
        )
        self._ticker_cik_cache: dict[str, str] = {}

    @staticmethod
    def _validate_user_agent(user_agent: str) -> str:
        """Validate user-agent per SEC guidelines (format: Organization Contact@domain.com)."""
        stripped = user_agent.strip()
        if not stripped or "@" not in stripped:
            raise InvalidUserAgentError(
                "SEC EDGAR requires a User-Agent containing contact email. "
                "Format: 'Sample Company Name AdminContact@domain.com'"
            )
        return stripped

    def close(self) -> None:
        """Close the underlying HTTP client if created internally."""
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "SECEdgarClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def get_cik_by_ticker(self, ticker: str) -> str:
        """Resolve an equity ticker symbol to a 10-digit zero-padded SEC CIK string."""
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker in self._ticker_cik_cache:
            return self._ticker_cik_cache[normalized_ticker]

        url = f"{self.base_sec_url}/files/company_tickers.json"
        try:
            response = self._client.get(url)
            response.raise_for_status()
            data: dict[str, dict[str, Any]] = response.json()
        except httpx.HTTPError as exc:
            raise SECEdgarError(f"Failed to fetch SEC company tickers mapping: {exc}") from exc

        for entry in data.values():
            entry_ticker = str(entry.get("ticker", "")).strip().upper()
            if entry_ticker == normalized_ticker:
                cik_val = int(entry["cik_str"])
                cik_str = f"{cik_val:010d}"
                self._ticker_cik_cache[normalized_ticker] = cik_str
                return cik_str

        raise FilingNotFoundError(
            f"Ticker '{normalized_ticker}' not found in SEC company directory"
        )

    def get_company_submissions(self, cik: str) -> dict[str, Any]:
        """Fetch the submissions metadata JSON document for a given CIK."""
        clean_cik = f"{int(cik):010d}"
        url = f"{self.base_data_url}/submissions/CIK{clean_cik}.json"
        try:
            response = self._client.get(url)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise FilingNotFoundError(f"Submissions for CIK '{clean_cik}' not found") from exc
            raise SECEdgarError(
                f"HTTP error fetching submissions for CIK '{clean_cik}': {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise SECEdgarError(
                f"Network error fetching submissions for CIK '{clean_cik}': {exc}"
            ) from exc

    def fetch_filing(
        self,
        ticker: str,
        form_type: str = "10-K",
        accession_number: str | None = None,
    ) -> RawSECFiling:
        """Retrieve a specific filing by ticker, form type, and optional accession number."""
        cik_str = self.get_cik_by_ticker(ticker)
        submissions = self.get_company_submissions(cik_str)

        filings_data = submissions.get("filings", {}).get("recent", {})
        forms: list[str] = filings_data.get("form", [])
        accession_numbers: list[str] = filings_data.get("accessionNumber", [])
        filing_dates: list[str] = filings_data.get("filingDate", [])
        primary_docs: list[str] = filings_data.get("primaryDocument", [])

        target_idx: int | None = None
        for idx, (f_type, acc_num) in enumerate(zip(forms, accession_numbers, strict=False)):
            if f_type.upper() == form_type.upper() and (
                accession_number is None or acc_num == accession_number
            ):
                target_idx = idx
                break

        if target_idx is None:
            acc_info = f" with accession '{accession_number}'" if accession_number else ""
            raise FilingNotFoundError(
                f"No filing found for ticker '{ticker}' with form '{form_type}'{acc_info}"
            )

        matched_accession = accession_numbers[target_idx]
        matched_date_str = filing_dates[target_idx]
        matched_primary_doc = primary_docs[target_idx]

        filing_date_val = date.fromisoformat(matched_date_str)
        cik_int = int(cik_str)
        acc_no_clean = re.sub(r"[^0-9]", "", matched_accession)
        doc_url = (
            f"{self.base_sec_url}/Archives/edgar/data/"
            f"{cik_int}/{acc_no_clean}/{matched_primary_doc}"
        )

        try:
            doc_response = self._client.get(doc_url)
            doc_response.raise_for_status()
            raw_text = doc_response.text
        except httpx.HTTPError as exc:
            raise SECEdgarError(f"Failed to fetch filing document from {doc_url}: {exc}") from exc

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        extracted_at = datetime.now(UTC)

        metadata = RawDocumentMetadata(
            source_uri=doc_url,
            extracted_at=extracted_at,
            content_hash=content_hash,
            extra_attributes={
                "form_type": form_type,
                "primary_document": matched_primary_doc,
                "cik": cik_str,
            },
        )

        return RawSECFiling(
            ticker=ticker.strip().upper(),
            cik=cik_str,
            form_type=form_type,
            filing_date=filing_date_val,
            accession_number=matched_accession,
            raw_content=raw_text,
            metadata=metadata,
        )
