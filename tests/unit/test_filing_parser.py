"""Unit tests for SEC filing HTML parser and cleaner."""

from datetime import UTC, date, datetime

import pytest

from financial_research_agent.extract.schemas import RawDocumentMetadata, RawSECFiling
from financial_research_agent.transform.parser import (
    EmptyContentError,
    FilingParser,
)
from financial_research_agent.transform.schemas import CleanDocument

SAMPLE_10K_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Form 10-K Annual Report</title>
    <style>body { font-family: Arial; }</style>
    <script>function track() { return true; }</script>
</head>
<body>
    <div class="header">
        <h1>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</h1>
        <p>Washington, D.C. 20549</p>
    </div>
    <div>
        PART I
        ITEM 1. BUSINESS
        Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets,
        wearables, and accessories, and sells a variety of related services.
    </div>
    <div>
        ITEM 1A. RISK FACTORS
        The Company's business, reputation, results of operations and financial condition
        can be adversely affected by global economic conditions, competition, and supply chain.
    </div>
    <div>
        PART II
        ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF OPERATIONS
        Total net sales increased by 8% during the fiscal year driven by strong demand for services
        and mobile devices across international markets.
    </div>
</body>
</html>
"""


@pytest.fixture
def parser() -> FilingParser:
    return FilingParser()


@pytest.mark.issue_6
def test_clean_html_strips_scripts_and_styles(parser: FilingParser) -> None:
    cleaned = parser.clean_html(SAMPLE_10K_HTML)
    assert "function track()" not in cleaned
    assert "font-family: Arial" not in cleaned
    assert "UNITED STATES SECURITIES AND EXCHANGE COMMISSION" in cleaned
    assert "Apple Inc. designs, manufactures" in cleaned


@pytest.mark.issue_6
def test_clean_html_whitespace_normalization(parser: FilingParser) -> None:
    messy_html = "<p>Word1   \t  Word2&nbsp;&nbsp;&nbsp;Word3\n\n\n\n\nWord4</p>"
    cleaned = parser.clean_html(messy_html)
    assert "Word1 Word2 Word3" in cleaned
    assert "\n\n\n" not in cleaned


@pytest.mark.issue_6
def test_clean_html_empty_content_raises_error(parser: FilingParser) -> None:
    with pytest.raises(EmptyContentError, match="empty"):
        parser.clean_html("   ")

    with pytest.raises(EmptyContentError, match="no text"):
        parser.clean_html("<div><style>body{}</style><script>var x=1;</script></div>")


@pytest.mark.issue_6
def test_extract_sections(parser: FilingParser) -> None:
    cleaned = parser.clean_html(SAMPLE_10K_HTML)
    sections = parser.extract_sections(cleaned)

    assert len(sections) == 3
    sec_ids = [s.section_id for s in sections]
    assert "item_1" in sec_ids
    assert "item_1a" in sec_ids
    assert "item_7" in sec_ids

    risk_section = next(s for s in sections if s.section_id == "item_1a")
    assert "RISK FACTORS" in risk_section.title.upper()
    assert "reputation, results of operations" in risk_section.content
    assert risk_section.char_count == len(risk_section.content)


@pytest.mark.issue_6
def test_parse_filing_end_to_end(parser: FilingParser) -> None:
    meta = RawDocumentMetadata(
        source_uri="https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl.htm",
        extracted_at=datetime(2023, 11, 3, 12, 0, 0, tzinfo=UTC),
        content_hash="mockhash123",
    )
    raw_filing = RawSECFiling(
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        accession_number="0000320193-23-000106",
        raw_content=SAMPLE_10K_HTML,
        metadata=meta,
    )

    clean_doc = parser.parse_filing(raw_filing)

    assert isinstance(clean_doc, CleanDocument)
    assert clean_doc.ticker == "AAPL"
    assert clean_doc.form_type == "10-K"
    assert clean_doc.document_id == "clean_AAPL_0000320193-23-000106"
    assert len(clean_doc.sections) == 3
    assert clean_doc.metadata["section_count"] == 3


@pytest.mark.issue_6
def test_parse_raw_text_plain(parser: FilingParser) -> None:
    plain = """ITEM 1. BUSINESS
Here is the plain business text description.

ITEM 7. MD&A
Financial analysis plain text discussion."""
    clean_doc = parser.parse_raw_text(
        content=plain,
        document_id="doc_plain_test",
        ticker="MSFT",
        form_type="10-K",
    )

    assert clean_doc.document_id == "doc_plain_test"
    assert len(clean_doc.sections) == 2
    assert clean_doc.sections[0].section_id == "item_1"
    assert clean_doc.sections[1].section_id == "item_7"
