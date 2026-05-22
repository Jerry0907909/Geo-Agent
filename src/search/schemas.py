"""Deep Search 数据模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class DeepSearchRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    max_sources: int = Field(default=8, ge=3, le=20)
    max_tokens: int = Field(default=8000, ge=2000, le=16000)
    time_range: Optional[str] = Field(default=None, description="day|week|month|year")


class RawSearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0.0
    source_type: str = "general"
    published_date: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedChunk(BaseModel):
    chunk_id: str
    text: str
    source_url: str
    source_title: str
    chunk_index: int = 0

    class Config:
        from_attributes = True


class RankedChunk(ExtractedChunk):
    relevance_score: float = 0.0
    rank: int = 0


class CitationRef(BaseModel):
    source_id: int
    url: str
    title: str


class DeepSearchEvent(BaseModel):
    type: str  # "status" | "content" | "sources" | "citation" | "done" | "error"
    message: Optional[str] = None
    content: Optional[str] = None
    sources: Optional[List[dict]] = None
    citations: Optional[List[dict]] = None
    execution_time: Optional[float] = None
