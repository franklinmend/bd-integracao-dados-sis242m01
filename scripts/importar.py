"""Importação da planilha base_teste.xlsx para PostgreSQL.
Configuração: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA.
ARQUIVO_EXCEL permite alterar o caminho da planilha.

A aba pedido_compra contém colunas extras preenchidas que ainda precisam ser
identificadas. Por segurança, o script interrompe a carga em vez de descartá-las.
"""
import os
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2 import sql

ARQUIVO = Path(os.getenv("ARQUIVO_EXCEL", "dados/base_teste.xlsx"))
SCHEMA = os.getenv("DB_SCHEMA", "integracao_dados")
DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

COLUNAS = {
    "fornecedor": ["idfornecedor", "razao_social"],
    "produtos_filial": ["filial_id", "idproduto", "descricao", "estoque",
        "preco_unitario", "preco_compra", "preco_venda", "idfornecedor"],
    "pedido_compra": ["pedido_id", "data_pedido", "item", "produto_id",
        "descricao_produto", "ordem_compra", "qtde_pedida", "filial_id",
        "data_entrega", "qtde_entregue", "preco_compra", "fornecedor_id"],
    "entradas_mercadoria": ["data_entrada", "nro_nfe", "item", "produto_id",
        "descricao_produto", "ordem_compra", "qtde_recebida", "filial_id",
        "custo_unitario"],
    "venda": ["venda_id", "data_emissao", "horariomov", "produto_id",
        "qtde_vendida", "valor_unitario", "filial_id", "item", "unidade_medida"],
}

def vazio(v):
    return pd.isna(v)

def texto(v, default=None):
    if vazio(v):
        return default
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()

def numero(v, default=None, tipo=float):
    return default if vazio(v) else tipo(v)

def data_sql(v):
    if vazio(v):
        return None
    dt = pd.to_datetime(v, errors="raise", dayfirst=True)
    return dt.date()

def ler_planilhas():
    if not ARQUIVO.is_file():
        raise FileNotFoundError(f"Planilha não encontrada: {ARQUIVO}")
    dados = {}
    for aba, obrigatorias in COLUNAS.items():
        df = pd.read_excel(ARQUIVO, sheet_name=aba)
        df.columns = [str(c).strip() for c in df.columns]
        faltantes = [c for c in obrigatorias if c not in df.columns]
        if faltantes:
            raise ValueError(f"{aba}: colunas ausentes: {faltantes}")
        dados[aba] = df

    extras = [c for c in dados["pedido_compra"].columns
              if c not in COLUNAS["pedido_compra"]
              and dados["pedido_compra"][c].notna().any()]
    if extras:
        quantidades = {c: int(dados["pedido_compra"][c].notna().sum()) for c in extras}
        raise ValueError(
            "A aba pedido_compra possui colunas extras preenchidas "
            f"({quantidades}). A carga foi cancelada para evitar perda de dados. "
            "Identifique o bloco adicional e acrescente seu mapeamento."
        )
    return dados

def montar_registros(aba, df, mapa_fornecedor):
    for idx, r in df.iterrows():
        try:
            if aba == "fornecedor":
                yield (texto(r["idfornecedor"]), texto(r["razao_social"]))
            elif aba == "produtos_filial":
                yield (
                    numero(r["filial_id"], None, int), texto(r["idproduto"]),
                    texto(r["descricao"]), numero(r["estoque"], 0),
                    numero(r["preco_unitario"], 0), numero(r["preco_compra"], 0),
                    numero(r["preco_venda"], 0), texto(r["idfornecedor"])
                )
            elif aba == "pedido_compra":
                cod = texto(r["fornecedor_id"])
                fornecedor_id = mapa_fornecedor.get(cod) if cod else None
                pedida = numero(r["qtde_pedida"], None)
                entregue = numero(r["qtde_entregue"], 0)
                pendente = max(pedida - entregue, 0) if pedida is not None else 0
                yield (
                    numero(r["pedido_id"], 0), data_sql(r["data_pedido"]),
                    numero(r["item"], 0), texto(r["produto_id"], "0"),
                    texto(r["descricao_produto"]), numero(r["ordem_compra"], 0),
                    pedida, numero(r["filial_id"], None, int),
                    data_sql(r["data_entrega"]), entregue, pendente,
                    numero(r["preco_compra"], 0), fornecedor_id
                )
            elif aba == "entradas_mercadoria":
                yield (
                    numero(r["ordem_compra"], 0), data_sql(r["data_entrada"]),
                    texto(r["nro_nfe"]), numero(r["item"], 0),
                    texto(r["produto_id"], "0"), texto(r["descricao_produto"]),
                    numero(r["qtde_recebida"], None),
                    numero(r["filial_id"], None, int),
                    numero(r["custo_unitario"], 0)
                )
            elif aba == "venda":
                yield (
                    numero(r["venda_id"], None, int), data_sql(r["data_emissao"]),
                    texto(r["horariomov"], "00:00:00"),
                    texto(r["produto_id"], ""), numero(r["qtde_vendida"], None),
                    numero(r["valor_unitario"], 0), numero(r["filial_id"], 1, int),
                    numero(r["item"], 0, int), texto(r["unidade_medida"])
                )
        except Exception as exc:
            raise ValueError(f"{aba}, linha Excel {idx + 2}: {exc}") from exc

