/* =====================================================================
   Central de Ar Ltda. — 01_complemento.sql
   Rodar DEPOIS de 00_schema_reconstruido.sql.
   Idempotente: pode ser executado mais de uma vez (CREATE OR ALTER).

   Conteúdo:
     a) PEDIDO.percentual_comissao (comissão pode variar em cada pedido)
        + usp_CadastrarPedido ajustada
     b) Procedures de listagem (usp_Listar*)
     c) usp_CadastrarItemPedido, usp_Atualizar* e usp_Excluir*
     d) Procedures de relatório (usp_Consultar*)
     e) Trigger de estoque em ITEM_PEDIDO

   Códigos de erro: 50001–50013 são os das procedures originais
   (reaproveitados quando a validação é a mesma); novos a partir de 50014.

   Valor de uma linha de item (usado em todos os totais), já com desconto:
       ROUND(quantidade * preco_unitario * (100 - desconto) / 100, 2)
   Comissão de uma linha: ROUND(valor_da_linha * PEDIDO.percentual_comissao / 100, 2)
   ===================================================================== */

USE CentralDeAr;
GO

/* =====================================================================
   a) Comissão por pedido
   ===================================================================== */

IF COL_LENGTH('PEDIDO', 'percentual_comissao') IS NULL
    ALTER TABLE PEDIDO ADD percentual_comissao DECIMAL(5,2) NULL;
GO

-- Migração de estrutura: pedidos que já existiam antes da coluna
-- recebem a comissão fixa do vendedor (não afeta nada se não houver pedidos).
UPDATE p
   SET p.percentual_comissao = v.comissao_fixa
  FROM PEDIDO p
  JOIN VENDEDOR v ON v.id_vendedor = p.fk_vendedor
 WHERE p.percentual_comissao IS NULL;
GO

IF EXISTS (SELECT 1 FROM sys.columns
            WHERE object_id = OBJECT_ID('PEDIDO')
              AND name = 'percentual_comissao'
              AND is_nullable = 1)
    ALTER TABLE PEDIDO ALTER COLUMN percentual_comissao DECIMAL(5,2) NOT NULL;
GO

IF OBJECT_ID('CK_PEDIDO_PERCENTUAL_COMISSAO', 'C') IS NULL
    ALTER TABLE PEDIDO ADD CONSTRAINT CK_PEDIDO_PERCENTUAL_COMISSAO
        CHECK (percentual_comissao >= 0 AND percentual_comissao <= 100);
GO

/* Novos parâmetros ficam no fim (opcionais), para não quebrar chamadas antigas.
   @percentual_comissao NULL -> usa VENDEDOR.comissao_fixa
   @data_pedido NULL         -> data/hora atual                                  */
CREATE OR ALTER PROCEDURE usp_CadastrarPedido
    @fk_cliente INT,
    @fk_vendedor INT,
    @id_pedido INT OUTPUT,
    @percentual_comissao DECIMAL(5,2) = NULL,
    @data_pedido DATETIME2 = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Verificar se o cliente existe
        IF NOT EXISTS (SELECT 1 FROM CLIENTE WHERE id_cliente = @fk_cliente)
        BEGIN
            THROW 50011, 'Cliente nao encontrado.', 1;
        END;

        -- Verificar se o vendedor existe
        IF NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @fk_vendedor)
        BEGIN
            THROW 50012, 'Vendedor nao encontrado.', 1;
        END;

        -- Verificar se o vendedor atende a regiao do cliente
        IF NOT EXISTS (
            SELECT 1
            FROM CLIENTE c
            INNER JOIN REGIAO r ON c.fk_regiao = r.id_regiao
            WHERE c.id_cliente = @fk_cliente
              AND r.fk_vendedor = @fk_vendedor
        )
        BEGIN
            THROW 50013,
                'O vendedor informado nao e responsavel pela regiao do cliente.',
                1;
        END;

        -- Comissao do pedido: se nao informada, usa a comissao fixa do vendedor
        IF @percentual_comissao IS NULL
        BEGIN
            SELECT @percentual_comissao = comissao_fixa
            FROM VENDEDOR
            WHERE id_vendedor = @fk_vendedor;
        END;

        IF @percentual_comissao < 0 OR @percentual_comissao > 100
        BEGIN
            THROW 50014, 'O percentual de comissao deve estar entre 0 e 100.', 1;
        END;

        -- Inserir pedido
        INSERT INTO PEDIDO (fk_cliente, fk_vendedor, data_pedido, percentual_comissao)
        VALUES (@fk_cliente, @fk_vendedor, ISNULL(@data_pedido, SYSDATETIME()), @percentual_comissao);

        -- Recuperar ID gerado
        SET @id_pedido = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Pedido cadastrado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   e) Trigger de estoque (fica antes das procedures de item por clareza)
   Itens removidos (deleted) devolvem estoque; itens incluídos (inserted) baixam.
   Funciona para INSERT, UPDATE (inclusive troca de quantidade) e DELETE,
   e para várias linhas de uma vez.
   ===================================================================== */
