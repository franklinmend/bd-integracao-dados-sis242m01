# Parte 4 — Estratégia de validação com o cliente

## Objetivo da reunião

Validar com o cliente a consistência e a interpretação dos dados de vendas de fevereiro de 2025 antes de considerar os números aptos para relatórios e decisões. As consultas de apoio estão em `sql/04_validacao.sql`.

## 1. Pontos que serão validados

1. **Período e abrangência:** confirmar que o recorte considera 01/02/2025 a 28/02/2025, inclusive, e quais filiais e sistemas de origem estão incluídos.
2. **Volume de vendas:** confrontar quantidade de registros, unidades vendidas e valor bruto calculado com o relatório do PDV/ERP.
3. **Regra financeira:** confirmar se o valor esperado é quantidade vendida multiplicada pelo valor unitário e se existem descontos, cancelamentos, devoluções ou impostos que devam ser considerados.
4. **Cadastro de produtos:** validar códigos sem correspondência no cadastro da filial e descrições ausentes/divergentes.
5. **Pedidos e recebimentos:** comparar quantidade pedida, recebida e pendente por ordem de compra, produto e item.
6. **Fornecedores:** confirmar que o código textual da planilha (por exemplo, F1) aponta para um único identificador numérico no cadastro.
7. **Datas e horários:** confirmar fuso/horário operacional, datas de emissão e eventuais registros fora do período.
8. **Exceções:** revisar ordens de compra sem número válido, registros sem vínculo e valores/quantidades negativos.

## 2. Técnicas para garantir exatidão e precisão

- **Reconciliação de totais:** comparar totalizadores do banco com os relatórios oficiais da origem, usando o mesmo período, filial e regra de cálculo.
- **Conferência por amostragem:** selecionar vendas e pedidos e rastrear o registro até a origem (documento fiscal, pedido e nota de entrada).
- **Integridade referencial:** usar chaves primárias/estrangeiras e consultas anti-join para localizar produtos e fornecedores sem correspondência.
- **Validação de domínio:** verificar datas, quantidades e valores negativos, nulos inesperados e códigos fora do padrão.
- **Reconciliação pedido × entrada:** somar as entradas por ordem de compra, produto e item antes de comparar com o pedido, evitando duplicação causada por múltiplas notas.
- **Rastreabilidade:** guardar a planilha original sem alteração, versão do script, data da carga, logs e resultado das consultas.
- **Critério de aceite:** registrar divergências, responsável pela confirmação, justificativa e decisão do cliente antes de corrigir dados.

## 3. Consultas preparadas para a reunião

| Consulta | O que demonstra |
| --- | --- |
| 1 | Quantidade de linhas, unidades e valor total vendido em fevereiro/2025. |
| 2 | Evolução diária para comparar com o fechamento do PDV. |
| 3 | Vendas de fevereiro com produto ausente do cadastro da mesma filial. |
| 4 | Diferenças entre quantidade pendente registrada e recalculada. |
| 5 | Entradas sem pedido correspondente pela chave de ligação. |
| 6 | Pedidos com `ordem_compra = 0`, que exigem confirmação da origem. |
| 7 | Códigos de fornecedor sem cadastro correspondente. |
| 8 | Quantidades ou valores negativos. |
| 9 | Pedidos com identificador numérico de fornecedor sem FK válida. |

## 4. Achados preliminares no banco consultado

A consulta foi executada no schema `integracao_dados` disponível durante a preparação. Ela retornou 14 linhas de venda em fevereiro de 2025, totalizando 173,22 unidades e R$ 14.093,17 (quantidade × valor unitário). O banco continha 20 fornecedores, 20 produtos por filial, 20 pedidos de compra, 20 entradas de mercadoria e 33 vendas no total.

Também foram observados dois pedidos com `ordem_compra = 0`. Esse valor dificulta a ligação com a tabela de entradas e precisa ser confirmado com o cliente. A listagem de vendas do mês contém seis códigos de produto que não aparecem no catálogo carregado: P22, P23, P24, P25, P26 e P27. A consulta 3 identifica esses casos para análise. Esses resultados descrevem o estado atual do banco consultado, não comprovam que a importação integral da planilha foi concluída.

## 5. Erros e inconsistências a investigar

| Tabela | Problema | Como identificar |
| --- | --- | --- |
| `venda` | Código de produto sem cadastro na mesma filial | Consulta 3 |
| `pedido_compra` | Ordem de compra igual a zero | Consulta 6 |
| `entradas_mercadoria` | Entrada sem pedido correspondente | Consulta 5 |
| `produtos_filial` | Código de fornecedor sem correspondência | Consulta 7 |
| `pedido_compra` | Pendente armazenado diferente do saldo recalculado | Consulta 4 |
| `venda` / `pedido_compra` | Quantidades ou valores negativos | Consulta 8 |
| `pedido_compra` | Identificador de fornecedor sem FK correspondente | Consulta 9 |

As consultas precisam ser executadas após a carga final. A quantidade de inconsistências deve ser registrada a partir dos resultados reais, sem presumir que toda linha retornada seja erro confirmado: alguns casos exigem validação de regra com o cliente.