def inserir(cur, tabela, colunas, chave, registros):
    comando = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING").format(
        sql.Identifier(SCHEMA), sql.Identifier(tabela),
        sql.SQL(", ").join(map(sql.Identifier, colunas)),
        sql.SQL(", ").join(sql.Placeholder() for _ in colunas),
        sql.SQL(", ").join(map(sql.Identifier, chave))
    )
    inseridos = ignorados = 0
    for reg in registros:
        cur.execute(comando, reg)
        if cur.rowcount == 1:
            inseridos += 1
        else:
            ignorados += 1
    return inseridos, ignorados

def main():
    planilhas = ler_planilhas()
    print("Abas validadas:")
    for aba, df in planilhas.items():
        print(f"  {aba}: {len(df)} linhas")

    if not DB["password"]:
        raise ValueError("Defina DB_PASSWORD no ambiente antes de executar.")

    cfg = [
        ("fornecedor", ["codigo_fornecedor", "razao_social"], ["codigo_fornecedor"],
         "fornecedor", ["idfornecedor"]),
        ("produtos_filial", ["filial_id", "produto_id", "descricao", "estoque",
         "preco_unitario", "preco_compra", "preco_venda", "codigo_fornecedor"],
         ["filial_id", "produto_id"], "produtos_filial",
         ["filial_id", "idproduto", "descricao", "estoque", "preco_unitario",
          "preco_compra", "preco_venda", "idfornecedor"]),
        ("pedido_compra", ["pedido_id", "data_pedido", "item", "produto_id",
         "descricao_produto", "ordem_compra", "qtde_pedida", "filial_id",
         "data_entrega", "qtde_entregue", "qtde_pendente", "preco_compra",
         "fornecedor_id"], ["pedido_id", "produto_id", "item"],
         "pedido_compra", COLUNAS["pedido_compra"]),
        ("entradas_mercadoria", ["ordem_compra", "data_entrada", "nro_nfe",
         "item", "produto_id", "descricao_produto", "qtde_recebida",
         "filial_id", "custo_unitario"],
         ["ordem_compra", "item", "produto_id", "nro_nfe"],
         "entradas_mercadoria", COLUNAS["entradas_mercadoria"]),
        ("venda", COLUNAS["venda"],
         ["filial_id", "venda_id", "data_emissao", "produto_id", "item", "horariomov"],
         "venda", COLUNAS["venda"]),
    ]

    with psycopg2.connect(**DB) as conn:
        with conn.cursor() as cur:
            # Cadastra fornecedores antes dos produtos e pedidos.
            fornecedores = inserir(
                cur, "fornecedor", ["codigo_fornecedor", "razao_social"],
                ["codigo_fornecedor"],
                ((texto(r["idfornecedor"]), texto(r["razao_social"]))
                 for _, r in planilhas["fornecedor"].iterrows())
            )
            cur.execute(sql.SQL("SELECT codigo_fornecedor, idfornecedor FROM {}.fornecedor").format(
                sql.Identifier(SCHEMA)))
            mapa = {codigo: ident for codigo, ident in cur.fetchall()}

            totais = {"fornecedor": fornecedores}
            for aba, colunas_db, chave, tabela, colunas_xlsx in cfg[1:]:
                # Converter registros de acordo com a estrutura de destino.
                regs = montar_registros(aba, planilhas[aba], mapa)
                totais[aba] = inserir(cur, tabela, colunas_db, chave, regs)

    print("\nResultado:")
    for tabela, (ok, ignorados) in totais.items():
        print(f"{tabela}: {ok} inseridos; {ignorados} já existentes/duplicados")
    print("Carga finalizada.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