CREATE OR ALTER TRIGGER trg_ITEM_PEDIDO_Estoque
ON ITEM_PEDIDO
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Variacao liquida de estoque por produto
    DECLARE @movimento TABLE (
        fk_produto INT PRIMARY KEY,
        variacao   DECIMAL(13,3) NOT NULL
    );

    INSERT INTO @movimento (fk_produto, variacao)
    SELECT fk_produto, SUM(qtd)
    FROM (
        SELECT fk_produto, quantidade AS qtd FROM deleted
        UNION ALL
        SELECT fk_produto, -quantidade      FROM inserted
    ) AS m
    GROUP BY fk_produto
    HAVING SUM(qtd) <> 0;

    IF NOT EXISTS (SELECT 1 FROM @movimento)
        RETURN;

    -- Estoque nao pode ficar negativo: mensagem clara com o produto
    DECLARE @msg NVARCHAR(2048);

    SELECT TOP (1)
        @msg = CONCAT(
            N'Estoque insuficiente para o produto "', p.descricao,
            N'" (codigo ', p.id_produto, N'). Disponivel: ',
            FORMAT(p.estoque, N'0.###'), N'; necessario: ',
            FORMAT(-m.variacao, N'0.###'), N'.')
    FROM PRODUTO p WITH (UPDLOCK, HOLDLOCK)
    INNER JOIN @movimento m ON m.fk_produto = p.id_produto
    WHERE p.estoque + m.variacao < 0
    ORDER BY p.id_produto;

    IF @msg IS NOT NULL
        THROW 50022, @msg, 1;

    UPDATE p
       SET p.estoque = p.estoque + m.variacao
      FROM PRODUTO p
     INNER JOIN @movimento m ON m.fk_produto = p.id_produto;
END;
GO

/* =====================================================================
   b) Listagens
   ===================================================================== */

CREATE OR ALTER PROCEDURE usp_ListarVendedores
AS
BEGIN
    SET NOCOUNT ON;

    SELECT id_vendedor, nome, telefone, email, comissao_fixa
    FROM VENDEDOR
    ORDER BY nome;
END;
GO

CREATE OR ALTER PROCEDURE usp_ListarRegioes
AS
BEGIN
    SET NOCOUNT ON;

    SELECT r.id_regiao,
           r.nome,
           r.descricao,
           r.fk_vendedor AS id_vendedor,
           v.nome        AS vendedor,
           (SELECT COUNT(*) FROM CLIENTE c WHERE c.fk_regiao = r.id_regiao) AS qtd_clientes
    FROM REGIAO r
    INNER JOIN VENDEDOR v ON v.id_vendedor = r.fk_vendedor
    ORDER BY r.nome;
END;
GO

CREATE OR ALTER PROCEDURE usp_ListarClientes
AS
BEGIN
    SET NOCOUNT ON;

    SELECT c.id_cliente,
           c.nome,
           c.cpf_cnpj,
           c.telefone,
           c.email,
           c.endereco,
           c.fk_regiao   AS id_regiao,
           r.nome        AS regiao,
           v.id_vendedor,
           v.nome        AS vendedor,
           v.comissao_fixa
    FROM CLIENTE c
    INNER JOIN REGIAO r   ON r.id_regiao   = c.fk_regiao
    INNER JOIN VENDEDOR v ON v.id_vendedor = r.fk_vendedor
    ORDER BY c.nome;
END;
GO

CREATE OR ALTER PROCEDURE usp_ListarProdutos
AS
BEGIN
    SET NOCOUNT ON;

    SELECT id_produto, descricao, preco, estoque
    FROM PRODUTO
    ORDER BY descricao;
