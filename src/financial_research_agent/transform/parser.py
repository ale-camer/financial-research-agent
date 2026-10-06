"""HTML parsing and text cleaning for SEC filings and financial documents."""

import re
import unicodedata
from datetime import date

from bs4 import BeautifulSoup

from financial_research_agent.extract.schemas import RawSECFiling
from financial_research_agent.transform.schemas import CleanDocument, FilingSection


class ParserError(Exception):
    """Base exception for document parsing failures."""


class EmptyContentError(ParserError):
    """Raised when the input document content is empty or contains no parseable text."""


class FilingParser:
    """Cleans raw HTML/XML SEC filings and extracts structured item sections."""

    def __init__(self, preferred_parser: str = "lxml") -> None:
        self.parser_engine = self._determine_parser(preferred_parser)

    @staticmethod
    def _determine_parser(preferred: str) -> str:
        """Verify if preferred parser is available, falling back to html.parser."""
        try:
            BeautifulSoup("<html></html>", preferred)
            return preferred
        except Exception:
            return "html.parser"

    def clean_html(self, raw_html: str) -> str:
        """Strip markup, scripts, and XBRL tags, returning normalized plain text."""
        if not raw_html or not raw_html.strip():
            raise EmptyContentError("Raw content string is empty.")

        soup = BeautifulSoup(raw_html, self.parser_engine)

        unwanted_tags = [
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav",
            "svg",
            "ix:header",
            "ix:hidden",
            "xbrli:context",
            "xbrli:unit",
        ]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        text = soup.get_text(separator="\n")
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

        # Collapse horizontal whitespace
        normalized = re.sub(r"[ \t]+", " ", normalized)
        # Collapse excessive line breaks (more than two)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        cleaned = normalized.strip()
        if not cleaned:
            raise EmptyContentError("Cleaned document contains no text after tag stripping.")
        return cleaned

    def extract_sections(self, clean_text: str) -> list[FilingSection]:
        """Extract standard SEC Item sections (e.g. Item 1, Item 1A, Item 7) from cleaned text."""
        item_pattern = re.compile(
            r"(?mi)^[ \t]*(?:PART\s+[I|V|X]+\s*[\.\:\-]?\s*)?"
            r"ITEM\s+([0-9]{1,2}[A-Z]?)\.?\s*[:\-\u2013\u2014]?\s*(.*?)$"
        )

        matches = list(item_pattern.finditer(clean_text))
        if not matches:
            return []

        sections: list[FilingSection] = []
        for i, match in enumerate(matches):
            item_num = match.group(1).upper()
            title_rest = match.group(2).strip()
            title = f"Item {item_num}" + (f": {title_rest}" if title_rest else "")

            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)

            content = clean_text[start_pos:end_pos].strip()
            # Ignore false matches with trivially short content (e.g. table of contents entries)
            if len(content) < 20 and i + 1 < len(matches):
                continue

            section_id = f"item_{item_num.lower()}"
            sections.append(
                FilingSection(
                    section_id=section_id,
                    title=title,
                    content=content,
                    char_count=len(content),
                )
            )

        return sections

    def parse_filing(self, filing: RawSECFiling) -> CleanDocument:
        """Parse a RawSECFiling into a structured CleanDocument."""
        clean_text = self.clean_html(filing.raw_content)
        sections = self.extract_sections(clean_text)

        doc_id = f"clean_{filing.ticker}_{filing.accession_number}"
        return CleanDocument(
            document_id=doc_id,
            source_document_id=filing.accession_number,
            ticker=filing.ticker,
            form_type=filing.form_type,
            filing_date=filing.filing_date,
            clean_text=clean_text,
            sections=sections,
            metadata={
                "parser_engine": self.parser_engine,
                "section_count": len(sections),
                "original_char_count": len(filing.raw_content),
                "clean_char_count": len(clean_text),
            },
        )

    def parse_raw_text(
        self,
        content: str,
        document_id: str,
        ticker: str = "",
        form_type: str = "UNKNOWN",
        filing_date: date | None = None,
    ) -> CleanDocument:
        """Parse raw HTML or plain text string directly into a CleanDocument."""
        if "<" in content and ">" in content:
            clean_text = self.clean_html(content)
        else:
            clean_text = content.strip()
            if not clean_text:
                raise EmptyContentError("Raw text content is empty.")

        sections = self.extract_sections(clean_text)
        return CleanDocument(
            document_id=document_id,
            source_document_id=document_id,
            ticker=ticker,
            form_type=form_type,
            filing_date=filing_date,
            clean_text=clean_text,
            sections=sections,
            metadata={"parser_engine": self.parser_engine, "section_count": len(sections)},
        )
