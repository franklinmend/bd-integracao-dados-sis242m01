"""
Importa a planilha base_teste.xlsx para PostgreSQL.

Configuração por variáveis de ambiente:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
  DB_SCHEMA (opcional; padrão: public)
  ARQUIVO_EXCEL (opcional; padrão: dados/base_teste.xlsx)

O script valida todas as abas antes de iniciar a transação. Se encontrar
colunas adicionais preenchidas em pedido_compra, interrompe a execução:
essas colunas precisam ter seu significado identificado antes de qualquer
mapeamento ou descarte.
"""
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2 import sql


ARQUIVO = Path(os.getenv("ARQUIVO_EXCEL", "dados/base_teste.xlsx"))
SCHEMA = os.getenv("DB_SCHEMA", "public")
DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

COLUNAS = {
    "fornecedor": ["idfornecedor", "razao_social"],
    "produtos_filial": [
        "filial_id", "idproduto", "descricao", "estoque", "preco_unitario",
        "preco_compra", "preco_venda", "idfornecedor",
    ],
    "pedido_compra": [
        "pedido_id", "data_pedido", "item", "produto_id", "descricao_produto",
        "ordem_compra", "qtde_pedida", "filial_id", "data_entrega",
        "qtde_entregue", "preco_compra", "fornecedor_id",
    ],
    "entradas_mercadoria": [
        "data_entrada", "nro_nfe", "item", "produto_id", "descricao_produto",
        "ordem_compra", "qtde_recebida", "filial_id", "custo_unitario",
    ],
    "venda": [
        "venda_id", "data_emissao", "horariomov", "produto_id",
        "qtde_vendida", "valor_unitario", "filial_id", "item", "unidade_medida",
    ],
}


def nulo(valor):
    return pd.isna(valor)


def texto(valor, padrao=None):
    if nulo(valor):
        return padrao
    # Evita transformar códigos numéricos lidos como float em strings com .0.
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def numero(valor, padrao=None, conversor=float):
    if nulo(valor):
        return padrao
    return conversor(valor)


