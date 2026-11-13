import { test, expect } from './helpers/fixtures';
import { t } from './helpers/textos';
import { sufixo } from './helpers/db';
import { abrir, abrirAba, encontrarLinha, escolherComRerun, linhasDaTabela, paraNumero, recarregar } from './helpers/app';

const ABAS = ['regiao', 'cliente', 'vendedor', 'clientes_regiao', 'produto', 'comissao'].map((a) => `relatorios.abas.${a}`);

test.describe('Relatórios', () => {
  test('as 6 abas de relatório abrem sem erro', async ({ page }) => {
    await abrir(page, 'Relatórios');
    for (const nome of ABAS) {
      const conteudo = await abrirAba(page, nome);
      if (nome === 'relatorios.abas.clientes_regiao') await escolherComRerun(page, conteudo, 'relatorios.campo_regiao', 'Centro');
      await expect(conteudo.getByTestId('stDataFrame').first()).toBeVisible();
      await expect(conteudo.locator('[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"]').first()).toBeVisible();
      await expect(page.getByTestId('stException')).toHaveCount(0);
      await expect(page.getByTestId('stAlertContentError')).toHaveCount(0);
    }
  });

  test('pedido novo aparece nos totais de região, cliente, vendedor, produto e comissão', async ({ page, db }) => {
    // valor alto e único: a linha fica no topo de cada relatório (ordenados do maior para o menor)
    const s = sufixo();
    const c = await db.criarCenario(s);
    const produto = `E2E Produto Relatório ${s}`;
    const idProduto = await db.criarProduto(produto, 987654.32, 5);
    await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto, quantidade: 1 }], 10);
    const total = '987654.32';          // a tabela acessível do grid guarda o valor bruto
    const comissao = '98765.43';        // 10% arredondado

    await abrir(page, 'Relatórios');

    let conteudo = await abrirAba(page, 'relatorios.abas.regiao');
    await expect(await encontrarLinha(page, conteudo, c.regiao)).toContainText(total);

    conteudo = await abrirAba(page, 'relatorios.abas.cliente');
    await expect(await encontrarLinha(page, conteudo, c.cliente)).toContainText(total);

    conteudo = await abrirAba(page, 'relatorios.abas.vendedor');
    const linhaVendedor = await encontrarLinha(page, conteudo, c.vendedor);
    await expect(linhaVendedor).toContainText(total);
    await expect(linhaVendedor).toContainText(comissao);

    conteudo = await abrirAba(page, 'relatorios.abas.clientes_regiao');
    await escolherComRerun(page, conteudo, 'relatorios.campo_regiao', c.regiao);
    await expect(linhasDaTabela(conteudo)).toHaveCount(1);
    await expect(linhasDaTabela(conteudo).first()).toContainText(c.cliente);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('comum.total_comprado') })).toContainText('R$ 987.654,32');

    conteudo = await abrirAba(page, 'relatorios.abas.produto');
    await expect(await encontrarLinha(page, conteudo, produto)).toContainText(total);

    conteudo = await abrirAba(page, 'relatorios.abas.comissao');
    await escolherComRerun(page, conteudo, 'relatorios.campo_vendedor', c.vendedor);
    await expect(linhasDaTabela(conteudo).filter({ hasText: produto })).toContainText(comissao);
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('relatorios.metrica_comissao') })).toContainText('R$ 98.765,43');
  });

  test('totais por região, vendedor e produto são iguais', async ({ page, db }) => {
    await abrir(page, 'Relatórios');
    // outros testes gravam em paralelo: repete até tela e banco serem lidos no mesmo instante
    await expect(async () => {
      await recarregar(page);
      const totalNaTela = paraNumero(await page.getByRole('tabpanel').getByTestId('stMetricValue').first().innerText());
      const t = await db.totaisDosRelatorios();       // as 3 procedures dos relatórios, numa transação
      expect(t.vendedor).toBeCloseTo(t.regiao, 2);
      expect(t.produto).toBeCloseTo(t.regiao, 2);
      expect(totalNaTela).toBeCloseTo(t.regiao, 2);   // "Total geral" da aba Por região
    }).toPass({ timeout: 60_000 });
  });
});
