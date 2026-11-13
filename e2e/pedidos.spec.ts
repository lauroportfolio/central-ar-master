import { Page } from '@playwright/test';
import { test, expect } from './helpers/fixtures';
import { padrao, t } from './helpers/textos';
import { sufixo } from './helpers/db';
import {
  abrir, abrirAba, adicionarItemNoEditor, campo, clicar, comRerun, escolher, escolherComRerun, esperarErro,
  esperarToast, excluirComConfirmacao, linhasDaTabela, painel, preencher, selecionarPorBusca, esperarTotalEmDestaque,
} from './helpers/app';

/** Abre um pedido existente pela lista (busca pelo nome do cliente, que é único no teste). */
async function abrirPedidoDoCliente(page: Page, cliente: string, idPedido: number) {
  await selecionarPorBusca(page, painel(page, 'lista_pedidos'), cliente);
  await expect(painel(page, 'pedido').getByText(t('pedidos.detalhe.titulo', { id: idPedido }))).toBeVisible();
}

test.describe('Pedidos', () => {
  test('criar pedido: vendedor preenchido pela região do cliente e estoque baixa', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s, 4.5);
    const produto = `E2E Produto ${s}`;
    const idProduto = await db.criarProduto(produto, 1500, 10);

    await abrir(page, 'Pedidos');
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', c.cliente);
    await expect(campo(corpo, 'pedidos.novo.campo_vendedor')).toHaveValue(`${c.vendedor} — ${c.regiao}`);
    await expect(campo(corpo, 'pedidos.novo.campo_comissao')).toHaveValue('4.50');

    await adicionarItemNoEditor(page, corpo, produto, 0);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 1500);
    await clicar(page, corpo, 'pedidos.novo.botao_salvar');
    await esperarToast(page, padrao('pedidos.novo.cadastrado', { total: 'R$ 1.500,00' }));

    const pedidos = await db.pedidosDoCliente(c.idCliente);
    expect(pedidos).toHaveLength(1);
    expect(pedidos[0]).toMatchObject({ fk_vendedor: c.idVendedor, percentual_comissao: 4.5 });
    expect(await db.itensDoPedido(pedidos[0].id_pedido)).toMatchObject([{ fk_produto: idProduto, quantidade: 1, preco_unitario: 1500 }]);
    expect(await db.estoque(idProduto)).toBe(9);
  });

  test('criar pedido com comissão personalizada', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s, 5);
    const produto = `E2E Produto ${s}`;
    await db.criarProduto(produto, 1000, 10);

    await abrir(page, 'Pedidos');
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', c.cliente);
    const comissao = campo(corpo, 'pedidos.novo.campo_comissao');
    await comissao.fill('8.25');
    await comRerun(page, () => comissao.press('Enter'));
    await adicionarItemNoEditor(page, corpo, produto, 0);
    await expect(corpo.getByText(padrao('pedidos.novo.rodape', { comissao: 'R$ 82,50' }))).toBeVisible();
    await clicar(page, corpo, 'pedidos.novo.botao_salvar');
    await esperarToast(page, 'pedidos.novo.cadastrado');

    const [pedido] = await db.pedidosDoCliente(c.idCliente);
    expect(pedido.percentual_comissao).toBe(8.25);                  // não usou a comissão fixa (5%)
  });

  test('itens: adicionar, alterar e remover conferindo o estoque (trigger)', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const prodA = `E2E Produto A ${s}`;
    const prodB = `E2E Produto B ${s}`;
    const idA = await db.criarProduto(prodA, 100, 10);
    const idB = await db.criarProduto(prodB, 200, 20);
    const idPedido = await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto: idA, quantidade: 2 }]);
    expect(await db.estoque(idA)).toBe(8);

    await abrir(page, 'Pedidos');
    await abrirPedidoDoCliente(page, c.cliente, idPedido);

    // adicionar B x3 -> estoque de B 20 -> 17
    let painelAba = await abrirAba(page, 'pedidos.detalhe.aba_adicionar');
    await escolher(page, painelAba, 'pedidos.detalhe.campo_produto', prodB);
    await preencher(painelAba, { 'pedidos.detalhe.campo_quantidade': 3 });
    await clicar(page, painelAba, 'pedidos.detalhe.botao_adicionar');
    await esperarToast(page, 'pedidos.detalhe.item_adicionado');
    expect(await db.estoque(idB)).toBe(17);
    expect(await db.itensDoPedido(idPedido)).toHaveLength(2);

    // alterar B de 3 para 5 -> estoque de B 17 -> 15
    painelAba = await abrirAba(page, 'pedidos.detalhe.aba_itens');
    await escolherComRerun(page, painelAba, 'pedidos.detalhe.alterar_item', prodB);
    await preencher(painelAba, { 'pedidos.detalhe.campo_quantidade': 5 });
    await clicar(page, painelAba, 'pedidos.detalhe.botao_salvar_item');
    await esperarToast(page, 'pedidos.detalhe.item_atualizado');
    expect(await db.estoque(idB)).toBe(15);
    expect((await db.itensDoPedido(idPedido)).find((i) => i.fk_produto === idB)?.quantidade).toBe(5);

    // remover A -> estoque de A volta para 10
    painelAba = await abrirAba(page, 'pedidos.detalhe.aba_itens');
    await escolherComRerun(page, painelAba, 'pedidos.detalhe.alterar_item', prodA);
    await clicar(page, painelAba, 'pedidos.detalhe.botao_remover_item');
    await esperarToast(page, 'pedidos.detalhe.item_removido');
    expect(await db.estoque(idA)).toBe(10);
    expect(await db.itensDoPedido(idPedido)).toMatchObject([{ fk_produto: idB, quantidade: 5 }]);
    await esperarTotalEmDestaque(painel(page, 'pedido'), 1000);
  });

  test('estoque insuficiente no pedido novo: erro e nada gravado', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const produto = `E2E Produto ${s}`;
    const idProduto = await db.criarProduto(produto, 300, 0);       // sem estoque

    await abrir(page, 'Pedidos');
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', c.cliente);
    await adicionarItemNoEditor(page, corpo, produto, 0);
    await clicar(page, corpo, 'pedidos.novo.botao_salvar');
    await esperarErro(corpo, padrao('erros.50022', { produto }));

    expect(await db.pedidosDoCliente(c.idCliente)).toEqual([]);     // nem o pedido ficou (transação)
    expect(await db.estoque(idProduto)).toBe(0);
  });

  test('estoque insuficiente ao adicionar item: erro e nada gravado', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const idA = await db.criarProduto(`E2E Produto A ${s}`, 100, 10);
    const prodB = `E2E Produto B ${s}`;
    const idB = await db.criarProduto(prodB, 100, 5);
    const idPedido = await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto: idA, quantidade: 1 }]);

    await abrir(page, 'Pedidos');
    await abrirPedidoDoCliente(page, c.cliente, idPedido);
    const painelAba = await abrirAba(page, 'pedidos.detalhe.aba_adicionar');
    await escolher(page, painelAba, 'pedidos.detalhe.campo_produto', prodB);
    await preencher(painelAba, { 'pedidos.detalhe.campo_quantidade': 999 });
    await clicar(page, painelAba, 'pedidos.detalhe.botao_adicionar');
    await esperarErro(painelAba, 'erros.50022');

    expect(await db.itensDoPedido(idPedido)).toMatchObject([{ fk_produto: idA }]);
    expect(await db.estoque(idB)).toBe(5);
  });

  test('excluir pedido: itens somem e o estoque volta', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const idA = await db.criarProduto(`E2E Produto A ${s}`, 100, 10);
    const idB = await db.criarProduto(`E2E Produto B ${s}`, 200, 20);
    const idPedido = await db.criarPedido(c.idCliente, c.idVendedor,
      [{ idProduto: idA, quantidade: 2 }, { idProduto: idB, quantidade: 3 }]);
    expect([await db.estoque(idA), await db.estoque(idB)]).toEqual([8, 17]);

    await abrir(page, 'Pedidos');
    await abrirPedidoDoCliente(page, c.cliente, idPedido);
    const painelAba = await abrirAba(page, 'pedidos.detalhe.aba_excluir');
    await excluirComConfirmacao(page, painelAba, 'pedidos.detalhe');
    await esperarToast(page, t('pedidos.detalhe.excluido', { id: idPedido }));

    expect(await db.pedido(idPedido)).toBeUndefined();
    expect(await db.itensDoPedido(idPedido)).toEqual([]);
    expect([await db.estoque(idA), await db.estoque(idB)]).toEqual([10, 20]);
    await expect(painel(page, 'pedido').getByText(t('pedidos.novo.titulo'))).toBeVisible();
    await expect(linhasDaTabela(painel(page, 'lista_pedidos'))).toHaveCount(0);
  });
});
