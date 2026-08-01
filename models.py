from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class Produto(Base):
    __tablename__ = "produtos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    descricao = Column(String, index=True)
    preco = Column(Float, index=True)
    quantidade = Column(Integer, index=True)

# Novo modelo para a tabela de logs/histórico de alterações
class HistoricoMovimentacao(Base):
    __tablename__ = "historico"

    id = Column(Integer, primary_key=True, index=True)
    acao = Column(String, index=True) # Ex: "CRIADO", "ATUALIZADO", "DELETADO"
    produto_nome = Column(String)
    data_hora = Column(DateTime, default=datetime.utcnow)