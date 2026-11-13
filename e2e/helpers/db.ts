/**
 * Acesso direto ao banco de TESTE para os testes conferirem o que entrou/saiu de verdade.
 * Aqui pode usar SELECT: é código de teste, não do app.
 * Para criar dados de apoio (pré-requisitos), usamos as próprias procedures.
 */
import sql from 'mssql';
import { BANCO_E2E, senhaSa } from './env';

function configBanco(extra: Partial<sql.config> = {}): sql.config {
  return {
    server: 'localhost',
    port: 1433,
    user: 'sa',
    password: senhaSa(),
    database: BANCO_E2E,
    options: { encrypt: true, trustServerCertificate: true },
    ...extra,
  };
}

/**
 * Trava do banco de TESTE (sp_getapplock do SQL Server).
 * Todo teste pega a trava em modo compartilhado (vários ao mesmo tempo); o "fluxo completo",
 * que compara números globais (total de pedidos, total vendido...), pega em modo exclusivo:
 * espera os testes em andamento terminarem e roda sozinho. O SQL Server atende os pedidos
 * em ordem de chegada, então ninguém fica esperando para sempre.
 */
export class TravaBanco {
  private constructor(private readonly pool: sql.ConnectionPool) {}

  static async adquirir(modo: 'Shared' | 'Exclusive'): Promise<TravaBanco> {
    // uma conexão só (a trava pertence à sessão) e sem limite de tempo na espera
    const pool = await new sql.ConnectionPool(configBanco({ pool: { max: 1, min: 1 }, requestTimeout: 0 })).connect();
    const r = await pool.request().input('modo', sql.NVarChar(32), modo).query(`
      DECLARE @r INT;
      EXEC @r = sp_getapplock @Resource = N'central-ar-e2e', @LockMode = @modo,
                              @LockOwner = 'Session', @LockTimeout = -1;
      SELECT @r AS r;`);
    if (r.recordset[0].r < 0) {
      await pool.close();
      throw new Error(`Não foi possível obter a trava ${modo} do banco de teste (código ${r.recordset[0].r}).`);
    }
    return new TravaBanco(pool);
  }

  async liberar(): Promise<void> {
    try {
      await this.pool.request().query(`EXEC sp_releaseapplock @Resource = N'central-ar-e2e', @LockOwner = 'Session';`);
    } finally {
      await this.pool.close();
    }
  }
}

export class Banco {
  private constructor(private readonly pool: sql.ConnectionPool) {}

  static async abrir(): Promise<Banco> {
    const pool = await new sql.ConnectionPool(configBanco({ pool: { max: 4, min: 0 } })).connect();
    return new Banco(pool);
  }

  /** Números gerais do banco (para comparar com a faixa de status e os KPIs do Início). */
  async resumoGeral(): Promise<{ pedidos: number; total: number; comissoes: number; vendedores: number;
                                regioes: number; clientes: number; produtos: number }> {
    const r = await this.umOuNenhum<Record<string, number>>(`
      SELECT
        (SELECT COUNT(*) FROM PEDIDO)   AS pedidos,
        (SELECT COUNT(*) FROM VENDEDOR) AS vendedores,
        (SELECT COUNT(*) FROM REGIAO)   AS regioes,
        (SELECT COUNT(*) FROM CLIENTE)  AS clientes,
        (SELECT COUNT(*) FROM PRODUTO)  AS produtos,
        (SELECT ISNULL(SUM(x.v), 0) FROM ITEM_PEDIDO i
           CROSS APPLY (SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS v) x) AS total,
        (SELECT ISNULL(SUM(ROUND(x.v * p.percentual_comissao / 100, 2)), 0) FROM ITEM_PEDIDO i
           JOIN PEDIDO p ON p.id_pedido = i.fk_pedido
           CROSS APPLY (SELECT ROUND(i.quantidade * i.preco_unitario * (100 - i.desconto) / 100, 2) AS v) x) AS comissoes`);
    return Object.fromEntries(Object.entries(r!).map(([k, v]) => [k, Number(v)])) as any;
  }

