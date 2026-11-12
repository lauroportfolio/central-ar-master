/* =====================================================================
   Central de Ar Ltda. — 02_seed.sql  (dados de exemplo)
   Rodar DEPOIS de 00_schema_reconstruido.sql e 01_complemento.sql.

   Tudo é feito SOMENTE com EXEC das stored procedures.
   Roda numa transação única: se algo falhar, nada fica gravado.
   Se já houver vendedores cadastrados, o script não faz nada
   (evita duplicar os dados ao rodar duas vezes).

   Dados fictícios (CPF/CNPJ, telefones e e-mails inventados).
   ===================================================================== */

USE CentralDeAr;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- Já existe cadastro? (consulta feita pela própria procedure de listagem)
DECLARE @existentes TABLE (
    id_vendedor INT, nome NVARCHAR(150), telefone VARCHAR(20),
    email NVARCHAR(254), comissao_fixa DECIMAL(5,2)
);
INSERT INTO @existentes EXEC usp_ListarVendedores;

IF EXISTS (SELECT 1 FROM @existentes)
BEGIN
    PRINT 'O banco ja possui vendedores cadastrados: seed NAO executado.';
    RETURN;
END;

BEGIN TRANSACTION;

/* ---------------- Vendedores ---------------- */
DECLARE @v_carlos INT, @v_fernanda INT, @v_rafael INT;

EXEC usp_CadastrarVendedor @nome = N'Carlos Mendes',   @comissao_fixa = 5.00,
     @telefone = '(11) 98101-2001', @email = N'carlos.mendes@centraldear.example',   @id_vendedor = @v_carlos OUTPUT;
EXEC usp_CadastrarVendedor @nome = N'Fernanda Lima',   @comissao_fixa = 4.50,
     @telefone = '(11) 98101-2002', @email = N'fernanda.lima@centraldear.example',   @id_vendedor = @v_fernanda OUTPUT;
EXEC usp_CadastrarVendedor @nome = N'Rafael Souza',    @comissao_fixa = 6.00,
     @telefone = '(11) 98101-2003', @email = N'rafael.souza@centraldear.example',    @id_vendedor = @v_rafael OUTPUT;

/* ---------------- Regiões (cada uma com um único vendedor) ---------------- */
DECLARE @r_centro INT, @r_sul INT, @r_norte INT, @r_leste INT;

EXEC usp_CadastrarRegiao @nome = N'Centro',     @fk_vendedor = @v_carlos,
     @descricao = N'Sé, República, Bela Vista e Consolação', @id_regiao = @r_centro OUTPUT;
EXEC usp_CadastrarRegiao @nome = N'Zona Sul',   @fk_vendedor = @v_fernanda,
     @descricao = N'Moema, Santo Amaro, Vila Mariana e Saúde', @id_regiao = @r_sul OUTPUT;
EXEC usp_CadastrarRegiao @nome = N'Zona Norte', @fk_vendedor = @v_rafael,
     @descricao = N'Santana, Tucuruvi, Casa Verde e Vila Maria', @id_regiao = @r_norte OUTPUT;
EXEC usp_CadastrarRegiao @nome = N'Zona Leste', @fk_vendedor = @v_carlos,
     @descricao = N'Tatuapé, Mooca, Penha e Itaquera', @id_regiao = @r_leste OUTPUT;

/* ---------------- Clientes ---------------- */
DECLARE @c1 INT, @c2 INT, @c3 INT, @c4 INT, @c5 INT, @c6 INT, @c7 INT, @c8 INT, @c9 INT, @c10 INT;

