-- PARTE 4 — CONSULTAS DE APOIO À VALIDAÇÃO (PostgreSQL)
-- Reunião de validação: fevereiro/2025.

-- 1) Indicadores consolidados do mês.
SELECT COUNT(*) linhas_venda, SUM(qtde_vendida) quantidade_total,
       ROUND(SUM(qtde_vendida*valor_unitario),2) valor_total
FROM integracao_dados.venda
WHERE data_emissao>=DATE '2025-02-01' AND data_emissao<DATE '2025-03-01';

-- 2) Totais por dia para confronto com relatório/PDV.
SELECT data_emissao,COUNT(*) linhas,SUM(qtde_vendida) quantidade,
       ROUND(SUM(qtde_vendida*valor_unitario),2) valor
FROM integracao_dados.venda
WHERE data_emissao>=DATE '2025-02-01' AND data_emissao<DATE '2025-03-01'
GROUP BY data_emissao ORDER BY data_emissao;

-- 3) Vendas do mês cujo produto não está cadastrado na mesma filial.
SELECT v.*
FROM integracao_dados.venda v
LEFT JOIN integracao_dados.produtos_filial p
 ON p.filial_id=v.filial_id AND p.produto_id=v.produto_id
WHERE v.data_emissao>=DATE '2025-02-01' AND v.data_emissao<DATE '2025-03-01'
  AND p.produto_id IS NULL;

-- 4) Diferença entre saldo pendente registrado e saldo recalculado pelas entradas.
WITH recebimentos AS (
 SELECT ordem_compra,produto_id,item,SUM(COALESCE(qtde_recebida,0)) recebida
 FROM integracao_dados.entradas_mercadoria GROUP BY ordem_compra,produto_id,item
)
SELECT pc.ordem_compra,pc.pedido_id,pc.produto_id,pc.item,pc.qtde_pedida,
       COALESCE(r.recebida,0) recebida,pc.qtde_pendente pendente_registrada,
       GREATEST(COALESCE(pc.qtde_pedida,0)-COALESCE(r.recebida,0),0) pendente_calculada
FROM integracao_dados.pedido_compra pc
LEFT JOIN recebimentos r
 ON r.ordem_compra=pc.ordem_compra AND r.produto_id=pc.produto_id AND r.item=pc.item
WHERE ABS(COALESCE(pc.qtde_pendente,0)-
 GREATEST(COALESCE(pc.qtde_pedida,0)-COALESCE(r.recebida,0),0))>0.0001;

-- 5) Entradas sem pedido correspondente (ordem + produto + item).
SELECT e.*
FROM integracao_dados.entradas_mercadoria e
WHERE NOT EXISTS (
 SELECT 1 FROM integracao_dados.pedido_compra pc
 WHERE pc.ordem_compra=e.ordem_compra AND pc.produto_id=e.produto_id AND pc.item=e.item
);

-- 6) Pedidos com ordem_compra igual a zero: vínculo com entradas não confiável.
SELECT pedido_id,produto_id,item,data_pedido,qtde_pedida,fornecedor_id
FROM integracao_dados.pedido_compra WHERE ordem_compra=0;

-- 7) Produtos cujo código de fornecedor não existe no cadastro.
SELECT p.filial_id,p.produto_id,p.codigo_fornecedor
FROM integracao_dados.produtos_filial p
LEFT JOIN integracao_dados.fornecedor f ON f.codigo_fornecedor=p.codigo_fornecedor
WHERE p.codigo_fornecedor IS NOT NULL AND f.idfornecedor IS NULL;

-- 8) Quantidades ou valores negativos.
SELECT 'venda' tabela,produto_id,data_emissao data_registro,qtde_vendida quantidade,
       valor_unitario valor
FROM integracao_dados.venda
WHERE (qtde_vendida<0 OR valor_unitario<0)
 AND data_emissao>=DATE '2025-02-01' AND data_emissao<DATE '2025-03-01'
UNION ALL
SELECT 'pedido_compra',produto_id,data_pedido,qtde_pedida,preco_compra
FROM integracao_dados.pedido_compra
WHERE qtde_pedida<0 OR preco_compra<0;

-- 9) Pedidos com FK de fornecedor sem correspondência.
SELECT pc.*
FROM integracao_dados.pedido_compra pc
LEFT JOIN integracao_dados.fornecedor f ON f.idfornecedor=pc.fornecedor_id
WHERE pc.fornecedor_id IS NOT NULL AND f.idfornecedor IS NULL;