  async fechar(): Promise<void> {
    await this.pool.close();
  }

  /** SELECT com parâmetros nomeados: consulta('... WHERE nome = @nome', { nome }). */
  async consulta<T = Record<string, any>>(texto: string, params: Record<string, unknown> = {}): Promise<T[]> {
    const req = this.pool.request();
    for (const [nome, valor] of Object.entries(params)) req.input(nome, valor);
    const r = await req.query(texto);
    return r.recordset as T[];
  }

  async umOuNenhum<T = Record<string, any>>(texto: string, params: Record<string, unknown> = {}): Promise<T | undefined> {
    return (await this.consulta<T>(texto, params))[0];
  }

  // ------------------------------------------------------------------ leituras

  vendedor(nome: string) {
    return this.umOuNenhum<{ id_vendedor: number; nome: string; comissao_fixa: number; telefone: string | null; email: string | null }>(
      'SELECT id_vendedor, nome, comissao_fixa, telefone, email FROM VENDEDOR WHERE nome = @nome', { nome });
  }

  regiao(nome: string) {
    return this.umOuNenhum<{ id_regiao: number; nome: string; fk_vendedor: number; descricao: string | null }>(
      'SELECT id_regiao, nome, fk_vendedor, descricao FROM REGIAO WHERE nome = @nome', { nome });
  }

  cliente(nome: string) {
    return this.umOuNenhum<{ id_cliente: number; nome: string; cpf_cnpj: string; fk_regiao: number; telefone: string | null }>(
      'SELECT id_cliente, nome, cpf_cnpj, fk_regiao, telefone FROM CLIENTE WHERE nome = @nome', { nome });
  }

  produto(descricao: string) {
    return this.umOuNenhum<{ id_produto: number; descricao: string; preco: number; estoque: number }>(
      'SELECT id_produto, descricao, preco, estoque FROM PRODUTO WHERE descricao = @descricao', { descricao });
  }

  async estoque(idProduto: number): Promise<number> {
    const r = await this.umOuNenhum<{ estoque: number }>('SELECT estoque FROM PRODUTO WHERE id_produto = @id', { id: idProduto });
    if (!r) throw new Error(`Produto ${idProduto} não existe`);
    return Number(r.estoque);
  }

  pedidosDoCliente(idCliente: number) {
    return this.consulta<{ id_pedido: number; fk_vendedor: number; percentual_comissao: number }>(
      'SELECT id_pedido, fk_vendedor, percentual_comissao FROM PEDIDO WHERE fk_cliente = @id ORDER BY id_pedido', { id: idCliente });
  }

  pedido(idPedido: number) {
    return this.umOuNenhum<{ id_pedido: number; fk_cliente: number; fk_vendedor: number; percentual_comissao: number }>(
      'SELECT id_pedido, fk_cliente, fk_vendedor, percentual_comissao FROM PEDIDO WHERE id_pedido = @id', { id: idPedido });
  }

  itensDoPedido(idPedido: number) {
    return this.consulta<{ fk_produto: number; quantidade: number; preco_unitario: number; desconto: number }>(
      'SELECT fk_produto, quantidade, preco_unitario, desconto FROM ITEM_PEDIDO WHERE fk_pedido = @id ORDER BY fk_produto', { id: idPedido });
  }

