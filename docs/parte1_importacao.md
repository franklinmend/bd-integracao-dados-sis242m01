# Parte 1 — Implantação e importação

## Escopo e status

Esta documentação registra as correções estáticas preparadas para a Etapa 1. A importação integral e a conferência contra a planilha ainda dependem da identificação do bloco adicional de colunas da aba `pedido_compra`. Não declarar a carga como concluída até executar o procedimento descrito abaixo.

## Arquivos da etapa

- `sql/01_ddl_enunciado.sql`: DDL original recebido, preservado.
- `sql/01_ddl_postgres.sql`: versão corrigida para PostgreSQL.
- `sql/01_ddl_mysql.sql`: versão corrigida para MySQL.
- `scripts/importar.py`: importador com configuração por variáveis de ambiente, validação prévia das abas, conversão de datas e contagem real de inserções.

## Erros identificados no DDL

1. `entradas_mercadoria` usa `ordem_compra` na chave primária sem declarar a coluna.
2. `produtos_filial` não tem vírgula antes da constraint de chave primária.
3. A chave de `produtos_filial` usa `idproduto`, mas a coluna foi declarada como `produto_id`.
4. A chave de `fornecedor` usa `idproduto`, coluna inexistente nessa tabela.
5. `idforncedor` deve ser padronizado como `idfornecedor`.
6. `decricao` deve ser padronizado como `descricao`.
7. `idfonecedor` deve ser padronizado como `idfornecedor`.
8. O identificador do fornecedor é textual (ex.: `F1`), portanto os campos relacionados não podem ser inteiros; foram padronizados como `VARCHAR(25)`.

A falha de sintaxe observada ao executar o DDL original foi reportada em `produtos_filial`, na definição da constraint, devido à vírgula ausente. Os demais itens acima são inconsistências estruturais identificadas pela leitura do DDL; não devem ser apresentados como erros efetivamente retornados pelo PostgreSQL se não foram executados individualmente.

## Problemas do importador original

- As instruções apontavam para `public`; confirmar que o DDL e o banco de destino usam o mesmo schema.
- Credenciais estavam fixas no código. A nova versão lê variáveis de ambiente.
- `df.iloc[:, :12]` descartava silenciosamente colunas adicionais da aba `pedido_compra`.
- `int(fornecedor_id)` não aceita códigos textuais como `F1`.
- A conversão de datas tratava os valores apenas como serial Excel e podia falhar para datas já interpretadas pelo pandas.
- O `rollback()` dentro do laço podia desfazer inserções anteriores da mesma etapa.
- Os totais impressos eram o tamanho do DataFrame, não o número efetivamente inserido; a nova versão usa `cursor.rowcount`.

## Estrutura da planilha e pendência de mapeamento

As abas esperadas pelo script são:

| Aba | Colunas esperadas pelo mapeamento |
| --- | --- |
| fornecedor | `idfornecedor`, `razao_social` |
| produtos_filial | `filial_id`, `idproduto`, `descricao`, `estoque`, `preco_unitario`, `preco_compra`, `preco_venda`, `idfornecedor` |
| pedido_compra | `pedido_id`, `data_pedido`, `item`, `produto_id`, `descricao_produto`, `ordem_compra`, `qtde_pedida`, `filial_id`, `data_entrega`, `qtde_entregue`, `preco_compra`, `fornecedor_id` |
| entradas_mercadoria | `data_entrada`, `nro_nfe`, `item`, `produto_id`, `descricao_produto`, `ordem_compra`, `qtde_recebida`, `filial_id`, `custo_unitario` |
| venda | `venda_id`, `data_emissao`, `horariomov`, `produto_id`, `qtde_vendida`, `valor_unitario`, `filial_id`, `item`, `unidade_medida` |

**Atenção:** a aba `pedido_compra` foi identificada com 23 colunas, enquanto o mapeamento original usa somente 12. Há dados preenchidos em colunas adicionais. A nova versão do importador não as elimina: ela interrompe a execução e informa quais colunas precisam ser analisadas. Não foi possível atribuir significado confiável a esse bloco adicional nesta revisão. É necessário inspecionar a planilha, identificar se é uma segunda tabela/bloco ou continuação dos pedidos e só então decidir como importar.

## Como executar

Instale as dependências:

```bash
pip install pandas openpyxl psycopg2-binary
```

Configure as variáveis de ambiente (exemplo para PowerShell):

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="postgres"
$env:DB_USER="postgres"
$env:DB_PASSWORD="SUA_SENHA"
$env:DB_SCHEMA="public"
python scripts/importar.py
```

Coloque a planilha em `dados/base_teste.xlsx` ou configure `ARQUIVO_EXCEL`. Não versionar senhas reais.

O script valida todas as abas antes de abrir a conexão e executa a carga em uma única transação. Se ocorrer erro, a transação é revertida. Registros já existentes conforme as chaves de conflito são ignorados e contabilizados separadamente.

## Conferência obrigatória após a carga

Executar no PostgreSQL:

```sql
SELECT 'fornecedor' AS tabela, COUNT(*) AS total FROM public.fornecedor
UNION ALL
SELECT 'produtos_filial', COUNT(*) FROM public.produtos_filial
UNION ALL
SELECT 'pedido_compra', COUNT(*) FROM public.pedido_compra
UNION ALL
SELECT 'entradas_mercadoria', COUNT(*) FROM public.entradas_mercadoria
UNION ALL
SELECT 'venda', COUNT(*) FROM public.venda
ORDER BY tabela;
```

Comparar cada contagem com o número de linhas válidas da respectiva aba, descontando apenas duplicidades justificadas pelas chaves primárias. Registrar aqui os resultados reais da execução:

| Tabela | Linhas na planilha | Inseridas nesta execução | Total no banco após carga |
| --- | ---: | ---: | ---: |
| fornecedor | A conferir | Não executado | Não conferido |
| produtos_filial | A conferir | Não executado | Não conferido |
| pedido_compra | A conferir | Não executado | Não conferido |
| entradas_mercadoria | A conferir | Não executado | Não conferido |
| venda | A conferir | Não executado | Não conferido |

## Resultado desta revisão

- DDL PostgreSQL e MySQL revisados estaticamente.
- Importador reestruturado para evitar perda silenciosa de colunas, credenciais hardcoded e contagens incorretas.
- **Importação não executada nesta revisão.**
- **Contagens finais não verificadas.**
- **Mapeamento das colunas adicionais de `pedido_compra` pendente.**

Não marcar a Etapa 1 como concluída antes de resolver o mapeamento adicional, executar a carga e preencher a tabela de conferência com resultados reais.
