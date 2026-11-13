import { test, expect } from './helpers/fixtures';
import { unico, sufixo } from './helpers/db';
import {
  abrir, buscar, campo, clicar, botao, esperarErro, esperarStreamlit, esperarToast,
  excluirComConfirmacao, linhasDaTabela, painel, preencher, selecionarPorBusca,
} from './helpers/app';

test.describe('Vendedores', () => {
  test.beforeEach(async ({ page }) => {
    await abrir(page, 'Vendedores');
  });

  test('cadastrar vendedor: aparece na tabela e no banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'Nome *': nome, 'Comissão padrão (%) *': '6.5', Telefone: '(11) 90000-0001', 'E-mail': 'e2e@exemplo.test' });
    await clicar(page, form, 'Cadastrar vendedor');
    await esperarToast(page, 'Vendedor cadastrado');

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
    await expect(lista.getByText('Nenhum registro encontrado.')).toBeVisible();
  });

  test('editar vendedor: muda na tabela e no banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const novoNome = `${nome} Editado`;
    await db.criarVendedor(nome, 5);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await selecionarPorBusca(page, lista, nome);
    await expect(form.getByText(/^Editar vendedor/)).toBeVisible();
    await preencher(form, { 'Nome *': novoNome, 'Comissão padrão (%) *': '7.25' });
    await clicar(page, form, 'Salvar alterações');
    await esperarToast(page, 'Vendedor atualizado');

    expect(await db.vendedor(nome)).toBeUndefined();
    expect(await db.vendedor(novoNome)).toMatchObject({ comissao_fixa: 7.25 });
    await buscar(page, lista, novoNome);
    await expect(linhasDaTabela(lista).first()).toContainText('7.25');
  });

  test('excluir vendedor: some da tabela e do banco', async ({ page, db }) => {
    const nome = unico('Vendedor');
    await db.criarVendedor(nome);
    const lista = painel(page, 'lista_vendedores');
    const form = painel(page, 'form_vendedores');

    await selecionarPorBusca(page, lista, nome);
    await excluirComConfirmacao(page, form, 'vendedor');
    await esperarToast(page, 'Vendedor excluído');

    expect(await db.vendedor(nome)).toBeUndefined();
    await expect(form.getByText('Novo vendedor')).toBeVisible();
    await buscar(page, lista, nome);
    await expect(lista.getByText('Nenhum registro encontrado.')).toBeVisible();
  });

  test('erro: nome do vendedor é obrigatório', async ({ page, db }) => {
    const form = painel(page, 'form_vendedores');
    await clicar(page, form, 'Cadastrar vendedor');
    await esperarErro(form, 'O nome do vendedor e obrigatorio.');
    // nada gravado com nome em branco (sem comparar totais: outros testes gravam em paralelo)
    expect(await db.consulta("SELECT nome FROM VENDEDOR WHERE LTRIM(RTRIM(nome)) = ''")).toEqual([]);
  });

  test('erro: comissão acima de 100 é bloqueada', async ({ page, db }) => {
    const nome = unico('Vendedor');
    const form = painel(page, 'form_vendedores');
    await preencher(form, { 'Nome *': nome, 'Comissão padrão (%) *': '150' });
    await botao(form, 'Cadastrar vendedor').click();
    // o próprio campo recusa o valor e o formulário não é enviado
    await expect(form.getByText(/outside the allowed range/)).toBeVisible();
    await expect(campo(form, 'Comissão padrão (%) *')).toHaveAttribute('aria-invalid', 'true');
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
    await excluirComConfirmacao(page, form, 'vendedor');
    await esperarErro(form, 'Nao e possivel excluir: o vendedor e responsavel por 1 regiao(oes)');
    expect(await db.vendedor(nome)).toBeDefined();
  });
});