EXEC usp_CadastrarCliente @nome = N'Padaria Pão Dourado Ltda.',      @cpf_cnpj = '11222333000101', @fk_regiao = @r_centro,
     @telefone = '(11) 3201-1001', @email = N'compras@paodourado.example',   @endereco = N'Rua Barão de Itapetininga, 120 - República',  @id_cliente = @c1 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Escritório Contábil Andrade',    @cpf_cnpj = '22333444000102', @fk_regiao = @r_centro,
     @telefone = '(11) 3201-1002', @email = N'contato@andradecont.example',  @endereco = N'Av. Paulista, 900, cj. 42 - Bela Vista',      @id_cliente = @c2 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Mariana Oliveira',               @cpf_cnpj = '10120230341',    @fk_regiao = @r_sul,
     @telefone = '(11) 99201-1003', @email = N'mariana.oliveira@email.example', @endereco = N'Rua Gaivota, 455, ap. 81 - Moema',        @id_cliente = @c3 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Clínica Odonto Sorriso',         @cpf_cnpj = '33444555000103', @fk_regiao = @r_sul,
     @telefone = '(11) 3201-1004', @email = N'adm@odontosorriso.example',    @endereco = N'Av. Santo Amaro, 3300 - Santo Amaro',         @id_cliente = @c4 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'João Pedro Santos',              @cpf_cnpj = '20230340452',    @fk_regiao = @r_sul,
     @telefone = '(11) 99201-1005', @email = N'joaopedro.santos@email.example', @endereco = N'Rua Domingos de Morais, 1500 - Vila Mariana', @id_cliente = @c5 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Mercadinho Bom Preço',           @cpf_cnpj = '44555666000104', @fk_regiao = @r_norte,
     @telefone = '(11) 3201-1006', @email = N'gerencia@bompreco.example',    @endereco = N'Av. Cruzeiro do Sul, 2100 - Santana',         @id_cliente = @c6 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Ana Beatriz Costa',              @cpf_cnpj = '30340450563',    @fk_regiao = @r_norte,
     @telefone = '(11) 99201-1007', @email = N'anabeatriz.costa@email.example', @endereco = N'Rua Voluntários da Pátria, 3800 - Santana', @id_cliente = @c7 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Academia Corpo em Forma',        @cpf_cnpj = '55666777000105', @fk_regiao = @r_leste,
     @telefone = '(11) 3201-1008', @email = N'financeiro@corpoemforma.example', @endereco = N'Rua Tuiuti, 1800 - Tatuapé',              @id_cliente = @c8 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Lucas Ferreira',                 @cpf_cnpj = '40450560674',    @fk_regiao = @r_leste,
     @telefone = '(11) 99201-1009', @email = N'lucas.ferreira@email.example',   @endereco = N'Rua da Mooca, 2900 - Mooca',                @id_cliente = @c9 OUTPUT;
EXEC usp_CadastrarCliente @nome = N'Hotel Estação Leste',            @cpf_cnpj = '66777888000106', @fk_regiao = @r_leste,
     @telefone = '(11) 3201-1010', @email = N'manutencao@hotelestacao.example', @endereco = N'Av. Radial Leste, 5000 - Penha',          @id_cliente = @c10 OUTPUT;

/* ---------------- Produtos ---------------- */
DECLARE @p_split9 INT, @p_split12 INT, @p_split18 INT, @p_janela INT,
        @p_pisoteto INT, @p_kit INT, @p_capacitor INT, @p_instalacao INT;

EXEC usp_CadastrarProduto @descricao = N'Ar-Condicionado Split Hi-Wall Inverter 9.000 BTUs',  @preco = 2399.00, @estoque = 40,  @id_produto = @p_split9 OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Ar-Condicionado Split Hi-Wall Inverter 12.000 BTUs', @preco = 2899.00, @estoque = 35,  @id_produto = @p_split12 OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Ar-Condicionado Split Hi-Wall 18.000 BTUs',          @preco = 3990.00, @estoque = 20,  @id_produto = @p_split18 OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Ar-Condicionado de Janela 7.500 BTUs',               @preco = 1499.00, @estoque = 25,  @id_produto = @p_janela OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Ar-Condicionado Piso-Teto 36.000 BTUs',              @preco = 8990.00, @estoque = 8,   @id_produto = @p_pisoteto OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Kit de Instalação (tubulação de cobre 3 m + suporte)', @preco = 289.90, @estoque = 120, @id_produto = @p_kit OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Capacitor de Partida 35 µF (peça de reposição)',     @preco = 79.90,   @estoque = 150, @id_produto = @p_capacitor OUTPUT;
EXEC usp_CadastrarProduto @descricao = N'Serviço de Instalação de Split até 18.000 BTUs',     @preco = 450.00,  @estoque = 999, @id_produto = @p_instalacao OUTPUT;

/* ---------------- Pedidos e itens ----------------
   O vendedor é sempre o responsável pela região do cliente.
   @percentual_comissao omitido = comissão fixa do vendedor;
   informado = comissão negociada só para aquele pedido.
   @preco_unitario omitido = preço atual do produto.                       */
DECLARE @ped INT;

-- 1) Padaria (Centro / Carlos) — comissão padrão
EXEC usp_CadastrarPedido @fk_cliente = @c1, @fk_vendedor = @v_carlos, @data_pedido = '2026-06-03T10:15:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split18,    @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 2;

-- 2) Escritório Andrade (Centro / Carlos) — comissão negociada 7%
EXEC usp_CadastrarPedido @fk_cliente = @c2, @fk_vendedor = @v_carlos, @percentual_comissao = 7.00, @data_pedido = '2026-06-18T14:40:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split12,    @quantidade = 4, @desconto = 5;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 4;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 4, @desconto = 10;