END;
GO

CREATE OR ALTER PROCEDURE usp_ListarPedidos
AS
BEGIN
    SET NOCOUNT ON;

    SELECT p.id_pedido,
           p.data_pedido,
           p.fk_cliente  AS id_cliente,
           c.nome        AS cliente,
           p.fk_vendedor AS id_vendedor,
           v.nome        AS vendedor,
           r.nome        AS regiao,
           p.percentual_comissao,
           COUNT(i.fk_produto) AS qtd_itens,
           CAST(ISNULL(SUM(x.valor_item), 0)    AS DECIMAL(14,2)) AS total_pedido,
           CAST(ISNULL(SUM(x.comissao_item), 0) AS DECIMAL(14,2)) AS valor_comissao
    FROM PEDIDO p
    INNER JOIN CLIENTE c  ON c.id_cliente  = p.fk_cliente
    INNER JOIN REGIAO r   ON r.id_regiao   = c.fk_regiao
    INNER JOIN VENDEDOR v ON v.id_vendedor = p.fk_vendedor
    LEFT  JOIN ITEM_PEDIDO i ON i.fk_pedido = p.id_pedido
    CROSS APPLY (
        SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
    ) AS vi
    CROSS APPLY (
        SELECT vi.valor_item AS valor_item,
               ROUND(vi.valor_item * p.percentual_comissao / 100, 2) AS comissao_item
    ) AS x
    GROUP BY p.id_pedido, p.data_pedido, p.fk_cliente, c.nome, p.fk_vendedor,
             v.nome, r.nome, p.percentual_comissao
    ORDER BY p.data_pedido DESC, p.id_pedido DESC;
END;
GO

CREATE OR ALTER PROCEDURE usp_ListarItensPedido
    @id_pedido INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM PEDIDO WHERE id_pedido = @id_pedido)
        BEGIN
            THROW 50015, 'Pedido nao encontrado.', 1;
        END;

        SELECT i.fk_produto AS id_produto,
               pr.descricao AS produto,
               i.quantidade,
               i.preco_unitario,
               i.desconto,
               CAST(ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2)
                    AS DECIMAL(14,2)) AS valor_total
        FROM ITEM_PEDIDO i
        INNER JOIN PRODUTO pr ON pr.id_produto = i.fk_produto
        WHERE i.fk_pedido = @id_pedido
        ORDER BY pr.descricao;

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Itens de pedido
   O estoque é ajustado pela trigger trg_ITEM_PEDIDO_Estoque.
   ===================================================================== */

/* @preco_unitario NULL -> usa o preço atual do produto */
CREATE OR ALTER PROCEDURE usp_CadastrarItemPedido
    @fk_pedido INT,
    @fk_produto INT,
    @quantidade DECIMAL(10,3),
    @preco_unitario DECIMAL(12,2) = NULL,
    @desconto DECIMAL(5,2) = 0
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM PEDIDO WHERE id_pedido = @fk_pedido)
        BEGIN
            THROW 50015, 'Pedido nao encontrado.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM PRODUTO WHERE id_produto = @fk_produto)
        BEGIN
            THROW 50016, 'Produto nao encontrado.', 1;
        END;

        IF @quantidade IS NULL OR @quantidade <= 0
        BEGIN
            THROW 50017, 'A quantidade deve ser maior que zero.', 1;
        END;

        SET @desconto = ISNULL(@desconto, 0);

        IF @desconto < 0 OR @desconto > 100
        BEGIN
            THROW 50018, 'O desconto deve estar entre 0 e 100.', 1;
        END;

        -- Preco nao informado: usa o preco atual do produto
        IF @preco_unitario IS NULL
        BEGIN
            SELECT @preco_unitario = preco
            FROM PRODUTO
            WHERE id_produto = @fk_produto;
        END;

        IF @preco_unitario < 0
        BEGIN
            THROW 50019, 'O preco unitario nao pode ser negativo.', 1;
        END;

        IF EXISTS (SELECT 1 FROM ITEM_PEDIDO
                    WHERE fk_pedido = @fk_pedido AND fk_produto = @fk_produto)
        BEGIN
            THROW 50020, 'Este produto ja esta no pedido. Altere a quantidade do item existente.', 1;
        END;

        INSERT INTO ITEM_PEDIDO (fk_pedido, fk_produto, quantidade, preco_unitario, desconto)
        VALUES (@fk_pedido, @fk_produto, @quantidade, @preco_unitario, @desconto);

        PRINT 'Item incluido no pedido com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* @preco_unitario e @desconto NULL -> mantêm o valor atual do item */
