-- PARTE 3 — TRANSFORMAÇÕES DE DADOS (PostgreSQL)
-- Informe :data_inicio e :data_fim no cliente SQL (fim exclusivo).

-- 1 e 2) Concatenar código/descrição e formatar data DD/MM/YYYY.
SELECT pc.produto_id || ' - ' || COALESCE(pc.descricao_produto,p.descricao,'') AS produto,
       pc.qtde_pedida AS qtde_requisitada,
       TO_CHAR(pc.data_pedido,'DD/MM/YYYY') AS data_solicitacao
FROM integracao_dados.pedido_compra pc
LEFT JOIN integracao_dados.produtos_filial p
  ON p.filial_id=pc.filial_id AND p.produto_id=pc.produto_id
WHERE pc.data_pedido >= CAST(:data_inicio AS date)
  AND pc.data_pedido < CAST(:data_fim AS date)
ORDER BY pc.data_pedido,pc.produto_id;

-- 3) "Mais de 10 vezes" foi interpretado como mais de 10 linhas/itens de pedido
-- distintos por produto no período, e não como quantidade pedida > 10.
SELECT pc.produto_id || ' - ' || COALESCE(MAX(pc.descricao_produto),MAX(p.descricao),'') AS produto,
       COUNT(*) AS vezes_requisitado,
       SUM(COALESCE(pc.qtde_pedida,0)) AS quantidade_total_requisitada,
       TO_CHAR(MIN(pc.data_pedido),'DD/MM/YYYY') AS primeira_solicitacao,
       TO_CHAR(MAX(pc.data_pedido),'DD/MM/YYYY') AS ultima_solicitacao
FROM integracao_dados.pedido_compra pc
LEFT JOIN integracao_dados.produtos_filial p
  ON p.filial_id=pc.filial_id AND p.produto_id=pc.produto_id
WHERE pc.data_pedido >= CAST(:data_inicio AS date)
  AND pc.data_pedido < CAST(:data_fim AS date)
GROUP BY pc.produto_id
HAVING COUNT(*) > 10
ORDER BY vezes_requisitado DESC,pc.produto_id;

-- 4) A tabela fornecedor gera o ID numérico por IDENTITY/AUTO_INCREMENT.
-- Esta trigger resolve o código textual (F1, F2...) e preenche a FK numérica
-- na tabela produtos_filial; não cria um fornecedor novo sem cadastro.
CREATE OR REPLACE FUNCTION integracao_dados.fn_vincular_fornecedor_produto()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.codigo_fornecedor IS NULL OR btrim(NEW.codigo_fornecedor)='' THEN
        NEW.idfornecedor := NULL;
        RETURN NEW;
    END IF;
    SELECT f.idfornecedor INTO NEW.idfornecedor
    FROM integracao_dados.fornecedor f
    WHERE f.codigo_fornecedor=btrim(NEW.codigo_fornecedor);
    IF NEW.idfornecedor IS NULL THEN
        RAISE EXCEPTION 'Fornecedor % não cadastrado',NEW.codigo_fornecedor;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_vincular_fornecedor_produto ON integracao_dados.produtos_filial;
CREATE TRIGGER trg_vincular_fornecedor_produto
BEFORE INSERT OR UPDATE OF codigo_fornecedor ON integracao_dados.produtos_filial
FOR EACH ROW EXECUTE FUNCTION integracao_dados.fn_vincular_fornecedor_produto();
