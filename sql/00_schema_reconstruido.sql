/* =====================================================================
   Central de Ar Ltda. — banco RECONSTRUÍDO a partir do backup incompleto
   (central_ar.bak era a parte 2 de 2 de um backup dividido).

   Recuperado do backup (fiel ao original):
     - 6 tabelas, colunas, PKs, FKs, UNIQUE, CHECKs e DEFAULTs (mesmos nomes)
     - Código completo de 5 procedures: usp_CadastrarVendedor, usp_CadastrarRegiao,
       usp_CadastrarCliente, usp_CadastrarProduto, usp_CadastrarPedido

   NÃO recuperado (só o nome existia no backup) — recriar no 01_complemento.sql:
     usp_CadastrarItemPedido, usp_ConsultarVendasPorRegiao, usp_ConsultarVendasPorCliente,
     usp_ConsultarVendasPorVendedor, usp_ConsultarClientesPorRegiao,
     usp_ConsultarVendasPorProduto, usp_ConsultarComissaoPorVendedor

   Inferido (tamanho exato não estava legível): ITEM_PEDIDO.quantidade DECIMAL(10,3),
   ITEM_PEDIDO.desconto DECIMAL(5,2), PEDIDO.data_pedido DATETIME2,
   PK de ITEM_PEDIDO composta (fk_pedido, fk_produto).
   ===================================================================== */

IF DB_ID('CentralDeAr') IS NULL
    CREATE DATABASE CentralDeAr;
GO
USE CentralDeAr;
GO

CREATE TABLE VENDEDOR (
    id_vendedor    INT IDENTITY(1,1) NOT NULL,
    nome           NVARCHAR(150)     NOT NULL,
    telefone       VARCHAR(20)       NULL,
    email          NVARCHAR(254)     NULL,
    comissao_fixa  DECIMAL(5,2)      NOT NULL,
    CONSTRAINT PK_VENDEDOR PRIMARY KEY (id_vendedor),
    CONSTRAINT CK_VENDEDOR_COMISSAO CHECK (comissao_fixa >= 0 AND comissao_fixa <= 100)
);
GO

CREATE TABLE REGIAO (
    id_regiao    INT IDENTITY(1,1) NOT NULL,
    nome         NVARCHAR(100)     NOT NULL,
    descricao    NVARCHAR(500)     NULL,
    fk_vendedor  INT               NOT NULL,
    CONSTRAINT PK_REGIAO PRIMARY KEY (id_regiao),
    CONSTRAINT FK_REGIAO_VENDEDOR FOREIGN KEY (fk_vendedor) REFERENCES VENDEDOR (id_vendedor)
);
GO

CREATE TABLE CLIENTE (
    id_cliente  INT IDENTITY(1,1) NOT NULL,
    nome        NVARCHAR(150)     NOT NULL,
    cpf_cnpj    VARCHAR(14)       NOT NULL,
    telefone    VARCHAR(20)       NULL,
    email       NVARCHAR(254)     NULL,
    endereco    NVARCHAR(250)     NULL,
    fk_regiao   INT               NOT NULL,
    CONSTRAINT PK_CLIENTE PRIMARY KEY (id_cliente),
    CONSTRAINT UQ_CLIENTE_CPF_CNPJ UNIQUE (cpf_cnpj),
    CONSTRAINT FK_CLIENTE_REGIAO FOREIGN KEY (fk_regiao) REFERENCES REGIAO (id_regiao)
);
GO

CREATE TABLE PRODUTO (
    id_produto  INT IDENTITY(1,1) NOT NULL,
    descricao   NVARCHAR(250)     NOT NULL,
    preco       DECIMAL(12,2)     NOT NULL,
    estoque     DECIMAL(10,3)     NOT NULL,
    CONSTRAINT PK_PRODUTO PRIMARY KEY (id_produto),
    CONSTRAINT CK_PRODUTO_PRECO   CHECK (preco >= 0),
    CONSTRAINT CK_PRODUTO_ESTOQUE CHECK (estoque >= 0)
);
GO