-- 3) Mariana (Zona Sul / Fernanda)
EXEC usp_CadastrarPedido @fk_cliente = @c3, @fk_vendedor = @v_fernanda, @data_pedido = '2026-07-02T09:30:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split9,     @quantidade = 1;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 1;

-- 4) Clínica Odonto (Zona Sul / Fernanda) — comissão negociada 3,5%
EXEC usp_CadastrarPedido @fk_cliente = @c4, @fk_vendedor = @v_fernanda, @percentual_comissao = 3.50, @data_pedido = '2026-07-10T16:05:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split12,    @quantidade = 3, @desconto = 8;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 3;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 3;

-- 5) Mercadinho (Zona Norte / Rafael)
EXEC usp_CadastrarPedido @fk_cliente = @c6, @fk_vendedor = @v_rafael, @data_pedido = '2026-07-22T11:20:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_pisoteto,   @quantidade = 1;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 1;

-- 6) Ana Beatriz (Zona Norte / Rafael) — janela, preço promocional informado
EXEC usp_CadastrarPedido @fk_cliente = @c7, @fk_vendedor = @v_rafael, @data_pedido = '2026-08-04T15:00:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_janela,     @quantidade = 1, @preco_unitario = 1399.00;

-- 7) Academia (Zona Leste / Carlos) — comissão negociada 6%
EXEC usp_CadastrarPedido @fk_cliente = @c8, @fk_vendedor = @v_carlos, @percentual_comissao = 6.00, @data_pedido = '2026-08-12T10:45:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_pisoteto,   @quantidade = 2, @desconto = 7;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 2;

-- 8) Lucas (Zona Leste / Carlos)
EXEC usp_CadastrarPedido @fk_cliente = @c9, @fk_vendedor = @v_carlos, @data_pedido = '2026-08-25T18:10:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split9,     @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 2;

-- 9) Hotel (Zona Leste / Carlos) — pedido grande, comissão reduzida 3%
EXEC usp_CadastrarPedido @fk_cliente = @c10, @fk_vendedor = @v_carlos, @percentual_comissao = 3.00, @data_pedido = '2026-09-03T08:50:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split12,    @quantidade = 10, @desconto = 12;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 10, @desconto = 10;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 10, @desconto = 15;

-- 10) João Pedro (Zona Sul / Fernanda) — só peça
EXEC usp_CadastrarPedido @fk_cliente = @c5, @fk_vendedor = @v_fernanda, @data_pedido = '2026-09-15T13:25:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_capacitor,  @quantidade = 1;

-- 11) Padaria de novo (Centro / Carlos) — manutenção
EXEC usp_CadastrarPedido @fk_cliente = @c1, @fk_vendedor = @v_carlos, @data_pedido = '2026-09-28T09:05:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_capacitor,  @quantidade = 2;

-- 12) Mercadinho de novo (Zona Norte / Rafael) — comissão negociada 8%
EXEC usp_CadastrarPedido @fk_cliente = @c6, @fk_vendedor = @v_rafael, @percentual_comissao = 8.00, @data_pedido = '2026-10-07T10:00:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split18,    @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 2;

-- 13) Clínica de novo (Zona Sul / Fernanda)
EXEC usp_CadastrarPedido @fk_cliente = @c4, @fk_vendedor = @v_fernanda, @data_pedido = '2026-10-21T15:35:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split9,     @quantidade = 2;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_capacitor,  @quantidade = 4;

-- 14) Ana Beatriz de novo (Zona Norte / Rafael)
EXEC usp_CadastrarPedido @fk_cliente = @c7, @fk_vendedor = @v_rafael, @data_pedido = '2026-11-03T17:15:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_split12,    @quantidade = 1;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_kit,        @quantidade = 1;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_instalacao, @quantidade = 1;

-- 15) Escritório Andrade de novo (Centro / Carlos) — janelas para a copa
EXEC usp_CadastrarPedido @fk_cliente = @c2, @fk_vendedor = @v_carlos, @data_pedido = '2026-11-10T11:40:00', @id_pedido = @ped OUTPUT;
EXEC usp_CadastrarItemPedido @fk_pedido = @ped, @fk_produto = @p_janela,     @quantidade = 2, @desconto = 5;

COMMIT TRANSACTION;

PRINT 'Seed concluido: 3 vendedores, 4 regioes, 10 clientes, 8 produtos e 15 pedidos.';
GO
