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
import { capturar, padrao, t, tPlural } from './helpers/textos';
import { cpfUnico, sufixo } from './helpers/db';
import {
  abrir, abrirAba, brl, buscar, campo, clicar, comRerun, escolher, escolherComRerun, esperarErro, esperarToast,
  esperarTotalEmDestaque, excluirComConfirmacao, irPelaNavbar, linhasDaTabela, painel, paraNumero, preencher,
  selecionarPorBusca, adicionarItemNoEditor, encontrarLinha, celulas,
} from './helpers/app';

const KPIS = ['total_vendido', 'pedidos', 'ticket_medio', 'comissoes', 'vendedores', 'regioes', 'clientes', 'produtos']
  .map((k) => `inicio.kpi.${k}`);

/** Lê a faixa de status e os KPIs da tela Início. */
async function lerInicio(page: Page) {
  const valor = (rotulo: string) =>
    page.getByTestId('stMetric').filter({ hasText: t(rotulo) }).getByTestId('stMetricValue');
  await expect(valor('inicio.kpi.total_vendido')).toBeVisible();
  const kpis: Record<string, string> = {};
  for (const rotulo of KPIS) kpis[rotulo] = (await valor(rotulo).innerText()).trim();
  return {
    faixa: (await page.locator('.faixa-status').innerText()).replace(/\s+/g, ' ').trim(),
    kpis,
    pedidos: Number(kpis['inicio.kpi.pedidos']),
    totalVendido: paraNumero(kpis['inicio.kpi.total_vendido']),
    comissoes: paraNumero(kpis['inicio.kpi.comissoes']),
  };
}

/** Igual ao brl_curto do app (faixa de status): R$ 123,8 mil / R$ 1,2 mi. */
function brlCurto(v: number): string {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1).replace('.', ',')} ${t('formato.milhao')}`;
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1).replace('.', ',')} ${t('formato.mil')}`;
  return brl(v);
}

