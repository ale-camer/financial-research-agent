"""Extract layer for pulling raw financial documents, market data, and news."""

from financial_research_agent.extract.market_data import (
    EmptyMarketDataError,
    MarketDataError,
    MarketDataExtractor,
)
from financial_research_agent.extract.news_rss import (
    EmptyFeedError,
    NewsExtractionError,
    NewsRSSExtractor,
)
from financial_research_agent.extract.schemas import (
    DocumentType,
    MarketDataPoint,
    RawDocument,
    RawDocumentMetadata,
    RawMarketData,
    RawNewsArticle,
    RawPayload,
    RawSECFiling,
)
from financial_research_agent.extract.sec_edgar import (
    FilingNotFoundError,
    InvalidUserAgentError,
    SECEdgarClient,
    SECEdgarError,
)

__all__ = [
    "DocumentType",
    "EmptyFeedError",
    "EmptyMarketDataError",
    "FilingNotFoundError",
    "InvalidUserAgentError",
    "MarketDataError",
    "MarketDataExtractor",
    "MarketDataPoint",
    "NewsExtractionError",
    "NewsRSSExtractor",
    "RawDocument",
    "RawDocumentMetadata",
    "RawMarketData",
    "RawNewsArticle",
    "RawPayload",
    "RawSECFiling",
    "SECEdgarClient",
    "SECEdgarError",
]
