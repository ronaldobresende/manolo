"""Modelos Pydantic para validação de dados."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class LLMChecklistResponse(BaseModel):
    """Modelo para validar o parsing do LLM antes da inserção no banco."""
    campos_preenchidos: Dict[str, Any] = Field(default_factory=dict)
    campos_ausentes: List[str] = Field(default_factory=list)