CREATE OR ALTER PROCEDURE usp_AtualizarItemPedido
    @fk_pedido INT,
    @fk_produto INT,
    @quantidade DECIMAL(10,3),
    @preco_unitario DECIMAL(12,2) = NULL,
    @desconto DECIMAL(5,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM ITEM_PEDIDO
                        WHERE fk_pedido = @fk_pedido AND fk_produto = @fk_produto)
        BEGIN
            THROW 50021, 'Item do pedido nao encontrado.', 1;
        END;

        IF @quantidade IS NULL OR @quantidade <= 0
        BEGIN
            THROW 50017, 'A quantidade deve ser maior que zero.', 1;
        END;

        IF @desconto < 0 OR @desconto > 100
        BEGIN
            THROW 50018, 'O desconto deve estar entre 0 e 100.', 1;
        END;

        IF @preco_unitario < 0
        BEGIN
            THROW 50019, 'O preco unitario nao pode ser negativo.', 1;
        END;

        UPDATE ITEM_PEDIDO
           SET quantidade     = @quantidade,
               preco_unitario = ISNULL(@preco_unitario, preco_unitario),
               desconto       = ISNULL(@desconto, desconto)
         WHERE fk_pedido = @fk_pedido
           AND fk_produto = @fk_produto;

        PRINT 'Item do pedido atualizado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE usp_ExcluirItemPedido
    @fk_pedido INT,
    @fk_produto INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM ITEM_PEDIDO
                        WHERE fk_pedido = @fk_pedido AND fk_produto = @fk_produto)
        BEGIN
            THROW 50021, 'Item do pedido nao encontrado.', 1;
        END;

        DELETE FROM ITEM_PEDIDO
         WHERE fk_pedido = @fk_pedido
           AND fk_produto = @fk_produto;

        PRINT 'Item removido do pedido com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Atualizar / Excluir — Vendedor
   ===================================================================== */

CREATE OR ALTER PROCEDURE usp_AtualizarVendedor
    @id_vendedor INT,
    @nome NVARCHAR(150),
    @comissao_fixa DECIMAL(5,2),
    @telefone VARCHAR(20) = NULL,
    @email NVARCHAR(254) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @id_vendedor)
        BEGIN
            THROW 50004, 'Vendedor nao encontrado.', 1;
        END;

        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50001, 'O nome do vendedor e obrigatorio.', 1;
        END;

        IF @comissao_fixa IS NULL OR @comissao_fixa < 0 OR @comissao_fixa > 100
        BEGIN
            THROW 50002, 'A comissao deve estar entre 0 e 100.', 1;
        END;

        -- Pedidos ja feitos guardam o proprio percentual: nao sao afetados.
        UPDATE VENDEDOR
           SET nome          = @nome,
               telefone      = @telefone,
               email         = @email,
               comissao_fixa = @comissao_fixa
         WHERE id_vendedor = @id_vendedor;

        PRINT 'Vendedor atualizado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE usp_ExcluirVendedor
    @id_vendedor INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        DECLARE @qtd INT, @msg NVARCHAR(2048);

        IF NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @id_vendedor)
        BEGIN
            THROW 50004, 'Vendedor nao encontrado.', 1;
        END;

        SELECT @qtd = COUNT(*) FROM REGIAO WHERE fk_vendedor = @id_vendedor;
        IF @qtd > 0
        BEGIN
            SET @msg = CONCAT(N'Nao e possivel excluir: o vendedor e responsavel por ', @qtd,
                              N' regiao(oes). Passe as regioes para outro vendedor antes.');
            THROW 50023, @msg, 1;
        END;

        SELECT @qtd = COUNT(*) FROM PEDIDO WHERE fk_vendedor = @id_vendedor;
        IF @qtd > 0
        BEGIN
            SET @msg = CONCAT(N'Nao e possivel excluir: o vendedor possui ', @qtd,
                              N' pedido(s) registrado(s).');
            THROW 50024, @msg, 1;
        END;

        DELETE FROM VENDEDOR WHERE id_vendedor = @id_vendedor;

        PRINT 'Vendedor excluido com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Atualizar / Excluir — Regiao
   ===================================================================== */

