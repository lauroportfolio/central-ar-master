/**
 * Fluxo completo: percorre o app inteiro como numa demonstração, do cadastro à exclusão.
 * Cada etapa (test.step) confere na TELA e no BANCO de teste.
 *
 * Como compara números globais (total de pedidos, total vendido, comissões), este teste
 * roda com a trava EXCLUSIVA do banco de teste (tag @exclusivo): espera os outros testes
 * em andamento terminarem e ninguém grava enquanto ele roda.
 *
 * Assistir: SLOW_MO=500 npx playwright test e2e/fluxo-completo.spec.ts --headed --workers=1
 */
import { Page } from '@playwright/test';
import { test, expect } from './helpers/fixtures';
import { cpfUnico, sufixo } from './helpers/db';
import {
  abrir, brl, buscar, campo, clicar, comRerun, escolher, escolherComRerun, esperarErro, esperarToast,
  esperarTotalEmDestaque, excluirComConfirmacao, irPelaNavbar, linhasDaTabela, painel, paraNumero, preencher,
  selecionarPorBusca, adicionarItemNoEditor, encontrarLinha, celulas,
} from './helpers/app';

const KPIS = ['Total vendido', 'Pedidos', 'Ticket médio', 'Comissões', 'Vendedores', 'Regiões', 'Clientes', 'Produtos'];

/** Lê a faixa de status e os KPIs da tela Início. */
async function lerInicio(page: Page) {
  const valor = (rotulo: string) =>
    page.getByTestId('stMetric').filter({ hasText: rotulo }).getByTestId('stMetricValue');
  await expect(valor('Total vendido')).toBeVisible();
  const kpis: Record<string, string> = {};
  for (const rotulo of KPIS) kpis[rotulo] = (await valor(rotulo).innerText()).trim();
  return {
    faixa: (await page.locator('.faixa-status').innerText()).replace(/\s+/g, ' ').trim(),
    kpis,
    pedidos: Number(kpis['Pedidos']),
    totalVendido: paraNumero(kpis['Total vendido']),
    comissoes: paraNumero(kpis['Comissões']),
  };
}

/** Igual ao brl_curto do app (faixa de status): R$ 123,8 mil / R$ 1,2 mi. */
function brlCurto(v: number): string {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1).replace('.', ',')} mi`;
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1).replace('.', ',')} mil`;
  return brl(v);
}

const numero = (n: number) => expect.stringMatching(new RegExp(`^${n}(\\.0+)?$`));

async function aba(page: Page, nome: string) {
  const guia = page.getByRole('tab', { name: nome, exact: true });
  await guia.click();
  await expect(guia).toHaveAttribute('aria-selected', 'true');
  return page.getByRole('tabpanel');
}