const numero = (n: number) => expect.stringMatching(new RegExp(`^${n}(\\.0+)?$`));

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
    expect(inicial.faixa).toContain(`${resumoInicial.pedidos} ${tPlural('status.pedidos', resumoInicial.pedidos)}`);
    expect(inicial.faixa).toContain(`${brlCurto(resumoInicial.total)} ${t('status.vendidos')}`);
  });

  await test.step('2. Cadastrar um vendedor novo com comissão de 5%', async () => {
    await irPelaNavbar(page, 'Vendedores');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'cadastros.vendedores.campo_nome': vendedor, 'cadastros.vendedores.campo_comissao': '5' });
    await clicar(page, form, 'cadastros.vendedores.botao_cadastrar');
    await esperarToast(page, 'cadastros.vendedores.cadastrado');
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
    await preencher(form, { 'cadastros.regioes.campo_nome': regiao });
    await escolher(page, form, 'cadastros.regioes.campo_vendedor', vendedor);
    await clicar(page, form, 'cadastros.regioes.botao_cadastrar');
    await esperarToast(page, 'cadastros.regioes.cadastrado');
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
    await preencher(form, { 'cadastros.clientes.campo_nome': cliente, 'cadastros.clientes.campo_cpf': cpf, 'comum.telefone': '(11) 3000-1000' });
    await escolher(page, form, 'cadastros.clientes.campo_regiao', regiao);
    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarToast(page, 'cadastros.clientes.cadastrado');
    const c = await db.cliente(cliente);
    expect(c).toMatchObject({ cpf_cnpj: cpf, fk_regiao: ids.regiao });
    ids.cliente = c!.id_cliente;
    const lista = painel(page, 'lista_clientes');
    await buscar(page, lista, cliente);
    await expect(linhasDaTabela(lista).first()).toContainText(cpf);
  });

  await test.step('5. Tentar cadastrar outro cliente com o mesmo CPF: erro e nada gravado', async () => {
    const form = painel(page, 'form_clientes');
    await preencher(form, { 'cadastros.clientes.campo_nome': clienteRepetido, 'cadastros.clientes.campo_cpf': cpf });
    await escolher(page, form, 'cadastros.clientes.campo_regiao', regiao);
    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarErro(form, 'erros.cpf_duplicado');
    expect(await db.cliente(clienteRepetido)).toBeUndefined();
    expect(await db.consulta('SELECT id_cliente FROM CLIENTE WHERE cpf_cnpj = @cpf', { cpf })).toHaveLength(1);
  });

  await test.step('6. Cadastrar dois produtos novos com estoque 10 e 5', async () => {
    await irPelaNavbar(page, 'Produtos');
    const form = painel(page, 'form_produtos');
    for (const p of [prodA, prodB]) {
      await preencher(form, { 'cadastros.produtos.campo_descricao': p.nome, 'cadastros.produtos.campo_preco': p.preco, 'cadastros.produtos.campo_estoque': p.estoque });
      await clicar(page, form, 'cadastros.produtos.botao_cadastrar');
      await esperarToast(page, 'cadastros.produtos.cadastrado');
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
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', cliente);
    await expect(campo(corpo, 'pedidos.novo.campo_vendedor')).toHaveValue(`${vendedor} — ${regiao}`);
    await expect(campo(corpo, 'pedidos.novo.campo_comissao')).toHaveValue('5.00');   // padrão do vendedor
    const comissao = campo(corpo, 'pedidos.novo.campo_comissao');
    await comissao.fill('8');
    await comRerun(page, () => comissao.press('Enter'));
    await adicionarItemNoEditor(page, corpo, prodA.nome, 0);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 1200);
    await clicar(page, corpo, 'pedidos.novo.botao_salvar');
    const toast = await esperarToast(page, 'pedidos.novo.cadastrado');
    ids.pedido = Number(capturar('pedidos.novo.cadastrado', 'id', toast));

    expect(await db.pedido(ids.pedido)).toMatchObject({ fk_cliente: ids.cliente, fk_vendedor: ids.vendedor, percentual_comissao: 8 });
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([{ fk_produto: ids.produtoA, quantidade: 1 }]);
    expect(await db.estoque(ids.produtoA)).toBe(9);
  });

  await test.step('8. Itens: A com 3 unidades e B com 2 → estoque cai para 7 e 3 (trigger)', async () => {
    await selecionarPorBusca(page, painel(page, 'lista_pedidos'), cliente);
    await expect(painel(page, 'pedido').getByText(t('pedidos.detalhe.titulo', { id: ids.pedido }))).toBeVisible();

    let conteudo = await abrirAba(page, 'pedidos.detalhe.aba_adicionar');
    await escolher(page, conteudo, 'pedidos.detalhe.campo_produto', prodB.nome);
    await preencher(conteudo, { 'pedidos.detalhe.campo_quantidade': 2 });
    await clicar(page, conteudo, 'pedidos.detalhe.botao_adicionar');
    await esperarToast(page, 'pedidos.detalhe.item_adicionado');

    conteudo = await abrirAba(page, 'pedidos.detalhe.aba_itens');
    await escolherComRerun(page, conteudo, 'pedidos.detalhe.alterar_item', prodA.nome);
    await preencher(conteudo, { 'pedidos.detalhe.campo_quantidade': 3 });
    await clicar(page, conteudo, 'pedidos.detalhe.botao_salvar_item');
    await esperarToast(page, 'pedidos.detalhe.item_atualizado');

    expect(await db.estoque(ids.produtoA)).toBe(7);
    expect(await db.estoque(ids.produtoB)).toBe(3);
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([
      { fk_produto: ids.produtoA, quantidade: 3 }, { fk_produto: ids.produtoB, quantidade: 2 }]);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 3 * 1200 + 2 * 450);
  });

  await test.step('9. Tentar colocar mais unidades do que o estoque: erro, estoque e itens iguais', async () => {
    const conteudo = await abrirAba(page, 'pedidos.detalhe.aba_itens');
    await escolherComRerun(page, conteudo, 'pedidos.detalhe.alterar_item', prodB.nome);
    await preencher(conteudo, { 'pedidos.detalhe.campo_quantidade': 50 });                 // B tem só 3 livres
    await clicar(page, conteudo, 'pedidos.detalhe.botao_salvar_item');
    await esperarErro(conteudo, padrao('erros.50022', { produto: prodB.nome }));

    expect(await db.estoque(ids.produtoB)).toBe(3);
    expect(await db.itensDoPedido(ids.pedido)).toMatchObject([
      { fk_produto: ids.produtoA, quantidade: 3 }, { fk_produto: ids.produtoB, quantidade: 2 }]);
  });

  await test.step('10. Alterar a quantidade de A de 3 para 5 → estoque ajustado para 5', async () => {
    const conteudo = await abrirAba(page, 'pedidos.detalhe.aba_itens');
    await escolherComRerun(page, conteudo, 'pedidos.detalhe.alterar_item', prodA.nome);
    await preencher(conteudo, { 'pedidos.detalhe.campo_quantidade': 5 });
    await clicar(page, conteudo, 'pedidos.detalhe.botao_salvar_item');
    await esperarToast(page, 'pedidos.detalhe.item_atualizado');
    expect(await db.estoque(ids.produtoA)).toBe(5);
    await esperarTotalEmDestaque(painel(page, 'pedido'), TOTAL_PEDIDO);
  });

  await test.step('11. Relatórios: o pedido aparece nas 6 abas e os totais batem com o banco', async () => {
    await irPelaNavbar(page, 'Relatórios');

    let conteudo = await abrirAba(page, 'relatorios.abas.regiao');
    expect(await celulas(await encontrarLinha(page, conteudo, regiao))).toContainEqual(numero(TOTAL_PEDIDO));
    const totais = await db.totaisDosRelatorios();
    expect(totais.vendedor).toBeCloseTo(totais.regiao, 2);
    expect(totais.produto).toBeCloseTo(totais.regiao, 2);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('relatorios.total_geral') })).toContainText(brl(totais.regiao));

    conteudo = await abrirAba(page, 'relatorios.abas.cliente');
    expect(await celulas(await encontrarLinha(page, conteudo, cliente))).toContainEqual(numero(TOTAL_PEDIDO));

    conteudo = await abrirAba(page, 'relatorios.abas.vendedor');
    const linhaVendedor = await celulas(await encontrarLinha(page, conteudo, vendedor));
    expect(linhaVendedor).toContainEqual(numero(TOTAL_PEDIDO));
    expect(linhaVendedor).toContainEqual(numero(COMISSAO_PEDIDO));

    conteudo = await abrirAba(page, 'relatorios.abas.clientes_regiao');
    await escolherComRerun(page, conteudo, 'relatorios.campo_regiao', regiao);
    await expect(linhasDaTabela(conteudo)).toHaveCount(1);
    await expect(linhasDaTabela(conteudo).first()).toContainText(cliente);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('comum.total_comprado') })).toContainText(brl(TOTAL_PEDIDO));

    conteudo = await abrirAba(page, 'relatorios.abas.produto');
    expect(await celulas(await encontrarLinha(page, conteudo, prodA.nome))).toContainEqual(numero(6000));
    expect(await celulas(await encontrarLinha(page, conteudo, prodB.nome))).toContainEqual(numero(900));

    conteudo = await abrirAba(page, 'relatorios.abas.comissao');
    await escolherComRerun(page, conteudo, 'relatorios.campo_vendedor', vendedor);
    const linhaA = await celulas(await encontrarLinha(page, conteudo, prodA.nome));
    const linhaB = await celulas(await encontrarLinha(page, conteudo, prodB.nome));
    expect(linhaA).toContainEqual(numero(480));                    // 8% de 6.000,00
    expect(linhaB).toContainEqual(numero(72));                     // 8% de 900,00
    expect(linhaA).toContainEqual(numero(8));                      // % efetivo
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('relatorios.metrica_comissao') })).toContainText(brl(COMISSAO_PEDIDO));
  });

  await test.step('12. Início: +1 pedido, total vendido e comissões aumentam pelo valor do pedido', async () => {
    await irPelaNavbar(page, 'Início');
    const agora = await lerInicio(page);
    expect(agora.pedidos).toBe(inicial.pedidos + 1);
    expect(agora.totalVendido).toBeCloseTo(inicial.totalVendido + TOTAL_PEDIDO, 2);
    expect(agora.comissoes).toBeCloseTo(inicial.comissoes + COMISSAO_PEDIDO, 2);
    expect(agora.faixa).toContain(`${inicial.pedidos + 1} ${tPlural('status.pedidos', inicial.pedidos + 1)}`);
    expect(agora.faixa).toContain(`${brlCurto(inicial.totalVendido + TOTAL_PEDIDO)} ${t('status.vendidos')}`);
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
    await preencher(form, { 'comum.telefone': '(11) 97777-6666' });
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarToast(page, 'cadastros.clientes.atualizado');
    expect(await db.cliente(cliente)).toMatchObject({ telefone: '(11) 97777-6666' });
    await expect(linhasDaTabela(lista).first()).toContainText('(11) 97777-6666');
  });

  await test.step('14. Tentar excluir cliente, região e vendedor com pedido: bloqueado, nada some', async () => {
    let form = painel(page, 'form_clientes');
    await excluirComConfirmacao(page, form, 'cadastros.clientes');                // cliente ainda selecionado
    await esperarErro(form, t('erros.50026', { qtd: 1 }));

    await irPelaNavbar(page, 'Regiões');
    form = painel(page, 'form_regioes');
    await selecionarPorBusca(page, painel(page, 'lista_regioes'), regiao);
    await excluirComConfirmacao(page, form, 'cadastros.regioes');
    await esperarErro(form, t('erros.50025', { qtd: 1 }));

    await irPelaNavbar(page, 'Vendedores');
    form = painel(page, 'form_vendedores');
    await selecionarPorBusca(page, painel(page, 'lista_vendedores'), vendedor);
    await excluirComConfirmacao(page, form, 'cadastros.vendedores');
    await esperarErro(form, t('erros.50023', { qtd: 1 }));

    expect(await db.cliente(cliente)).toBeDefined();
    expect(await db.regiao(regiao)).toBeDefined();
    expect(await db.vendedor(vendedor)).toBeDefined();
    expect(await db.pedido(ids.pedido)).toBeDefined();
  });

  await test.step('15. Excluir o pedido → itens somem e o estoque volta a 10 e 5', async () => {
    await irPelaNavbar(page, 'Pedidos');
    await selecionarPorBusca(page, painel(page, 'lista_pedidos'), cliente);
    const conteudo = await abrirAba(page, 'pedidos.detalhe.aba_excluir');
    await excluirComConfirmacao(page, conteudo, 'pedidos.detalhe');
    await esperarToast(page, t('pedidos.detalhe.excluido', { id: ids.pedido }));

    expect(await db.pedido(ids.pedido)).toBeUndefined();
    expect(await db.itensDoPedido(ids.pedido)).toEqual([]);
    expect(await db.estoque(ids.produtoA)).toBe(10);
    expect(await db.estoque(ids.produtoB)).toBe(5);
    await expect(linhasDaTabela(painel(page, 'lista_pedidos'))).toHaveCount(0);
  });

  await test.step('16. Excluir cliente, região, vendedor e os dois produtos → somem da tela e do banco', async () => {
    const excluir = async (tela: 'Clientes' | 'Regiões' | 'Vendedores' | 'Produtos', chave: string,
                           nome: string) => {
      await irPelaNavbar(page, tela);
      const lista = painel(page, `lista_${chave}`);
      await selecionarPorBusca(page, lista, nome);
      await excluirComConfirmacao(page, painel(page, `form_${chave}`), `cadastros.${chave}`);
      await esperarToast(page, `cadastros.${chave}.excluido`);
      await buscar(page, lista, nome);
      await expect(lista.getByText(t('comum.nenhum_registro'))).toBeVisible();
    };
    await excluir('Clientes', 'clientes', cliente);
    expect(await db.cliente(cliente)).toBeUndefined();
    await excluir('Regiões', 'regioes', regiao);
    expect(await db.regiao(regiao)).toBeUndefined();
    await excluir('Vendedores', 'vendedores', vendedor);
    expect(await db.vendedor(vendedor)).toBeUndefined();
    await excluir('Produtos', 'produtos', prodA.nome);
    expect(await db.produto(prodA.nome)).toBeUndefined();
    await excluir('Produtos', 'produtos', prodB.nome);
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