/* Trocar o vendedor da região vale para pedidos futuros;
   pedidos antigos continuam com o vendedor que fez a venda. */
CREATE OR ALTER PROCEDURE usp_AtualizarRegiao
    @id_regiao INT,
    @nome NVARCHAR(100),
    @fk_vendedor INT,
    @descricao NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM REGIAO WHERE id_regiao = @id_regiao)
        BEGIN
            THROW 50007, 'Regiao nao encontrada.', 1;
        END;

        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50003, 'O nome da regiao e obrigatorio.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @fk_vendedor)
        BEGIN
            THROW 50004, 'Vendedor nao encontrado.', 1;
        END;

        UPDATE REGIAO
           SET nome        = @nome,
               descricao   = @descricao,
               fk_vendedor = @fk_vendedor
         WHERE id_regiao = @id_regiao;

        PRINT 'Regiao atualizada com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE usp_ExcluirRegiao
    @id_regiao INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        DECLARE @qtd INT, @msg NVARCHAR(2048);

        IF NOT EXISTS (SELECT 1 FROM REGIAO WHERE id_regiao = @id_regiao)
        BEGIN
            THROW 50007, 'Regiao nao encontrada.', 1;
        END;

        SELECT @qtd = COUNT(*) FROM CLIENTE WHERE fk_regiao = @id_regiao;
        IF @qtd > 0
        BEGIN
            SET @msg = CONCAT(N'Nao e possivel excluir: a regiao possui ', @qtd,
                              N' cliente(s). Mude os clientes de regiao antes.');
            THROW 50025, @msg, 1;
        END;

        DELETE FROM REGIAO WHERE id_regiao = @id_regiao;

        PRINT 'Regiao excluida com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Atualizar / Excluir — Cliente
   ===================================================================== */

CREATE OR ALTER PROCEDURE usp_AtualizarCliente
    @id_cliente INT,
    @nome NVARCHAR(150),
    @cpf_cnpj VARCHAR(14),
    @fk_regiao INT,
    @telefone VARCHAR(20) = NULL,
    @email NVARCHAR(254) = NULL,
    @endereco NVARCHAR(250) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM CLIENTE WHERE id_cliente = @id_cliente)
        BEGIN
            THROW 50011, 'Cliente nao encontrado.', 1;
        END;

        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50005, 'O nome do cliente e obrigatorio.', 1;
        END;

        IF NULLIF(LTRIM(RTRIM(@cpf_cnpj)), '') IS NULL
        BEGIN
            THROW 50006, 'O CPF/CNPJ e obrigatorio.', 1;
        END;

        IF EXISTS (SELECT 1 FROM CLIENTE
                    WHERE cpf_cnpj = @cpf_cnpj AND id_cliente <> @id_cliente)
        BEGIN
            THROW 50028, 'Ja existe outro cliente com este CPF/CNPJ.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM REGIAO WHERE id_regiao = @fk_regiao)
        BEGIN
            THROW 50007, 'Regiao nao encontrada.', 1;
        END;

        UPDATE CLIENTE
           SET nome      = @nome,
               cpf_cnpj  = @cpf_cnpj,
               telefone  = @telefone,
               email     = @email,
               endereco  = @endereco,
               fk_regiao = @fk_regiao
         WHERE id_cliente = @id_cliente;

        PRINT 'Cliente atualizado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE usp_ExcluirCliente
    @id_cliente INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        DECLARE @qtd INT, @msg NVARCHAR(2048);

        IF NOT EXISTS (SELECT 1 FROM CLIENTE WHERE id_cliente = @id_cliente)
        BEGIN
            THROW 50011, 'Cliente nao encontrado.', 1;
        END;

        SELECT @qtd = COUNT(*) FROM PEDIDO WHERE fk_cliente = @id_cliente;
        IF @qtd > 0
        BEGIN
            SET @msg = CONCAT(N'Nao e possivel excluir: o cliente possui ', @qtd,
                              N' pedido(s) registrado(s).');
            THROW 50026, @msg, 1;
        END;

        DELETE FROM CLIENTE WHERE id_cliente = @id_cliente;

        PRINT 'Cliente excluido com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Atualizar / Excluir — Produto
   ===================================================================== */

