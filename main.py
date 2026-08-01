from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas
from database import SessionLocal, engine

# Cria as tabelas no banco de dados automaticamente se elas não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuração do CORS para permitir a comunicação com o Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Função para conectar com o banco de dados a cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Cadastrar um novo produto (Com validação de duplicidade e log)
@app.post("/produtos/", response_model=schemas.ProdutoResponse)
def criar_produto(produto: schemas.ProdutoBase, db: Session = Depends(get_db)):
    produto_existente = db.query(models.Produto).filter(models.Produto.nome == produto.nome).first()
    if produto_existente:
        raise HTTPException(status_code=400, detail="Já existe um produto cadastrado com este nome.")

    db_produto = models.Produto(
        nome=produto.nome,
        descricao=produto.descricao,
        preco=produto.preco,
        quantidade=produto.quantidade
    )
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)

    log = models.HistoricoMovimentacao(acao="CRIADO", produto_nome=db_produto.nome)
    db.add(log)
    db.commit()

    return db_produto

# 2. Listar produtos (Com paginação e busca por nome)
@app.get("/produtos/", response_model=List[schemas.ProdutoResponse])
def listar_produtos(
    pesquisa: Optional[str] = Query(None, description="Buscar produto por nome"),
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Produto)
    if pesquisa:
        query = query.filter(models.Produto.nome.ilike(f"%{pesquisa}%"))
    
    produtos = query.offset(skip).limit(limit).all()
    return produtos

# 3. Listar produtos com estoque crítico
@app.get("/produtos/estoque-critico/", response_model=List[schemas.ProdutoResponse])
def listar_produtos_estoque_critico(db: Session = Depends(get_db)):
    produtos_criticos = db.query(models.Produto).filter(models.Produto.quantidade < 5).all()
    return produtos_criticos

# 4. Rota para visualizar o Histórico de Movimentações
@app.get("/historico/", response_model=List[schemas.HistoricoResponse])
def ver_historico(db: Session = Depends(get_db)):
    historico = db.query(models.HistoricoMovimentacao).all()
    return historico

# 5. Atualizar um produto existente
@app.put("/produtos/{produto_id}", response_model=schemas.ProdutoResponse)
def atualizar_produto(produto_id: int, produto: schemas.ProdutoBase, db: Session = Depends(get_db)):
    db_produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    db_produto.nome = produto.nome
    db_produto.descricao = produto.descricao
    db_produto.preco = produto.preco
    db_produto.quantidade = produto.quantidade
    
    db.commit()
    db.refresh(db_produto)

    log = models.HistoricoMovimentacao(acao="ATUALIZADO", produto_nome=db_produto.nome)
    db.add(log)
    db.commit()

    return db_produto

# 6. Deletar um produto existente
@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    db_produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    nome_produto = db_produto.nome
    db.delete(db_produto)
    db.commit()

    log = models.HistoricoMovimentacao(acao="DELETADO", produto_nome=nome_produto)
    db.add(log)
    db.commit()

    return {"detail": "Produto deletado com sucesso!"}