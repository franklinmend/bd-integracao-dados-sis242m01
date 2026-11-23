-- PARTE 2 — CONSULTAS SQL BÁSICAS (PostgreSQL)
-- 1) Consumo por produto em fevereiro de 2025.
SELECT v.produto_id,
       COALESCE(p.descricao, 'Descrição não cadastrada') AS descricao,
       SUM(v.qtde_vendida) AS quantidade_vendida,
       ROUND(SUM(v.qtde_vendida * v.valor_unitario), 2) AS valor_total
FROM integracao_dados.venda v
LEFT JOIN integracao_dados.produtos_filial p
  ON p.filial_id = v.filial_id AND p.produto_id = v.produto_id
WHERE v.data_emissao >= DATE '2025-02-01'
  AND v.data_emissao < DATE '2025-03-01'
GROUP BY v.produto_id, p.descricao
ORDER BY v.produto_id;

-- 2) Produtos requisitados e ainda não recebidos integralmente.
WITH recebimentos AS (
    SELECT ordem_compra, produto_id, item,
           SUM(COALESCE(qtde_recebida,0)) AS qtde_recebida
    FROM integracao_dados.entradas_mercadoria
    GROUP BY ordem_compra, produto_id, item
)
SELECT pc.ordem_compra, pc.pedido_id, pc.produto_id,
       COALESCE(pc.descricao_produto,p.descricao,'Descrição não cadastrada') produto,
       pc.qtde_pedida, COALESCE(r.qtde_recebida,0) qtde_recebida,
       GREATEST(COALESCE(pc.qtde_pedida,0)-COALESCE(r.qtde_recebida,0),0) qtde_pendente
FROM integracao_dados.pedido_compra pc
LEFT JOIN recebimentos r
  ON r.ordem_compra=pc.ordem_compra AND r.produto_id=pc.produto_id AND r.item=pc.item
LEFT JOIN integracao_dados.produtos_filial p
  ON p.filial_id=pc.filial_id AND p.produto_id=pc.produto_id
WHERE COALESCE(pc.qtde_pedida,0)>COALESCE(r.qtde_recebida,0)
ORDER BY pc.ordem_compra,pc.produto_id,pc.item;