CREATE OR ALTER PROCEDURE usp_AtualizarProduto
    @id_produto INT,
    @descricao NVARCHAR(250),
    @preco DECIMAL(12,2),
    @estoque DECIMAL(10,3)
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM PRODUTO WHERE id_produto = @id_produto)
        BEGIN
            THROW 50016, 'Produto nao encontrado.', 1;
        END;

        IF NULLIF(LTRIM(RTRIM(@descricao)), '') IS NULL
        BEGIN
            THROW 50008, 'A descricao do produto e obrigatoria.', 1;
        END;

        IF @preco IS NULL OR @preco < 0
        BEGIN
            THROW 50009, 'O preco nao pode ser negativo.', 1;
        END;

        IF @estoque IS NULL OR @estoque < 0
        BEGIN
            THROW 50010, 'O estoque nao pode ser negativo.', 1;
        END;

        -- Itens ja vendidos guardam o proprio preco_unitario: nao sao afetados.
        UPDATE PRODUTO
           SET descricao = @descricao,
               preco     = @preco,
               estoque   = @estoque
         WHERE id_produto = @id_produto;

        PRINT 'Produto atualizado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE usp_ExcluirProduto
    @id_produto INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        DECLARE @qtd INT, @msg NVARCHAR(2048);

        IF NOT EXISTS (SELECT 1 FROM PRODUTO WHERE id_produto = @id_produto)
        BEGIN
            THROW 50016, 'Produto nao encontrado.', 1;
        END;

        SELECT @qtd = COUNT(*) FROM ITEM_PEDIDO WHERE fk_produto = @id_produto;
        IF @qtd > 0
        BEGIN
            SET @msg = CONCAT(N'Nao e possivel excluir: o produto aparece em ', @qtd,
                              N' item(ns) de pedido.');
            THROW 50027, @msg, 1;
        END;

        DELETE FROM PRODUTO WHERE id_produto = @id_produto;

        PRINT 'Produto excluido com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   c) Atualizar / Excluir — Pedido
   ===================================================================== */

/* @data_pedido NULL -> mantém a data atual do pedido.
   A regra "vendedor atende a região do cliente" só é conferida quando o
   cliente ou o vendedor mudam (a região pode ter trocado de vendedor depois
   da venda, e o pedido antigo continua válido). */
CREATE OR ALTER PROCEDURE usp_AtualizarPedido
    @id_pedido INT,
    @fk_cliente INT,
    @fk_vendedor INT,
    @percentual_comissao DECIMAL(5,2),
    @data_pedido DATETIME2 = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM PEDIDO WHERE id_pedido = @id_pedido)
        BEGIN
            THROW 50015, 'Pedido nao encontrado.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM CLIENTE WHERE id_cliente = @fk_cliente)
        BEGIN
            THROW 50011, 'Cliente nao encontrado.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @fk_vendedor)
        BEGIN
            THROW 50012, 'Vendedor nao encontrado.', 1;
        END;

        IF @percentual_comissao IS NULL OR @percentual_comissao < 0 OR @percentual_comissao > 100
        BEGIN
            THROW 50014, 'O percentual de comissao deve estar entre 0 e 100.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM PEDIDO
                        WHERE id_pedido = @id_pedido
                          AND fk_cliente = @fk_cliente
                          AND fk_vendedor = @fk_vendedor)
           AND NOT EXISTS (
                SELECT 1
                FROM CLIENTE c
                INNER JOIN REGIAO r ON c.fk_regiao = r.id_regiao
                WHERE c.id_cliente = @fk_cliente
                  AND r.fk_vendedor = @fk_vendedor)
        BEGIN
            THROW 50013,
                'O vendedor informado nao e responsavel pela regiao do cliente.',
                1;
        END;

        UPDATE PEDIDO
           SET fk_cliente          = @fk_cliente,
               fk_vendedor         = @fk_vendedor,
               percentual_comissao = @percentual_comissao,
               data_pedido         = ISNULL(@data_pedido, data_pedido)
         WHERE id_pedido = @id_pedido;

        PRINT 'Pedido atualizado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

