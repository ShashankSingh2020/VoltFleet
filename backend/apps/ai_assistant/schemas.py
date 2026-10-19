from typing import List
from pydantic import BaseModel, Field


class AnomalyExplanationSchema(BaseModel):
    summary: str
    hypotheses: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_grounding: str