CREATE TABLE PEDIDO (
    id_pedido    INT IDENTITY(1,1) NOT NULL,
    fk_cliente   INT               NOT NULL,
    fk_vendedor  INT               NOT NULL,
    data_pedido  DATETIME2         NOT NULL CONSTRAINT DF_PEDIDO_DATA DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_PEDIDO PRIMARY KEY (id_pedido),
    CONSTRAINT FK_PEDIDO_CLIENTE  FOREIGN KEY (fk_cliente)  REFERENCES CLIENTE (id_cliente),
    CONSTRAINT FK_PEDIDO_VENDEDOR FOREIGN KEY (fk_vendedor) REFERENCES VENDEDOR (id_vendedor)
);
GO

CREATE TABLE ITEM_PEDIDO (
    fk_pedido       INT            NOT NULL,
    fk_produto      INT            NOT NULL,
    quantidade      DECIMAL(10,3)  NOT NULL,
    preco_unitario  DECIMAL(12,2)  NOT NULL,
    desconto        DECIMAL(5,2)   NOT NULL CONSTRAINT DF_ITEM_DESCONTO DEFAULT (0),
    CONSTRAINT PK_ITEM_PEDIDO PRIMARY KEY (fk_pedido, fk_produto),
    CONSTRAINT FK_ITEM_PEDIDO_PEDIDO  FOREIGN KEY (fk_pedido)  REFERENCES PEDIDO (id_pedido),
    CONSTRAINT FK_ITEM_PEDIDO_PRODUTO FOREIGN KEY (fk_produto) REFERENCES PRODUTO (id_produto),
    CONSTRAINT CK_ITEM_QUANTIDADE CHECK (quantidade > 0),
    CONSTRAINT CK_ITEM_PRECO      CHECK (preco_unitario >= 0),
    CONSTRAINT CK_ITEM_DESCONTO   CHECK (desconto >= 0 AND desconto <= 100)
);
GO

/* ---------------- Procedures originais (texto recuperado do backup) ---------------- */

