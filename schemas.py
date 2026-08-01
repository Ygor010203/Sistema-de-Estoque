from pydantic import BaseModel
from typing import Optional
from datetime import datetime  # ✅ IMPORT AQUI

class ProdutoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    quantidade: int

class ProdutoResponse(ProdutoBase):
    id: int

    class Config:
        from_attributes = True

class HistoricoResponse(BaseModel):
    id: int
    acao: str
    produto_nome: str
    data_hora: datetime

    class Config:
        from_attributes = True