-- DDL corrigido para MySQL 8.0+
CREATE DATABASE IF NOT EXISTS integracao_dados;
USE integracao_dados;

CREATE TABLE fornecedor (
    idfornecedor BIGINT NOT NULL AUTO_INCREMENT,
    codigo_fornecedor VARCHAR(25) NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    CONSTRAINT fornecedor_pkey PRIMARY KEY (idfornecedor),
    CONSTRAINT fornecedor_codigo_uk UNIQUE (codigo_fornecedor)
) ENGINE=InnoDB;

CREATE TABLE produtos_filial (
    filial_id INT NOT NULL,
    produto_id VARCHAR(255) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    estoque DECIMAL(14,4) NOT NULL DEFAULT 0,
    preco_unitario DECIMAL(14,4) NOT NULL DEFAULT 0,
    preco_compra DECIMAL(14,4) NOT NULL DEFAULT 0,
    preco_venda DECIMAL(14,4) NOT NULL DEFAULT 0,
    codigo_fornecedor VARCHAR(25),
    idfornecedor BIGINT,
    CONSTRAINT produtos_filial_pkey PRIMARY KEY (filial_id, produto_id),
    CONSTRAINT produtos_filial_fornecedor_fk
      FOREIGN KEY (idfornecedor) REFERENCES fornecedor(idfornecedor)
) ENGINE=InnoDB;

CREATE TABLE pedido_compra (
    pedido_id DECIMAL(18,2) NOT NULL DEFAULT 0,
    data_pedido DATE,
    item DECIMAL(12,2) NOT NULL DEFAULT 0,
    produto_id VARCHAR(25) NOT NULL DEFAULT '0',
    descricao_produto VARCHAR(255),
    ordem_compra DECIMAL(18,2) NOT NULL DEFAULT 0,
    qtde_pedida DECIMAL(14,4),
    filial_id INT,
    data_entrega DATE,
    qtde_entregue DECIMAL(14,4) NOT NULL DEFAULT 0,
    qtde_pendente DECIMAL(14,4) NOT NULL DEFAULT 0,
    preco_compra DECIMAL(14,4) DEFAULT 0,
    fornecedor_id BIGINT,
    CONSTRAINT pedido_compra_pkey PRIMARY KEY (pedido_id, produto_id, item),
    CONSTRAINT pedido_compra_fornecedor_fk
      FOREIGN KEY (fornecedor_id) REFERENCES fornecedor(idfornecedor)
) ENGINE=InnoDB;

CREATE TABLE entradas_mercadoria (
    ordem_compra DECIMAL(18,2) NOT NULL DEFAULT 0,
    data_entrada DATE,
    nro_nfe VARCHAR(255) NOT NULL,
    item DECIMAL(12,2) NOT NULL DEFAULT 0,
    produto_id VARCHAR(25) NOT NULL DEFAULT '0',
    descricao_produto VARCHAR(255),
    qtde_recebida DECIMAL(14,4),
    filial_id INT,
    custo_unitario DECIMAL(14,4) NOT NULL DEFAULT 0,
    CONSTRAINT entradas_mercadoria_pkey
      PRIMARY KEY (ordem_compra, item, produto_id, nro_nfe)
) ENGINE=InnoDB;

CREATE TABLE venda (
    venda_id BIGINT NOT NULL,
    data_emissao DATE NOT NULL,
    horariomov VARCHAR(8) NOT NULL DEFAULT '00:00:00',
    produto_id VARCHAR(25) NOT NULL DEFAULT '',
    qtde_vendida DECIMAL(14,4),
    valor_unitario DECIMAL(14,4) NOT NULL DEFAULT 0,
    filial_id BIGINT NOT NULL DEFAULT 1,
    item INT NOT NULL DEFAULT 0,
    unidade_medida VARCHAR(3),
    CONSTRAINT pk_consumo PRIMARY KEY
      (filial_id, venda_id, data_emissao, produto_id, item, horariomov)
) ENGINE=InnoDB;

DELIMITER $$
CREATE TRIGGER trg_vincular_fornecedor_produto
BEFORE INSERT ON produtos_filial
FOR EACH ROW
BEGIN
    DECLARE v_id BIGINT DEFAULT NULL;
    IF NEW.codigo_fornecedor IS NULL OR TRIM(NEW.codigo_fornecedor) = '' THEN
        SET NEW.idfornecedor = NULL;
    ELSE
        SELECT MAX(idfornecedor) INTO v_id
          FROM fornecedor
         WHERE codigo_fornecedor = TRIM(NEW.codigo_fornecedor);
        IF v_id IS NULL THEN
            SIGNAL SQLSTATE '45000'
              SET MESSAGE_TEXT = 'Código de fornecedor não cadastrado';
        END IF;
        SET NEW.idfornecedor = v_id;
    END IF;
END$$

CREATE TRIGGER trg_vincular_fornecedor_produto_update
BEFORE UPDATE ON produtos_filial
FOR EACH ROW
BEGIN
    DECLARE v_id BIGINT DEFAULT NULL;
    IF NEW.codigo_fornecedor IS NULL OR TRIM(NEW.codigo_fornecedor) = '' THEN
        SET NEW.idfornecedor = NULL;
    ELSE
        SELECT MAX(idfornecedor) INTO v_id
          FROM fornecedor
         WHERE codigo_fornecedor = TRIM(NEW.codigo_fornecedor);
        IF v_id IS NULL THEN
            SIGNAL SQLSTATE '45000'
              SET MESSAGE_TEXT = 'Código de fornecedor não cadastrado';
        END IF;
        SET NEW.idfornecedor = v_id;
    END IF;
END$$
DELIMITER ;