/* Apaga os itens e o pedido numa transação; a trigger devolve o estoque. */
CREATE OR ALTER PROCEDURE usp_ExcluirPedido
    @id_pedido INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF NOT EXISTS (SELECT 1 FROM PEDIDO WHERE id_pedido = @id_pedido)
        BEGIN
            THROW 50015, 'Pedido nao encontrado.', 1;
        END;

        BEGIN TRANSACTION;

            DELETE FROM ITEM_PEDIDO WHERE fk_pedido = @id_pedido;
            DELETE FROM PEDIDO      WHERE id_pedido = @id_pedido;

        COMMIT TRANSACTION;

        PRINT 'Pedido excluido com sucesso (estoque dos itens devolvido)!';

    END TRY

    BEGIN CATCH
        IF XACT_STATE() <> 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

/* =====================================================================
   d) Relatórios (total vendido = soma dos itens já com desconto)
   ===================================================================== */

-- Total vendido por região (região do cliente). Mostra também regiões sem vendas.
CREATE OR ALTER PROCEDURE usp_ConsultarVendasPorRegiao
AS
BEGIN
    SET NOCOUNT ON;

    SELECT r.id_regiao,
           r.nome AS regiao,
           v.nome AS vendedor_responsavel,
           COUNT(DISTINCT p.id_pedido) AS qtd_pedidos,
           CAST(ISNULL(SUM(x.valor_item), 0) AS DECIMAL(14,2)) AS total_vendido
    FROM REGIAO r
    INNER JOIN VENDEDOR v    ON v.id_vendedor = r.fk_vendedor
    LEFT  JOIN CLIENTE c     ON c.fk_regiao   = r.id_regiao
    LEFT  JOIN PEDIDO p      ON p.fk_cliente  = c.id_cliente
    LEFT  JOIN ITEM_PEDIDO i ON i.fk_pedido   = p.id_pedido
    CROSS APPLY (
        SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
    ) AS x
    GROUP BY r.id_regiao, r.nome, v.nome
    ORDER BY total_vendido DESC, r.nome;
END;
GO

-- Total vendido por cliente. Mostra também clientes sem compras.
CREATE OR ALTER PROCEDURE usp_ConsultarVendasPorCliente
AS
BEGIN
    SET NOCOUNT ON;

    SELECT c.id_cliente,
           c.nome AS cliente,
           c.cpf_cnpj,
           r.nome AS regiao,
           COUNT(DISTINCT p.id_pedido) AS qtd_pedidos,
           CAST(ISNULL(SUM(x.valor_item), 0) AS DECIMAL(14,2)) AS total_vendido
    FROM CLIENTE c
    INNER JOIN REGIAO r      ON r.id_regiao  = c.fk_regiao
    LEFT  JOIN PEDIDO p      ON p.fk_cliente = c.id_cliente
    LEFT  JOIN ITEM_PEDIDO i ON i.fk_pedido  = p.id_pedido
    CROSS APPLY (
        SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
    ) AS x
    GROUP BY c.id_cliente, c.nome, c.cpf_cnpj, r.nome
    ORDER BY total_vendido DESC, c.nome;
END;
GO

-- Total vendido por vendedor (vendedor que fez o pedido) e comissão total.
CREATE OR ALTER PROCEDURE usp_ConsultarVendasPorVendedor
AS
BEGIN
    SET NOCOUNT ON;

    SELECT v.id_vendedor,
           v.nome AS vendedor,
           COUNT(DISTINCT p.id_pedido) AS qtd_pedidos,
           CAST(ISNULL(SUM(x.valor_item), 0)    AS DECIMAL(14,2)) AS total_vendido,
           CAST(ISNULL(SUM(x.comissao_item), 0) AS DECIMAL(14,2)) AS total_comissao
    FROM VENDEDOR v
    LEFT JOIN PEDIDO p      ON p.fk_vendedor = v.id_vendedor
    LEFT JOIN ITEM_PEDIDO i ON i.fk_pedido   = p.id_pedido
    CROSS APPLY (
        SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
    ) AS vi
    CROSS APPLY (
        SELECT vi.valor_item AS valor_item,
               ROUND(vi.valor_item * p.percentual_comissao / 100, 2) AS comissao_item
    ) AS x
    GROUP BY v.id_vendedor, v.nome
    ORDER BY total_vendido DESC, v.nome;
END;
GO

