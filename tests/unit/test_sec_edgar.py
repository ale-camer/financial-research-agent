"""Unit tests for SEC EDGAR extractor client."""

import hashlib
from datetime import date

import httpx
import pytest

from financial_research_agent.extract.schemas import RawSECFiling
from financial_research_agent.extract.sec_edgar import (
    FilingNotFoundError,
    InvalidUserAgentError,
    SECEdgarClient,
)

SAMPLE_USER_AGENT = "ResearchTeam admin@example.com"

SAMPLE_TICKERS_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp."},
}

SAMPLE_SUBMISSIONS_AAPL = {
    "cik": "0000320193",
    "entityType": "operating",
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-23-000106", "0000320193-23-000077"],
            "filingDate": ["2023-11-03", "2023-08-04"],
            "reportDate": ["2023-09-30", "2023-07-01"],
            "form": ["10-K", "10-Q"],
            "primaryDocument": ["aapl-20230930.htm", "aapl-20230701.htm"],
        }
    },
}

SAMPLE_10K_HTML = "<html><body><h1>Apple Inc. Form 10-K Annual Report</h1></body></html>"


@pytest.fixture
def mock_sec_client() -> SECEdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "company_tickers.json" in url_str:
            return httpx.Response(200, json=SAMPLE_TICKERS_JSON)
        if "CIK0000320193.json" in url_str:
            return httpx.Response(200, json=SAMPLE_SUBMISSIONS_AAPL)
        if "CIK9999999999.json" in url_str:
            return httpx.Response(404, text="Not Found")
        if "000032019323000106/aapl-20230930.htm" in url_str:
            return httpx.Response(200, text=SAMPLE_10K_HTML)
        if "000032019323000077/aapl-20230701.htm" in url_str:
            return httpx.Response(200, text="<html>10-Q report</html>")
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return SECEdgarClient(user_agent=SAMPLE_USER_AGENT, http_client=http_client)


@pytest.mark.issue_2
def test_invalid_user_agent_validation() -> None:
    with pytest.raises(InvalidUserAgentError):
        SECEdgarClient(user_agent="")

    with pytest.raises(InvalidUserAgentError):
        SECEdgarClient(user_agent="GenericBot without email")


@pytest.mark.issue_2
def test_valid_user_agent_context_manager() -> None:
    with SECEdgarClient(user_agent="ValidBot user@domain.com") as client:
        assert client.user_agent == "ValidBot user@domain.com"


@pytest.mark.issue_2
def test_get_cik_by_ticker_and_cache(mock_sec_client: SECEdgarClient) -> None:
    cik = mock_sec_client.get_cik_by_ticker("aapl")
    assert cik == "0000320193"

    # Second call uses internal cache
    assert mock_sec_client.get_cik_by_ticker("AAPL") == "0000320193"


@pytest.mark.issue_2
def test_get_cik_by_ticker_not_found(mock_sec_client: SECEdgarClient) -> None:
    with pytest.raises(FilingNotFoundError, match="Ticker 'UNKNOWN' not found"):
        mock_sec_client.get_cik_by_ticker("UNKNOWN")


@pytest.mark.issue_2
def test_get_company_submissions_success(mock_sec_client: SECEdgarClient) -> None:
    data = mock_sec_client.get_company_submissions("320193")
    assert data["name"] == "Apple Inc."
    assert "filings" in data


@pytest.mark.issue_2
def test_get_company_submissions_not_found(mock_sec_client: SECEdgarClient) -> None:
    with pytest.raises(FilingNotFoundError):
        mock_sec_client.get_company_submissions("9999999999")


@pytest.mark.issue_2
def test_fetch_filing_10k_success(mock_sec_client: SECEdgarClient) -> None:
    filing = mock_sec_client.fetch_filing(ticker="AAPL", form_type="10-K")

    assert isinstance(filing, RawSECFiling)
    assert filing.ticker == "AAPL"
    assert filing.cik == "0000320193"
    assert filing.form_type == "10-K"
    assert filing.filing_date == date(2023, 11, 3)
    assert filing.accession_number == "0000320193-23-000106"
    assert filing.raw_content == SAMPLE_10K_HTML

    expected_hash = hashlib.sha256(SAMPLE_10K_HTML.encode("utf-8")).hexdigest()
    assert filing.metadata.content_hash == expected_hash
    assert "0000320193" in filing.metadata.source_uri


@pytest.mark.issue_2
def test_fetch_filing_specific_form_and_accession(mock_sec_client: SECEdgarClient) -> None:
    filing = mock_sec_client.fetch_filing(
        ticker="AAPL",
        form_type="10-Q",
        accession_number="0000320193-23-000077",
    )
    assert filing.form_type == "10-Q"
    assert filing.accession_number == "0000320193-23-000077"
    assert "10-Q report" in filing.raw_content


@pytest.mark.issue_2
def test_fetch_filing_not_found(mock_sec_client: SECEdgarClient) -> None:
    with pytest.raises(
        FilingNotFoundError, match="No filing found for ticker 'AAPL' with form '8-K'"
    ):
        mock_sec_client.fetch_filing(ticker="AAPL", form_type="8-K")
