import { test, expect } from './helpers/fixtures';
import { padrao, t } from './helpers/textos';
import { unico, sufixo } from './helpers/db';
import {
  abrir, buscar, campo, clicar, botao, esperarErro, esperarStreamlit, esperarToast,
  excluirComConfirmacao, linhasDaTabela, painel, preencher, selecionarLinha, selecionarPorBusca,
} from './helpers/app';

test.describe('Vendedores', () => {
  test.beforeEach(async ({ page }) => {
    await abrir(page, 'Vendedores');
  });

  test('cadastrar vendedor: aparece na tabela e no banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'cadastros.vendedores.campo_nome': nome, 'cadastros.vendedores.campo_comissao': '6.5', 'comum.telefone': '(11) 90000-0001', 'comum.email': 'e2e@exemplo.test' });
    await clicar(page, form, 'cadastros.vendedores.botao_cadastrar');
    await esperarToast(page, 'cadastros.vendedores.cadastrado');

    const noBanco = await db.vendedor(nome);
    expect(noBanco).toMatchObject({ nome, comissao_fixa: 6.5, telefone: '(11) 90000-0001', email: 'e2e@exemplo.test' });

    const lista = painel(page, 'lista_vendedores');
    await buscar(page, lista, nome);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText(nome);
    await expect(linhasDaTabela(lista).first()).toContainText('6.5');
  });

  test('buscar vendedor: filtra a tabela', async ({ page, db }) => {
    const marca = sufixo();
    await db.criarVendedor(`E2E Busca ${marca} Ana`);
    await db.criarVendedor(`E2E Busca ${marca} Bruno`);
    const lista = painel(page, 'lista_vendedores');

    await buscar(page, lista, marca);
    await expect(linhasDaTabela(lista)).toHaveCount(2);
    await buscar(page, lista, `${marca} Bruno`);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText('Bruno');
    await buscar(page, lista, `nada-${marca}`);
    await expect(lista.getByText(t('comum.nenhum_registro'))).toBeVisible();
  });

  test('editar vendedor: muda na tabela e no banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const novoNome = `${nome} Editado`;
    await db.criarVendedor(nome, 5);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await selecionarPorBusca(page, lista, nome);
    await expect(form.getByText(padrao('cadastros.vendedores.editar'))).toBeVisible();
    await preencher(form, { 'cadastros.vendedores.campo_nome': novoNome, 'cadastros.vendedores.campo_comissao': '7.25' });
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarToast(page, 'cadastros.vendedores.atualizado');

    expect(await db.vendedor(nome)).toBeUndefined();
    expect(await db.vendedor(novoNome)).toMatchObject({ comissao_fixa: 7.25 });
    await buscar(page, lista, novoNome);
    await expect(linhasDaTabela(lista).first()).toContainText('7.25');
  });

  test('editar nome que muda a ordem mantém o mesmo vendedor selecionado', async ({ page, db }) => {
    // A e B aparecem nessa ordem; renomear A para "... Z" o leva para depois de B.
    const marca = `E2E Ordem ${sufixo()}`;
    const idA = await db.criarVendedor(`${marca} A`, 5);
    const idB = await db.criarVendedor(`${marca} B`, 5);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await buscar(page, lista, marca);
    await expect(linhasDaTabela(lista)).toHaveCount(2);
    await expect(linhasDaTabela(lista).first()).toContainText(`${marca} A`);
    await selecionarLinha(page, lista, `${marca} A`);
    await expect(form.getByText(t('cadastros.vendedores.editar', { id: idA }))).toBeVisible();

    await preencher(form, { 'cadastros.vendedores.campo_nome': `${marca} Z` });
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarToast(page, 'cadastros.vendedores.atualizado');

    // a ordem mudou (B, Z), mas continua selecionado o MESMO registro (id de A)
    await expect(linhasDaTabela(lista).first()).toContainText(`${marca} B`);
    await expect(form.getByText(t('cadastros.vendedores.editar', { id: idA }))).toBeVisible();
    await expect(campo(form, 'cadastros.vendedores.campo_nome')).toHaveValue(`${marca} Z`);
    await expect(linhasDaTabela(lista).filter({ hasText: `${marca} Z` })).toHaveAttribute('aria-selected', 'true');
    await expect(linhasDaTabela(lista).filter({ hasText: `${marca} B` })).toHaveAttribute('aria-selected', 'false');
    expect(await db.vendedor(`${marca} Z`)).toMatchObject({ id_vendedor: idA });
    expect(await db.vendedor(`${marca} B`)).toMatchObject({ id_vendedor: idB });
  });

  test('excluir vendedor: some da tabela e do banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    await db.criarVendedor(nome);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await selecionarPorBusca(page, lista, nome);
    await excluirComConfirmacao(page, form, 'cadastros.vendedores');
    await esperarToast(page, 'cadastros.vendedores.excluido');

    expect(await db.vendedor(nome)).toBeUndefined();
    await expect(form.getByText(t('cadastros.vendedores.novo'))).toBeVisible();
    await buscar(page, lista, nome);
    await expect(lista.getByText(t('comum.nenhum_registro'))).toBeVisible();
  });

  test('erro: nome do vendedor é obrigatório', async ({ page, db }) => {
    const form = painel(page, 'form_vendedores');
    await clicar(page, form, 'cadastros.vendedores.botao_cadastrar');
    await esperarErro(form, 'erros.50001');
    // nada gravado com nome em branco (sem comparar totais: outros testes gravam em paralelo)
    expect(await db.consulta("SELECT nome FROM VENDEDOR WHERE LTRIM(RTRIM(nome)) = ''")).toEqual([]);
  });

  test('erro: comissão acima de 100 é bloqueada', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'cadastros.vendedores.campo_nome': nome, 'cadastros.vendedores.campo_comissao': '150' });
    await botao(form, 'cadastros.vendedores.botao_cadastrar').click();
    // o próprio campo recusa o valor e o formulário não é enviado
    await expect(form.getByText(/outside the allowed range/)).toBeVisible();
    await expect(campo(form, 'cadastros.vendedores.campo_comissao')).toHaveAttribute('aria-invalid', 'true');
    await esperarStreamlit(page);
    expect(await db.vendedor(nome)).toBeUndefined();
  });

  test('erro: excluir vendedor com região é bloqueado', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const id = await db.criarVendedor(nome);
    await db.criarRegiao(unico('Região'), id);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await selecionarPorBusca(page, lista, nome);
    await excluirComConfirmacao(page, form, 'cadastros.vendedores');
    await esperarErro(form, t('erros.50023', { qtd: 1 }));
    expect(await db.vendedor(nome)).toBeDefined();
  });
});
