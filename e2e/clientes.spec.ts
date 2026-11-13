import { test, expect } from './helpers/fixtures';
import { padrao, t } from './helpers/textos';
import { cnpjUnico, cpfUnico, sufixo, unico } from './helpers/db';
import {
  abrir, buscar, recarregar, clicar, escolher, esperarErro, esperarToast, excluirComConfirmacao,
  linhasDaTabela, painel, preencher, selecionarPorBusca,
} from './helpers/app';

test.describe('Clientes', () => {
  test.beforeEach(async ({ page }) => {
    await abrir(page, 'Clientes');
  });

  test('cadastrar cliente: aparece na tabela e no banco (CPF/CNPJ só com números)', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    await recarregar(page);                       // as regiões do formulário são lidas ao abrir a tela
    const nome = unico('Cliente');
    const cnpj = cnpjUnico();
    const cnpjFormatado = `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
    const form = painel(page, 'form_clientes');

    await preencher(form, {
      'cadastros.clientes.campo_nome': nome,
      'cadastros.clientes.campo_cpf': cnpjFormatado,
      'comum.telefone': '(11) 3000-0000',
      'comum.email': 'cliente@exemplo.test',
      'comum.endereco': 'Rua do Teste, 100',
    });
    await escolher(page, form, 'cadastros.clientes.campo_regiao', cenario.regiao);
    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarToast(page, 'cadastros.clientes.cadastrado');

    expect(await db.cliente(nome)).toMatchObject({ cpf_cnpj: cnpj, fk_regiao: cenario.idRegiao });
    const lista = painel(page, 'lista_clientes');
    await buscar(page, lista, nome);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText(cnpj);
  });

  test('buscar cliente: filtra por nome e por CPF/CNPJ', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const cpf = cpfUnico();
    await db.criarCliente(`${cenario.cliente} Segundo`, cpf, cenario.idRegiao);
    const lista = painel(page, 'lista_clientes');

    await buscar(page, lista, cenario.cliente);
    await expect(linhasDaTabela(lista)).toHaveCount(2);
    await buscar(page, lista, cpf);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText('Segundo');
  });

  test('editar cliente: muda na tabela e no banco', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const novoNome = `${cenario.cliente} Editado`;
    const lista = painel(page, 'lista_clientes');
    const form = painel(page, 'form_clientes');

    await selecionarPorBusca(page, lista, cenario.cliente);
    await preencher(form, { 'cadastros.clientes.campo_nome': novoNome, 'comum.telefone': '(11) 98888-7777' });
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarToast(page, 'cadastros.clientes.atualizado');

    expect(await db.cliente(novoNome)).toMatchObject({ telefone: '(11) 98888-7777' });
    await buscar(page, lista, novoNome);
    await expect(linhasDaTabela(lista).first()).toContainText('(11) 98888-7777');
  });

  test('excluir cliente: some da tabela e do banco', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const lista = painel(page, 'lista_clientes');
    const form = painel(page, 'form_clientes');

    await selecionarPorBusca(page, lista, cenario.cliente);
    await excluirComConfirmacao(page, form, 'cadastros.clientes');
    await esperarToast(page, 'cadastros.clientes.excluido');

    expect(await db.cliente(cenario.cliente)).toBeUndefined();
    await buscar(page, lista, cenario.cliente);
    await expect(lista.getByText(t('comum.nenhum_registro'))).toBeVisible();
  });

  test('erro: nome e CPF/CNPJ são obrigatórios', async ({ page, db }) => {
    const form = painel(page, 'form_clientes');

    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarErro(form, 'erros.50005');

    const nome = unico('Cliente');
    await preencher(form, { 'cadastros.clientes.campo_nome': nome });
    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarErro(form, 'erros.50006');
    expect(await db.cliente(nome)).toBeUndefined();
    // nada gravado com nome em branco (sem comparar totais: outros testes gravam em paralelo)
    expect(await db.consulta("SELECT nome FROM CLIENTE WHERE LTRIM(RTRIM(nome)) = ''")).toEqual([]);
  });

  test('erro: CPF/CNPJ repetido no cadastro', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const existente = await db.cliente(cenario.cliente);
    await recarregar(page);
    const nome = unico('Cliente');
    const form = painel(page, 'form_clientes');

    await preencher(form, { 'cadastros.clientes.campo_nome': nome, 'cadastros.clientes.campo_cpf': existente!.cpf_cnpj });
    await escolher(page, form, 'cadastros.clientes.campo_regiao', cenario.regiao);
    await clicar(page, form, 'cadastros.clientes.botao_cadastrar');
    await esperarErro(form, 'erros.cpf_duplicado');
    expect(await db.cliente(nome)).toBeUndefined();
  });

  test('erro: CPF/CNPJ repetido na edição', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const outroCpf = cpfUnico();
    await db.criarCliente(`${cenario.cliente} Outro`, outroCpf, cenario.idRegiao);
    const lista = painel(page, 'lista_clientes');
    const form = painel(page, 'form_clientes');

    await selecionarPorBusca(page, lista, `${cenario.cliente} Outro`);
    await preencher(form, { 'cadastros.clientes.campo_cpf': (await db.cliente(cenario.cliente))!.cpf_cnpj });
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarErro(form, 'erros.50028');
    expect(await db.cliente(`${cenario.cliente} Outro`)).toMatchObject({ cpf_cnpj: outroCpf });
  });

  test('erro: excluir cliente com pedido é bloqueado', async ({ page, db }) => {
    const cenario = await db.criarCenario(sufixo());
    const idProduto = await db.criarProduto(unico('Produto'), 100, 10);
    await db.criarPedido(cenario.idCliente, cenario.idVendedor, [{ idProduto, quantidade: 1 }]);
    const lista = painel(page, 'lista_clientes');
    const form = painel(page, 'form_clientes');

    await selecionarPorBusca(page, lista, cenario.cliente);
    await excluirComConfirmacao(page, form, 'cadastros.clientes');
    await esperarErro(form, t('erros.50026', { qtd: 1 }));
    expect(await db.cliente(cenario.cliente)).toBeDefined();
  });
});