  /** Totais dos relatórios por região, vendedor e produto, lidos das MESMAS procedures que a tela usa,
   *  numa transação SERIALIZABLE (fotografia consistente mesmo com outros testes gravando em paralelo). */
  async totaisDosRelatorios(): Promise<{ regiao: number; vendedor: number; produto: number }> {
    const r = await this.umOuNenhum<{ regiao: number; vendedor: number; produto: number }>(`
      SET NOCOUNT ON;
      SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
      BEGIN TRAN;
        DECLARE @r TABLE (id INT, regiao NVARCHAR(100), vendedor NVARCHAR(150), qtd INT, total DECIMAL(14,2));
        DECLARE @v TABLE (id INT, vendedor NVARCHAR(150), qtd INT, total DECIMAL(14,2), comissao DECIMAL(14,2));
        DECLARE @p TABLE (id INT, produto NVARCHAR(250), qtd INT, quantidade DECIMAL(13,3), total DECIMAL(14,2));
        INSERT @r EXEC usp_ConsultarVendasPorRegiao;
        INSERT @v EXEC usp_ConsultarVendasPorVendedor;
        INSERT @p EXEC usp_ConsultarVendasPorProduto;
      COMMIT;
      SELECT (SELECT SUM(total) FROM @r) AS regiao, (SELECT SUM(total) FROM @v) AS vendedor,
             (SELECT SUM(total) FROM @p) AS produto;`);
    return { regiao: Number(r!.regiao), vendedor: Number(r!.vendedor), produto: Number(r!.produto) };
  }

  // ------------------------------------------------------------------ criação de pré-requisitos (via procedures)

  private async execComId(proc: string, saida: string, params: Record<string, unknown>): Promise<number> {
    const req = this.pool.request();
    for (const [nome, valor] of Object.entries(params)) req.input(nome, valor);
    req.output(saida, sql.Int);
    const r = await req.execute(proc);
    return Number(r.output[saida]);
  }

  criarVendedor(nome: string, comissao = 5) {
    return this.execComId('usp_CadastrarVendedor', 'id_vendedor', { nome, comissao_fixa: comissao });
  }

  criarRegiao(nome: string, idVendedor: number) {
    return this.execComId('usp_CadastrarRegiao', 'id_regiao', { nome, fk_vendedor: idVendedor });
  }

  criarCliente(nome: string, cpfCnpj: string, idRegiao: number) {
    return this.execComId('usp_CadastrarCliente', 'id_cliente', { nome, cpf_cnpj: cpfCnpj, fk_regiao: idRegiao });
  }

  criarProduto(descricao: string, preco: number, estoque: number) {
    return this.execComId('usp_CadastrarProduto', 'id_produto', { descricao, preco, estoque });
  }

  async criarPedido(idCliente: number, idVendedor: number, itens: { idProduto: number; quantidade: number }[],
                    percentual?: number): Promise<number> {
    const id = await this.execComId('usp_CadastrarPedido', 'id_pedido', {
      fk_cliente: idCliente, fk_vendedor: idVendedor, percentual_comissao: percentual ?? null });
    for (const item of itens) {
      await this.pool.request()
        .input('fk_pedido', id).input('fk_produto', item.idProduto).input('quantidade', item.quantidade)
        .execute('usp_CadastrarItemPedido');
    }
    return id;
  }

  /** Cenário completo de apoio: vendedor -> região -> cliente (nomes únicos). */
  async criarCenario(sufixo: string, comissao = 5) {
    const vendedor = `E2E Vendedor ${sufixo}`;
    const regiao = `E2E Região ${sufixo}`;
    const cliente = `E2E Cliente ${sufixo}`;
    const idVendedor = await this.criarVendedor(vendedor, comissao);
    const idRegiao = await this.criarRegiao(regiao, idVendedor);
    const idCliente = await this.criarCliente(cliente, cpfUnico(), idRegiao);
    return { vendedor, regiao, cliente, idVendedor, idRegiao, idCliente };
  }
}

// ------------------------------------------------------------------ dados únicos

/** Sufixo aleatório curto para nomes únicos ("E2E Cliente k3f9a2"). */
export function sufixo(): string {
  return Math.random().toString(36).slice(2, 8);
}

export function unico(prefixo: string): string {
  return `E2E ${prefixo} ${sufixo()}`;
}

function digitos(n: number): string {
  let s = String(1 + Math.floor(Math.random() * 9));
  while (s.length < n) s += Math.floor(Math.random() * 10);
  return s;
}

export const cpfUnico = () => digitos(11);
export const cnpjUnico = () => digitos(14);