test('fluxo completo', { tag: '@exclusivo' }, async ({ page, db }) => {
  test.setTimeout(10 * 60_000);            // é longo, ainda mais com SLOW_MO

  const s = sufixo();
  const vendedor = `E2E Fluxo Vendedor ${s}`;
  const regiao = `E2E Fluxo Região ${s}`;
  const cliente = `E2E Fluxo Cliente ${s}`;
  const clienteRepetido = `E2E Fluxo Cliente Repetido ${s}`;
  const cpf = cpfUnico();
  const prodA = { nome: `E2E Fluxo Produto A ${s}`, preco: 1200, estoque: 10 };
  const prodB = { nome: `E2E Fluxo Produto B ${s}`, preco: 450, estoque: 5 };
  // pedido final: A x5 (6.000,00) + B x2 (900,00) = 6.900,00; comissão 8% = 480,00 + 72,00 = 552,00
  const TOTAL_PEDIDO = 6900;
  const COMISSAO_PEDIDO = 552;

  let inicial!: Awaited<ReturnType<typeof lerInicio>>;
  let resumoInicial!: Awaited<ReturnType<typeof db.resumoGeral>>;
  const ids = { vendedor: 0, regiao: 0, cliente: 0, produtoA: 0, produtoB: 0, pedido: 0 };

  await test.step('1. Abrir o Início e guardar os números da faixa de status e dos KPIs', async () => {
    await abrir(page, 'Início');
    inicial = await lerInicio(page);
    resumoInicial = await db.resumoGeral();
    expect(inicial.pedidos).toBe(resumoInicial.pedidos);
    expect(inicial.totalVendido).toBeCloseTo(resumoInicial.total, 2);
    expect(inicial.comissoes).toBeCloseTo(resumoInicial.comissoes, 2);
    expect(inicial.faixa).toContain(`${resumoInicial.pedidos} pedidos`);
    expect(inicial.faixa).toContain(`${brlCurto(resumoInicial.total)} vendidos`);
  });

  await test.step('2. Cadastrar um vendedor novo com comissão de 5%', async () => {
    await irPelaNavbar(page, 'Vendedores');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'Nome *': vendedor, 'Comissão padrão (%) *': '5' });
    await clicar(page, form, 'Cadastrar vendedor');
    await esperarToast(page, 'Vendedor cadastrado');
    const v = await db.vendedor(vendedor);
    expect(v).toMatchObject({ comissao_fixa: 5 });
    ids.vendedor = v!.id_vendedor;
    const lista = painel(page, 'lista_vendedores');
    await buscar(page, lista, vendedor);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
  });

  await test.step('3. Cadastrar uma região nova atendida por esse vendedor', async () => {
    await irPelaNavbar(page, 'Regiões');
    const form = painel(page, 'form_regioes');
    await preencher(form, { 'Nome da região *': regiao });
    await escolher(page, form, 'Vendedor responsável *', vendedor);
    await clicar(page, form, 'Cadastrar região');
    await esperarToast(page, 'Região cadastrada');
    const r = await db.regiao(regiao);
    expect(r).toMatchObject({ fk_vendedor: ids.vendedor });
    ids.regiao = r!.id_regiao;
    const lista = painel(page, 'lista_regioes');
    await buscar(page, lista, regiao);
    await expect(linhasDaTabela(lista).first()).toContainText(vendedor);
  });

  await test.step('4. Cadastrar um cliente novo nessa região (CPF único)', async () => {
    await irPelaNavbar(page, 'Clientes');
    const form = painel(page, 'form_clientes');
    await preencher(form, { 'Nome / razão social *': cliente, 'CPF/CNPJ * (somente números)': cpf, Telefone: '(11) 3000-1000' });
    await escolher(page, form, 'Região *', regiao);
    await clicar(page, form, 'Cadastrar cliente');
    await esperarToast(page, 'Cliente cadastrado');
    const c = await db.cliente(cliente);
    expect(c).toMatchObject({ cpf_cnpj: cpf, fk_regiao: ids.regiao });
    ids.cliente = c!.id_cliente;
    const lista = painel(page, 'lista_clientes');
    await buscar(page, lista, cliente);
    await expect(linhasDaTabela(lista).first()).toContainText(cpf);
  });

  await test.step('5. Tentar cadastrar outro cliente com o mesmo CPF: erro e nada gravado', async () => {
    const form = painel(page, 'form_clientes');
    await preencher(form, { 'Nome / razão social *': clienteRepetido, 'CPF/CNPJ * (somente números)': cpf });
    await escolher(page, form, 'Região *', regiao);
    await clicar(page, form, 'Cadastrar cliente');
    await esperarErro(form, 'Ja existe um cliente com este CPF/CNPJ.');
    expect(await db.cliente(clienteRepetido)).toBeUndefined();
    expect(await db.consulta('SELECT id_cliente FROM CLIENTE WHERE cpf_cnpj = @cpf', { cpf })).toHaveLength(1);
  });

  await test.step('6. Cadastrar dois produtos novos com estoque 10 e 5', async () => {
    await irPelaNavbar(page, 'Produtos');
    const form = painel(page, 'form_produtos');
    for (const p of [prodA, prodB]) {
      await preencher(form, { 'Descrição *': p.nome, 'Preço (R$) *': p.preco, 'Estoque *': p.estoque });
      await clicar(page, form, 'Cadastrar produto');
      await esperarToast(page, 'Produto cadastrado');
    }
    const a = await db.produto(prodA.nome);
    const b = await db.produto(prodB.nome);
    expect(a).toMatchObject({ preco: 1200, estoque: 10 });
    expect(b).toMatchObject({ preco: 450, estoque: 5 });
    ids.produtoA = a!.id_produto;
    ids.produtoB = b!.id_produto;
    const lista = painel(page, 'lista_produtos');
    await buscar(page, lista, `Fluxo Produto`);
    await expect(linhasDaTabela(lista).filter({ hasText: s })).toHaveCount(2);
  });

  await test.step('7. Criar pedido: vendedor vem da região e comissão do pedido muda para 8%', async () => {
    await irPelaNavbar(page, 'Pedidos');
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'Cliente *', cliente);
    await expect(campo(corpo, 'Vendedor (responsável pela região)')).toHaveValue(`${vendedor} — ${regiao}`);
    await expect(campo(corpo, 'Comissão deste pedido (%)')).toHaveValue('5.00');   // padrão do vendedor
    const comissao = campo(corpo, 'Comissão deste pedido (%)');
    await comissao.fill('8');
    await comRerun(page, () => comissao.press('Enter'));
    await adicionarItemNoEditor(page, corpo, prodA.nome, 0);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 1200);
    await clicar(page, corpo, 'Salvar pedido');
    const toast = await esperarToast(page, /Pedido nº \d+ cadastrado/);
    ids.pedido = Number(toast.match(/Pedido nº (\d+)/)![1]);

    expect(await db.pedido(ids.pedido)).toMatchObject({ fk_cliente: ids.cliente, fk_vendedor: ids.vendedor, percentual_comissao: 8 });
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([{ fk_produto: ids.produtoA, quantidade: 1 }]);
    expect(await db.estoque(ids.produtoA)).toBe(9);
  });

  await test.step('8. Itens: A com 3 unidades e B com 2 → estoque cai para 7 e 3 (trigger)', async () => {
    await selecionarPorBusca(page, painel(page, 'lista_pedidos'), cliente);
    await expect(painel(page, 'pedido').getByText(`Pedido nº ${ids.pedido}`)).toBeVisible();

    let conteudo = await aba(page, 'Adicionar item');
    await escolher(page, conteudo, 'Produto', prodB.nome);
    await preencher(conteudo, { Quantidade: 2 });
    await clicar(page, conteudo, 'Adicionar item');
    await esperarToast(page, 'Item adicionado');

    conteudo = await aba(page, 'Itens');
    await escolherComRerun(page, conteudo, 'Alterar ou remover o item', prodA.nome);
    await preencher(conteudo, { Quantidade: 3 });
    await clicar(page, conteudo, 'Salvar item');
    await esperarToast(page, 'Item atualizado');

    expect(await db.estoque(ids.produtoA)).toBe(7);
    expect(await db.estoque(ids.produtoB)).toBe(3);
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([
      { fk_produto: ids.produtoA, quantidade: 3 }, { fk_produto: ids.produtoB, quantidade: 2 }]);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 3 * 1200 + 2 * 450);
  });

  await test.step('9. Tentar colocar mais unidades do que o estoque: erro, estoque e itens iguais', async () => {
    const conteudo = await aba(page, 'Itens');
    await escolherComRerun(page, conteudo, 'Alterar ou remover o item', prodB.nome);
    await preencher(conteudo, { Quantidade: 50 });                 // B tem só 3 livres
    await clicar(page, conteudo, 'Salvar item');
    await esperarErro(conteudo, `Estoque insuficiente para o produto "${prodB.nome}"`);

    expect(await db.estoque(ids.produtoB)).toBe(3);
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([
      { fk_produto: ids.produtoA, quantidade: 3 }, { fk_produto: ids.produtoB, quantidade: 2 }]);
  });

  await test.step('10. Alterar a quantidade de A de 3 para 5 → estoque ajustado para 5', async () => {
    const conteudo = await aba(page, 'Itens');
    await escolherComRerun(page, conteudo, 'Alterar ou remover o item', prodA.nome);
    await preencher(conteudo, { Quantidade: 5 });
    await clicar(page, conteudo, 'Salvar item');
    await esperarToast(page, 'Item atualizado');
    expect(await db.estoque(ids.produtoA)).toBe(5);
    await esperarTotalEmDestaque(painel(page, 'pedido'), TOTAL_PEDIDO);
  });

  await test.step('11. Relatórios: o pedido aparece nas 6 abas e os totais batem com o banco', async () => {
    await irPelaNavbar(page, 'Relatórios');

    let conteudo = await aba(page, 'Por região');
    expect(await celulas(await encontrarLinha(page, conteudo, regiao))).toContainEqual(numero(TOTAL_PEDIDO));
    const totais = await db.totaisDosRelatorios();
    expect(totais.vendedor).toBeCloseTo(totais.regiao, 2);
    expect(totais.produto).toBeCloseTo(totais.regiao, 2);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: 'Total geral' })).toContainText(brl(totais.regiao));

    conteudo = await aba(page, 'Por cliente');
    expect(await celulas(await encontrarLinha(page, conteudo, cliente))).toContainEqual(numero(TOTAL_PEDIDO));

    conteudo = await aba(page, 'Por vendedor');
    const linhaVendedor = await celulas(await encontrarLinha(page, conteudo, vendedor));
    expect(linhaVendedor).toContainEqual(numero(TOTAL_PEDIDO));
    expect(linhaVendedor).toContainEqual(numero(COMISSAO_PEDIDO));

    conteudo = await aba(page, 'Clientes de uma região');
    await escolherComRerun(page, conteudo, 'Região *', regiao);
    await expect(linhasDaTabela(conteudo)).toHaveCount(1);
    await expect(linhasDaTabela(conteudo).first()).toContainText(cliente);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: 'Total comprado' })).toContainText(brl(TOTAL_PEDIDO));

    conteudo = await aba(page, 'Por produto');
    expect(await celulas(await encontrarLinha(page, conteudo, prodA.nome))).toContainEqual(numero(6000));
    expect(await celulas(await encontrarLinha(page, conteudo, prodB.nome))).toContainEqual(numero(900));

    conteudo = await aba(page, 'Comissão por vendedor');
    await escolherComRerun(page, conteudo, 'Vendedor', vendedor);
    const linhaA = await celulas(await encontrarLinha(page, conteudo, prodA.nome));
    const linhaB = await celulas(await encontrarLinha(page, conteudo, prodB.nome));
    expect(linhaA).toContainEqual(numero(480));                    // 8% de 6.000,00
    expect(linhaB).toContainEqual(numero(72));                     // 8% de 900,00
    expect(linhaA).toContainEqual(numero(8));                      // % efetivo
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: 'Comissão' })).toContainText(brl(COMISSAO_PEDIDO));
  });

  await test.step('12. Início: +1 pedido, total vendido e comissões aumentam pelo valor do pedido', async () => {
    await irPelaNavbar(page, 'Início');
    const agora = await lerInicio(page);
    expect(agora.pedidos).toBe(inicial.pedidos + 1);
    expect(agora.totalVendido).toBeCloseTo(inicial.totalVendido + TOTAL_PEDIDO, 2);
    expect(agora.comissoes).toBeCloseTo(inicial.comissoes + COMISSAO_PEDIDO, 2);
    expect(agora.faixa).toContain(`${inicial.pedidos + 1} pedidos`);
    expect(agora.faixa).toContain(`${brlCurto(inicial.totalVendido + TOTAL_PEDIDO)} vendidos`);
    const resumo = await db.resumoGeral();
    expect(resumo.pedidos).toBe(resumoInicial.pedidos + 1);
    expect(resumo.total).toBeCloseTo(resumoInicial.total + TOTAL_PEDIDO, 2);
    expect(resumo.comissoes).toBeCloseTo(resumoInicial.comissoes + COMISSAO_PEDIDO, 2);
  });

  await test.step('13. Editar o telefone do cliente → muda na tela e no banco', async () => {
    await irPelaNavbar(page, 'Clientes');
    const lista = painel(page, 'lista_clientes');
    const form = painel(page, 'form_clientes');
    await selecionarPorBusca(page, lista, cliente);
    await preencher(form, { Telefone: '(11) 97777-6666' });
    await clicar(page, form, 'Salvar alterações');
    await esperarToast(page, 'Cliente atualizado');
    expect(await db.cliente(cliente)).toMatchObject({ telefone: '(11) 97777-6666' });
    await expect(linhasDaTabela(lista).first()).toContainText('(11) 97777-6666');
  });

  await test.step('14. Tentar excluir cliente, região e vendedor com pedido: bloqueado, nada some', async () => {
    let form = painel(page, 'form_clientes');
    await excluirComConfirmacao(page, form, 'cliente');                // cliente ainda selecionado
    await esperarErro(form, 'Nao e possivel excluir: o cliente possui 1 pedido(s)');

    await irPelaNavbar(page, 'Regiões');
    form = painel(page, 'form_regioes');
    await selecionarPorBusca(page, painel(page, 'lista_regioes'), regiao);
    await excluirComConfirmacao(page, form, 'região');
    await esperarErro(form, 'Nao e possivel excluir: a regiao possui 1 cliente(s)');

    await irPelaNavbar(page, 'Vendedores');
    form = painel(page, 'form_vendedores');
    await selecionarPorBusca(page, painel(page, 'lista_vendedores'), vendedor);
    await excluirComConfirmacao(page, form, 'vendedor');
    await esperarErro(form, 'Nao e possivel excluir: o vendedor e responsavel por 1 regiao(oes)');

    expect(await db.cliente(cliente)).toBeDefined();
    expect(await db.regiao(regiao)).toBeDefined();
    expect(await db.vendedor(vendedor)).toBeDefined();
    expect(await db.pedido(ids.pedido)).toBeDefined();
  });

  await test.step('15. Excluir o pedido → itens somem e o estoque volta a 10 e 5', async () => {
    await irPelaNavbar(page, 'Pedidos');
    await selecionarPorBusca(page, painel(page, 'lista_pedidos'), cliente);
    const conteudo = await aba(page, 'Excluir pedido');
    await excluirComConfirmacao(page, conteudo, 'pedido');
    await esperarToast(page, `Pedido nº ${ids.pedido} excluído`);

    expect(await db.pedido(ids.pedido)).toBeUndefined();
    expect(await db.itensDoPedido(ids.pedido)).toEqual([]);
    expect(await db.estoque(ids.produtoA)).toBe(10);
    expect(await db.estoque(ids.produtoB)).toBe(5);
    await expect(linhasDaTabela(painel(page, 'lista_pedidos'))).toHaveCount(0);
  });

  await test.step('16. Excluir cliente, região, vendedor e os dois produtos → somem da tela e do banco', async () => {
    const excluir = async (tela: 'Clientes' | 'Regiões' | 'Vendedores' | 'Produtos', chave: string,
                           entidade: string, nome: string, aviso: string) => {
      await irPelaNavbar(page, tela);
      const lista = painel(page, `lista_${chave}`);
      await selecionarPorBusca(page, lista, nome);
      await excluirComConfirmacao(page, painel(page, `form_${chave}`), entidade);
      await esperarToast(page, aviso);
      await buscar(page, lista, nome);
      await expect(lista.getByText('Nenhum registro encontrado.')).toBeVisible();
    };
    await excluir('Clientes', 'clientes', 'cliente', cliente, 'Cliente excluído');
    expect(await db.cliente(cliente)).toBeUndefined();
    await excluir('Regiões', 'regioes', 'região', regiao, 'Região excluída');
    expect(await db.regiao(regiao)).toBeUndefined();
    await excluir('Vendedores', 'vendedores', 'vendedor', vendedor, 'Vendedor excluído');
    expect(await db.vendedor(vendedor)).toBeUndefined();
    await excluir('Produtos', 'produtos', 'produto', prodA.nome, 'Produto excluído');
    expect(await db.produto(prodA.nome)).toBeUndefined();
    await excluir('Produtos', 'produtos', 'produto', prodB.nome, 'Produto excluído');
    expect(await db.produto(prodB.nome)).toBeUndefined();
  });

  await test.step('17. Início: faixa de status e KPIs iguais aos da etapa 1', async () => {
    await irPelaNavbar(page, 'Início');
    const final = await lerInicio(page);
    expect(final.kpis).toEqual(inicial.kpis);
    expect(final.faixa).toBe(inicial.faixa);
    expect(await db.resumoGeral()).toEqual(resumoInicial);
  });
});