def data_sql(valor):
    if nulo(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.date() if isinstance(valor, (pd.Timestamp, datetime)) else valor
    # Excel serial date; mantém compatibilidade com planilhas que armazenam
    # datas como número, mas também aceita strings reconhecidas pelo pandas.
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return (pd.Timestamp("1899-12-30") + pd.to_timedelta(valor, unit="D")).date()
    convertido = pd.to_datetime(valor, errors="raise", dayfirst=True)
    return convertido.date()


def ler_planilhas():
    if not ARQUIVO.is_file():
        raise FileNotFoundError(
            f"Planilha não encontrada: {ARQUIVO}. Coloque-a em dados/base_teste.xlsx "
            "ou defina ARQUIVO_EXCEL."
        )

    planilhas = {}
    for aba, obrigatorias in COLUNAS.items():
        df = pd.read_excel(ARQUIVO, sheet_name=aba)
        df.columns = [str(c).strip() for c in df.columns]
        ausentes = [c for c in obrigatorias if c not in df.columns]
        if ausentes:
            raise ValueError(f"Aba '{aba}': colunas obrigatórias ausentes: {ausentes}")
        planilhas[aba] = df

    # A planilha recebida tem colunas extras preenchidas na aba pedido_compra.
    # Não truncar silenciosamente: identificar e resolver o layout antes da carga.
    df_pedido = planilhas["pedido_compra"]
    extras = [c for c in df_pedido.columns if c not in COLUNAS["pedido_compra"]]
    extras_preenchidas = [
        c for c in extras if df_pedido[c].notna().any()
    ]
    if extras_preenchidas:
        detalhes = {
            c: int(df_pedido[c].notna().sum()) for c in extras_preenchidas
        }
        raise ValueError(
            "Aba 'pedido_compra' contém colunas adicionais com dados "
            f"({detalhes}). A carga foi cancelada para não descartar nem "
            "atribuir significado incorreto a esses valores. Identifique o "
            "layout dessas colunas e ajuste o mapeamento antes de importar."
        )

    return planilhas


def registros(aba, df):
    for indice, r in df.iterrows():
        try:
            if aba == "fornecedor":
                yield (
                    texto(r["idfornecedor"]),
                    texto(r["razao_social"]),
                )
            elif aba == "produtos_filial":
                yield (
                    numero(r["filial_id"], None, int),
                    texto(r["idproduto"]),
                    texto(r["descricao"]),
                    numero(r["estoque"], 0),
                    numero(r["preco_unitario"], 0),
                    numero(r["preco_compra"], 0),
                    numero(r["preco_venda"], 0),
                    texto(r["idfornecedor"]),
                )
            elif aba == "pedido_compra":
                pedida = numero(r["qtde_pedida"], None)
                entregue = numero(r["qtde_entregue"], 0)
                pendente = (pedida - entregue) if pedida is not None else None
                yield (
                    numero(r["pedido_id"], 0),
                    data_sql(r["data_pedido"]),
                    numero(r["item"], 0),
                    texto(r["produto_id"], "0"),
                    texto(r["descricao_produto"]),
                    numero(r["ordem_compra"], 0),
                    pedida,
                    numero(r["filial_id"], None, int),
                    data_sql(r["data_entrega"]),
                    entregue,
                    pendente if pendente is not None else 0,
                    numero(r["preco_compra"], 0),
                    texto(r["fornecedor_id"]),
                )
            elif aba == "entradas_mercadoria":
                yield (
                    data_sql(r["data_entrada"]),
                    texto(r["nro_nfe"]),
                    numero(r["item"], 0),
                    texto(r["produto_id"], "0"),
                    texto(r["descricao_produto"]),
                    numero(r["ordem_compra"], 0),
                    numero(r["qtde_recebida"], None),
                    numero(r["filial_id"], None, int),
                    numero(r["custo_unitario"], 0),
                )
            elif aba == "venda":
                horario = texto(r["horariomov"], "00:00:00")
                yield (
                    numero(r["venda_id"], None, int),
                    data_sql(r["data_emissao"]),
                    horario,
                    texto(r["produto_id"], ""),
                    numero(r["qtde_vendida"], None),
                    numero(r["valor_unitario"], 0),
                    numero(r["filial_id"], 1, int),
                    numero(r["item"], 0, int),
                    texto(r["unidade_medida"]),
                )
        except Exception as exc:
            raise ValueError(f"Aba '{aba}', linha Excel {indice + 2}: {exc}") from exc


def inserir(cur, schema, tabela, colunas, conflito, dados):
    comando = sql.SQL("""
        INSERT INTO {}.{} ({})
        VALUES ({})
        ON CONFLICT ({}) DO NOTHING
    """).format(
        sql.Identifier(schema),
        sql.Identifier(tabela),
        sql.SQL(", ").join(map(sql.Identifier, colunas)),
        sql.SQL(", ").join(sql.Placeholder() for _ in colunas),
        sql.SQL(", ").join(map(sql.Identifier, conflito)),
    )
    inseridos = 0
    ignorados = 0
    for registro in dados:
        cur.execute(comando, registro)
        if cur.rowcount == 1:
            inseridos += 1
        else:
            ignorados += 1
    return inseridos, ignorados


def main():
    planilhas = ler_planilhas()
    print("Validação das abas concluída:")
    for aba, df in planilhas.items():
        print(f"  {aba}: {len(df)} linhas")

    config_ausente = [k for k in ("host", "dbname", "user") if not DB[k]]
    if config_ausente or not DB["password"]:
        raise ValueError(
            "Configure DB_HOST, DB_NAME, DB_USER e DB_PASSWORD antes de executar."
        )

    mapeamentos = [
        ("fornecedor", ["idfornecedor", "razao_social"], ["idfornecedor"]),
        ("produtos_filial",
         ["filial_id", "produto_id", "descricao", "estoque", "preco_unitario",
          "preco_compra", "preco_venda", "idfornecedor"],
         ["filial_id", "produto_id"]),
        ("pedido_compra",
         ["pedido_id", "data_pedido", "item", "produto_id", "descricao_produto",
          "ordem_compra", "qtde_pedida", "filial_id", "data_entrega",
          "qtde_entregue", "qtde_pendente", "preco_compra", "fornecedor_id"],
         ["pedido_id", "produto_id", "item"]),
        ("entradas_mercadoria",
         ["data_entrada", "nro_nfe", "item", "produto_id", "descricao_produto",
          "ordem_compra", "qtde_recebida", "filial_id", "custo_unitario"],
         ["ordem_compra", "item", "produto_id", "nro_nfe"]),
        ("venda",
         ["venda_id", "data_emissao", "horariomov", "produto_id", "qtde_vendida",
          "valor_unitario", "filial_id", "item", "unidade_medida"],
         ["filial_id", "venda_id", "data_emissao", "produto_id", "item", "horariomov"]),
    ]

    print("\nConectando ao PostgreSQL...")
    with psycopg2.connect(**DB) as conn:
        with conn.cursor() as cur:
            totais = {}
            for tabela, colunas, conflito in mapeamentos:
                totais[tabela] = inserir(
                    cur, SCHEMA, tabela, colunas, conflito,
                    registros(tabela, planilhas[tabela])
                )
        # O context manager confirma a transação somente se todas as abas
        # forem importadas; qualquer exceção provoca rollback integral.
    print("\nResumo da importação:")
    for tabela, (inseridos, ignorados) in totais.items():
        print(f"  {tabela}: {inseridos} inseridos; {ignorados} já existentes/duplicados")
    print("Importação concluída.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
