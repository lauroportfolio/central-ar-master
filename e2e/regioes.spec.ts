import { test, expect } from './helpers/fixtures';
import { padrao, t } from './helpers/textos';
import { cpfUnico, sufixo, unico } from './helpers/db';
import {
  abrir, buscar, recarregar, clicar, escolher, esperarErro, esperarToast, excluirComConfirmacao,
  linhasDaTabela, painel, preencher, selecionarPorBusca,
} from './helpers/app';

test.describe('Regiões', () => {
  test.beforeEach(async ({ page }) => {
    await abrir(page, 'Regiões');
  });

  test('cadastrar região: aparece na tabela e no banco', async ({ page, db }) => {
    const vendedor = unico('Vendedor');
    const idVendedor = await db.criarVendedor(vendedor);
    await recarregar(page);                     // a lista de vendedores do formulário é lida ao abrir a tela
    const nome = unico('Região');
    const form = painel(page, 'form_regioes');

    await preencher(form, { 'cadastros.regioes.campo_nome': nome, 'cadastros.regioes.campo_descricao_novo': 'Bairros de teste' });
    await escolher(page, form, 'cadastros.regioes.campo_vendedor', vendedor);
    await clicar(page, form, 'cadastros.regioes.botao_cadastrar');
    await esperarToast(page, 'cadastros.regioes.cadastrado');

    expect(await db.regiao(nome)).toMatchObject({ nome, fk_vendedor: idVendedor, descricao: 'Bairros de teste' });
    const lista = painel(page, 'lista_regioes');
    await buscar(page, lista, nome);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
    await expect(linhasDaTabela(lista).first()).toContainText(vendedor);
  });

  test('buscar região: filtra a tabela', async ({ page, db }) => {
    const marca = sufixo();
    const id = await db.criarVendedor(`E2E Vendedor ${marca}`);
    await db.criarRegiao(`E2E Busca ${marca} Norte`, id);
    await db.criarRegiao(`E2E Busca ${marca} Sul`, id);
    const lista = painel(page, 'lista_regioes');

    await buscar(page, lista, `Busca ${marca}`);
    await expect(linhasDaTabela(lista)).toHaveCount(2);
    await buscar(page, lista, `${marca} Sul`);
    await expect(linhasDaTabela(lista)).toHaveCount(1);
  });

  test('editar região: troca nome e vendedor na tabela e no banco', async ({ page, db }) => {
    const nome = unico('Região');
    const novoNome = `${nome} Editada`;
    const outroVendedor = unico('Vendedor');
    await db.criarRegiao(nome, await db.criarVendedor(unico('Vendedor')));
    const idOutro = await db.criarVendedor(outroVendedor);
    await recarregar(page);
    const lista = painel(page, 'lista_regioes');
    const form = painel(page, 'form_regioes');

    await selecionarPorBusca(page, lista, nome);
    await preencher(form, { 'cadastros.regioes.campo_nome': novoNome });
    await escolher(page, form, 'cadastros.regioes.campo_vendedor', outroVendedor);
    await clicar(page, form, 'comum.salvar_alteracoes');
    await esperarToast(page, 'cadastros.regioes.atualizado');

    expect(await db.regiao(novoNome)).toMatchObject({ fk_vendedor: idOutro });
    await buscar(page, lista, novoNome);
    await expect(linhasDaTabela(lista).first()).toContainText(outroVendedor);
  });

  test('excluir região: some da tabela e do banco', async ({ page, db }) => {
    const nome = unico('Região');
    await db.criarRegiao(nome, await db.criarVendedor(unico('Vendedor')));
    const lista = painel(page, 'lista_regioes');
    const form = painel(page, 'form_regioes');

    await selecionarPorBusca(page, lista, nome);
    await excluirComConfirmacao(page, form, 'cadastros.regioes');
    await esperarToast(page, 'cadastros.regioes.excluido');

    expect(await db.regiao(nome)).toBeUndefined();
    await buscar(page, lista, nome);
    await expect(lista.getByText(t('comum.nenhum_registro'))).toBeVisible();
  });

  test('erro: nome da região é obrigatório', async ({ page, db }) => {
    const form = painel(page, 'form_regioes');
    await clicar(page, form, 'cadastros.regioes.botao_cadastrar');
    await esperarErro(form, 'erros.50003');
    // nada gravado com nome em branco (sem comparar totais: outros testes gravam em paralelo)
    expect(await db.consulta("SELECT nome FROM REGIAO WHERE LTRIM(RTRIM(nome)) = ''")).toEqual([]);
  });

  test('erro: excluir região com clientes é bloqueado', async ({ page, db }) => {
    const nome = unico('Região');
    const idRegiao = await db.criarRegiao(nome, await db.criarVendedor(unico('Vendedor')));
    await db.criarCliente(unico('Cliente'), cpfUnico(), idRegiao);
    const lista = painel(page, 'lista_regioes');
    const form = painel(page, 'form_regioes');

    await selecionarPorBusca(page, lista, nome);
    await excluirComConfirmacao(page, form, 'cadastros.regioes');
    await esperarErro(form, t('erros.50025', { qtd: 1 }));
    expect(await db.regiao(nome)).toBeDefined();
  });
});