-- Clientes de uma região (região obrigatória).
CREATE OR ALTER PROCEDURE usp_ConsultarClientesPorRegiao
    @id_regiao INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF @id_regiao IS NULL
        BEGIN
            THROW 50029, 'Informe a regiao.', 1;
        END;

        IF NOT EXISTS (SELECT 1 FROM REGIAO WHERE id_regiao = @id_regiao)
        BEGIN
            THROW 50007, 'Regiao nao encontrada.', 1;
        END;

        SELECT c.id_cliente,
               c.nome AS cliente,
               c.cpf_cnpj,
               c.telefone,
               c.email,
               c.endereco,
               COUNT(DISTINCT p.id_pedido) AS qtd_pedidos,
               CAST(ISNULL(SUM(x.valor_item), 0) AS DECIMAL(14,2)) AS total_vendido
        FROM CLIENTE c
        LEFT JOIN PEDIDO p      ON p.fk_cliente = c.id_cliente
        LEFT JOIN ITEM_PEDIDO i ON i.fk_pedido  = p.id_pedido
        CROSS APPLY (
            SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
        ) AS x
        WHERE c.fk_regiao = @id_regiao
        GROUP BY c.id_cliente, c.nome, c.cpf_cnpj, c.telefone, c.email, c.endereco
        ORDER BY c.nome;

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

-- Total vendido por produto. Mostra também produtos sem vendas.
CREATE OR ALTER PROCEDURE usp_ConsultarVendasPorProduto
AS
BEGIN
    SET NOCOUNT ON;

    SELECT pr.id_produto,
           pr.descricao AS produto,
           COUNT(DISTINCT i.fk_pedido) AS qtd_pedidos,
           CAST(ISNULL(SUM(i.quantidade), 0) AS DECIMAL(13,3)) AS quantidade_vendida,
           CAST(ISNULL(SUM(x.valor_item), 0) AS DECIMAL(14,2)) AS total_vendido
    FROM PRODUTO pr
    LEFT JOIN ITEM_PEDIDO i ON i.fk_produto = pr.id_produto
    CROSS APPLY (
        SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
    ) AS x
    GROUP BY pr.id_produto, pr.descricao
    ORDER BY total_vendido DESC, pr.descricao;
END;
GO

/* Extrato de comissão de cada vendedor SEPARADO POR PRODUTO.
   A comissão é calculada item a item com o percentual gravado em cada pedido,
   então o mesmo produto pode ter percentuais diferentes em pedidos diferentes;
   percentual_efetivo = comissão / total vendido daquele produto.
   @id_vendedor NULL -> todos os vendedores. */
CREATE OR ALTER PROCEDURE usp_ConsultarComissaoPorVendedor
    @id_vendedor INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        IF @id_vendedor IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM VENDEDOR WHERE id_vendedor = @id_vendedor)
        BEGIN
            THROW 50004, 'Vendedor nao encontrado.', 1;
        END;

        SELECT v.id_vendedor,
               v.nome        AS vendedor,
               pr.id_produto,
               pr.descricao  AS produto,
               COUNT(DISTINCT p.id_pedido) AS qtd_pedidos,
               CAST(SUM(i.quantidade)      AS DECIMAL(13,3)) AS quantidade_vendida,
               CAST(SUM(x.valor_item)      AS DECIMAL(14,2)) AS total_vendido,
               CAST(SUM(x.comissao_item)   AS DECIMAL(14,2)) AS valor_comissao,
               CAST(CASE WHEN SUM(x.valor_item) = 0 THEN 0
                         ELSE SUM(x.comissao_item) * 100 / SUM(x.valor_item) END
                    AS DECIMAL(5,2)) AS percentual_efetivo
        FROM VENDEDOR v
        INNER JOIN PEDIDO p      ON p.fk_vendedor = v.id_vendedor
        INNER JOIN ITEM_PEDIDO i ON i.fk_pedido   = p.id_pedido
        INNER JOIN PRODUTO pr    ON pr.id_produto = i.fk_produto
        CROSS APPLY (
            SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS valor_item
        ) AS vi
        CROSS APPLY (
            SELECT vi.valor_item AS valor_item,
                   ROUND(vi.valor_item * p.percentual_comissao / 100, 2) AS comissao_item
        ) AS x
        WHERE @id_vendedor IS NULL OR v.id_vendedor = @id_vendedor
        GROUP BY v.id_vendedor, v.nome, pr.id_produto, pr.descricao
        ORDER BY v.nome, valor_comissao DESC, pr.descricao;

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

PRINT 'Complemento aplicado com sucesso.';
GO
