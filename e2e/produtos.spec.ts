import { test, expect } from './helpers/fixtures';
import { sufixo, unico } from './helpers/db';
import {
  abrir, buscar, clicar, esperarErro, esperarToast, excluirComConfirmacao,
  linhasDaTabela, painel, preencher, selecionarPorBusca,
} from './helpers/app';

test.describe('Produtos', () => {
  test.beforeEach(async ({ page }) => {
    await abrir(page, 'Produtos');
  });

  test('cadastrar produto: aparece na tabela e no banco', async ({ page, db }) => {
    const descricao = unico('Produto Split');
    const form = painel(page, 'form_produtos');
    await preencher(form, { 'Descrição *': descricao, 'Preço (R$) *': '1234.56', 'Estoque *': '12' });
    await clicar(page, form, 'Cadastrar produto');
    await esperarToast(page, 'Produto cadastrado');

    expect(await db.produto(descricao)).toMatchObject({ preco: 1234.56, estoque: 12 });
    const lista = painel(page, 'lista_produtos');
    await buscar(page, lista, descricao);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText('1234.56');
  });

  test('buscar produto: filtra a tabela', async ({ page, db }) => {
    const marca = sufixo();
    await db.criarProduto(`E2E Busca ${marca} Capacitor`, 10, 1);
    await db.criarProduto(`E2E Busca ${marca} Controle`, 20, 1);
    const lista = painel(page, 'lista_produtos');

    await buscar(page, lista, `Busca ${marca}`);
    await expect(linhasDaTabela(lista)).toHaveCount(2);
    await buscar(page, lista, `${marca} Controle`);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
  });

  test('editar produto: muda preço e estoque na tabela e no banco', async ({ page, db }) => {
    const descricao = unico('Produto');
    await db.criarProduto(descricao, 100, 5);
    const lista = painel(page, 'lista_produtos');
    const form = painel(page, 'form_produtos');

    await selecionarPorBusca(page, lista, descricao);
    await preencher(form, { 'Preço (R$) *': '150.75', 'Estoque *': '8' });
    await clicar(page, form, 'Salvar alterações');
    await esperarToast(page, 'Produto atualizado');

    expect(await db.produto(descricao)).toMatchObject({ preco: 150.75, estoque: 8 });
    await expect(linhasDaTabela(lista).first()).toContainText('150.75');
  });

  test('excluir produto: some da tabela e do banco', async ({ page, db }) => {
    const descricao = unico('Produto');
    await db.criarProduto(descricao, 100, 5);
    const lista = painel(page, 'lista_produtos');
    const form = painel(page, 'form_produtos');

    await selecionarPorBusca(page, lista, descricao);
    await excluirComConfirmacao(page, form, 'produto');
    await esperarToast(page, 'Produto excluído');

    expect(await db.produto(descricao)).toBeUndefined();
    await buscar(page, lista, descricao);
    await expect(lista.getByText('Nenhum registro encontrado.')).toBeVisible();
  });

  test('erro: descrição do produto é obrigatória', async ({ page, db }) => {
    const form = painel(page, 'form_produtos');
    await clicar(page, form, 'Cadastrar produto');
    await esperarErro(form, 'A descricao do produto e obrigatoria.');
    // nada gravado com descricao em branco (sem comparar totais: outros testes gravam em paralelo)
    expect(await db.consulta("SELECT descricao FROM PRODUTO WHERE LTRIM(RTRIM(descricao)) = ''")).toEqual([]);
  });

  test('erro: excluir produto já vendido é bloqueado', async ({ page, db }) => {
    const descricao = unico('Produto');
    const idProduto = await db.criarProduto(descricao, 100, 10);
    const cenario = await db.criarCenario(sufixo());
    await db.criarPedido(cenario.idCliente, cenario.idVendedor, [{ idProduto, quantidade: 2 }]);
    const lista = painel(page, 'lista_produtos');
    const form = painel(page, 'form_produtos');

    await selecionarPorBusca(page, lista, descricao);
    await excluirComConfirmacao(page, form, 'produto');
    await esperarErro(form, 'Nao e possivel excluir: o produto aparece em 1 item(ns) de pedido.');
    expect(await db.produto(descricao)).toBeDefined();
  });
});
