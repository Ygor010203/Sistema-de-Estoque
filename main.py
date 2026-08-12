import io
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx

# (Certifique-se de importar seus módulos locais corretamente, ex: models, database, etc.)
import models
from database import SessionLocal, engine

# Cria as tabelas se não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuração de CORS (Permite requisições do frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Variáveis do Pipefy (Substitua ou mantenha puxando do seu .env)
import os
from dotenv import load_dotenv
load_dotenv()

PIPE_ID = os.getenv("PIPE_ID")
PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")


@app.get("/pipefy/finalizados/")
async def buscar_cards_finalizados(db: Session = Depends(get_db)):
    if not PIPE_ID or not PIPEFY_TOKEN:
        raise HTTPException(status_code=500, detail="Configurações do Pipefy ausentes no .env")

    query = """
    {
      pipe(id: %s) {
        phases {
          name
          cards {
            edges {
              node {
                id
                title
                fields {
                  name
                  value
                }
              }
            }
          }
        }
      }
    }
    """ % PIPE_ID

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://app.pipefy.com/graphql",
            json={"query": query},
            headers={
                "Authorization": f"Bearer {PIPEFY_TOKEN}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Erro ao comunicar com a API do Pipefy")

    dados = response.json()
    if "errors" in dados:
        raise HTTPException(status_code=400, detail=str(dados["errors"]))

    fases = dados.get("data", {}).get("pipe", {}).get("phases", [])
    
    cards_processados = []
    for fase in fases:
        if fase["name"].lower() == "finalizado":
            for edge in fase["cards"]["edges"]:
                node = edge["node"]
                
                item_info = {
                    "card_id": str(node.get("id", "-")),
                    "produto_nome": "-",
                    "prestador": "-",
                    "cidade": "-",
                    "nf": "-",
                    "quantidade": 0
                }
                
                for field in node["fields"]:
                    fn = field["name"].strip().upper()
                    val = field.get("value")
                    
                    if not val:
                        continue
                        
                    if fn in ["RASTREADOR", "EQUIPAMENTO", "PRODUTO"]:
                        item_info["produto_nome"] = val
                    elif fn in ["QUANTIDADE", "QTD"]:
                        item_info["quantidade"] = int(val) if val.isdigit() else 0
                    elif "PRESTADOR" in fn:
                        item_info["prestador"] = val
                    elif "CIDADE" in fn or "ESTADO" in fn:
                        item_info["cidade"] = val
                    elif "NOTA" in fn or "NF" in fn:
                        item_info["nf"] = val

                cards_processados.append(item_info)

    return {"cards_finalizados": cards_processados}


@app.get("/pipefy/exportar-excel/")
async def exportar_excel(db: Session = Depends(get_db)):
    if not PIPE_ID or not PIPEFY_TOKEN:
        raise HTTPException(status_code=500, detail="Configurações do Pipefy ausentes no .env")

    query = """
    {
      pipe(id: %s) {
        phases {
          name
          cards {
            edges {
              node {
                id
                title
                fields {
                  name
                  value
                }
              }
            }
          }
        }
      }
    }
    """ % PIPE_ID

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://app.pipefy.com/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {PIPEFY_TOKEN}", "Content-Type": "application/json"}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Erro ao comunicar com a API do Pipefy")

    dados = response.json()
    fases = dados.get("data", {}).get("pipe", {}).get("phases", [])
    
    lista_dados = []
    for fase in fases:
        if fase["name"].lower() == "finalizado":
            for edge in fase["cards"]["edges"]:
                node = edge["node"]
                item = {
                    "Card ID": str(node.get("id", "-")),
                    "Produto": "-",
                    "Prestador": "-",
                    "Cidade": "-",
                    "NF": "-",
                    "Qtd Saída": 0
                }
                for field in node["fields"]:
                    fn = field["name"].strip().upper()
                    val = field.get("value")
                    if not val:
                        continue
                    if fn in ["RASTREADOR", "EQUIPAMENTO", "PRODUTO"]:
                        item["Produto"] = val
                    elif fn in ["QUANTIDADE", "QTD"]:
                        item["Qtd Saída"] = int(val) if val.isdigit() else 0
                    elif "PRESTADOR" in fn:
                        item["Prestador"] = val
                    elif "CIDADE" in fn or "ESTADO" in fn:
                        item["Cidade"] = val
                    elif "NOTA" in fn or "NF" in fn:
                        item["NF"] = val
                lista_dados.append(item)

    df = pd.DataFrame(lista_dados)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Saídas Pipefy')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=saidas_pipefy.xlsx"}
    )


# --- ROTAS DE PRODUTOS (Mantenha as suas rotas de produtos /produtos/ aqui embaixo) ---
@app.get("/produtos/")
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(models.Produto).all()

@app.post("/produtos/")
def criar_produto(produto: dict, db: Session = Depends(get_db)):
    # Adapte conforme o seu modelo de produto atual
    novo_produto = models.Produto(**produto)
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto

@app.delete("/produtos/{produto_id}")
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    db.delete(produto)
    db.commit()
    return {"message": "Deletado com sucesso"}