CREATE PROCEDURE usp_CadastrarVendedor
    @nome NVARCHAR(150),
    @comissao_fixa DECIMAL(5,2),
    @telefone VARCHAR(20) = NULL,
    @email NVARCHAR(254) = NULL,
    @id_vendedor INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Validar o nome
        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50001, 'O nome do vendedor e obrigatorio.', 1;
        END;

        -- Validar a comissao
        IF @comissao_fixa < 0 OR @comissao_fixa > 100
        BEGIN
            THROW 50002, 'A comissao deve estar entre 0 e 100.', 1;
        END;

        -- Inserir vendedor
        INSERT INTO VENDEDOR (
            nome,
            telefone,
            email,
            comissao_fixa
        )
        VALUES (
            @nome,
            @telefone,
            @email,
            @comissao_fixa
        );

        -- Recuperar o ID gerado
        SET @id_vendedor = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Vendedor cadastrado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE PROCEDURE usp_CadastrarRegiao
    @nome NVARCHAR(100),
    @fk_vendedor INT,
    @descricao NVARCHAR(500) = NULL,
    @id_regiao INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Validar o nome da regiao
        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50003, 'O nome da regiao e obrigatorio.', 1;
        END;

        -- Verificar se o vendedor existe
        IF NOT EXISTS (
            SELECT 1
            FROM VENDEDOR
            WHERE id_vendedor = @fk_vendedor
        )
        BEGIN
            THROW 50004, 'Vendedor nao encontrado.', 1;
        END;

        -- Inserir regiao
        INSERT INTO REGIAO (
            nome,
            descricao,
            fk_vendedor
        )
        VALUES (
            @nome,
            @descricao,
            @fk_vendedor
        );

        -- Recuperar ID gerado
        SET @id_regiao = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Regiao cadastrada com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE PROCEDURE usp_CadastrarCliente
    @nome NVARCHAR(150),
    @cpf_cnpj VARCHAR(14),
    @fk_regiao INT,
    @telefone VARCHAR(20) = NULL,
    @email NVARCHAR(254) = NULL,
    @endereco NVARCHAR(250) = NULL,
    @id_cliente INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Validar nome
        IF NULLIF(LTRIM(RTRIM(@nome)), '') IS NULL
        BEGIN
            THROW 50005, 'O nome do cliente e obrigatorio.', 1;
        END;

        -- Validar CPF/CNPJ
        IF NULLIF(LTRIM(RTRIM(@cpf_cnpj)), '') IS NULL
        BEGIN
            THROW 50006, 'O CPF/CNPJ e obrigatorio.', 1;
        END;

        -- Verificar se a regiao existe
        IF NOT EXISTS (
            SELECT 1
            FROM REGIAO
            WHERE id_regiao = @fk_regiao
        )
        BEGIN
            THROW 50007, 'Regiao nao encontrada.', 1;
        END;

        -- Inserir cliente
        INSERT INTO CLIENTE (
            nome,
            cpf_cnpj,
            telefone,
            email,
            endereco,
            fk_regiao
        )
        VALUES (
            @nome,
            @cpf_cnpj,
            @telefone,
            @email,
            @endereco,
            @fk_regiao
        );

        -- Recuperar ID gerado
        SET @id_cliente = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Cliente cadastrado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE PROCEDURE usp_CadastrarProduto
    @descricao NVARCHAR(250),
    @preco DECIMAL(12,2),
    @estoque DECIMAL(10,3),
    @id_produto INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Validar descricao
        IF NULLIF(LTRIM(RTRIM(@descricao)), '') IS NULL
        BEGIN
            THROW 50008, 'A descricao do produto e obrigatoria.', 1;
        END;

        -- Validar preco
        IF @preco < 0
        BEGIN
            THROW 50009, 'O preco nao pode ser negativo.', 1;
        END;

        -- Validar estoque
        IF @estoque < 0
        BEGIN
            THROW 50010, 'O estoque nao pode ser negativo.', 1;
        END;

        -- Inserir produto
        INSERT INTO PRODUTO (
            descricao,
            preco,
            estoque
        )
        VALUES (
            @descricao,
            @preco,
            @estoque
        );

        -- Recuperar ID gerado
        SET @id_produto = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Produto cadastrado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO

CREATE PROCEDURE usp_CadastrarPedido
    @fk_cliente INT,
    @fk_vendedor INT,
    @id_pedido INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY

        -- Verificar se o cliente existe
        IF NOT EXISTS (
            SELECT 1
            FROM CLIENTE
            WHERE id_cliente = @fk_cliente
        )
        BEGIN
            THROW 50011, 'Cliente nao encontrado.', 1;
        END;

        -- Verificar se o vendedor existe
        IF NOT EXISTS (
            SELECT 1
            FROM VENDEDOR
            WHERE id_vendedor = @fk_vendedor
        )
        BEGIN
            THROW 50012, 'Vendedor nao encontrado.', 1;
        END;

        -- Verificar se o vendedor atende a regiao do cliente
        IF NOT EXISTS (
            SELECT 1
            FROM CLIENTE c
            INNER JOIN REGIAO r
                ON c.fk_regiao = r.id_regiao
            WHERE c.id_cliente = @fk_cliente
              AND r.fk_vendedor = @fk_vendedor
        )
        BEGIN
            THROW 50013,
                'O vendedor informado nao e responsavel pela regiao do cliente.',
                1;
        END;

        -- Inserir pedido
        INSERT INTO PEDIDO (
            fk_cliente,
            fk_vendedor
        )
        VALUES (
            @fk_cliente,
            @fk_vendedor
        );

        -- Recuperar ID gerado
        SET @id_pedido = CONVERT(INT, SCOPE_IDENTITY());

        PRINT 'Pedido cadastrado com sucesso!';

    END TRY

    BEGIN CATCH
        THROW;
    END CATCH;
END;
GO
