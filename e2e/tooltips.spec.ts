import { Locator, Page } from '@playwright/test';
import { test, expect } from './helpers/fixtures';
import { padrao, t } from './helpers/textos';
import {
  abrir, abrirAba, balaoCss, balaoNativo, escolherComRerun, escolherTema, estiloDoBalao, fecharBaloes,
  irPelaNavbar, painel, passarMouse, selecionarPorBusca,
} from './helpers/app';

type Medida = { ponto: string; estilo: Record<string, string> };

/** Mecanismo (a): help= nativo — passa o mouse e confere o texto no balão do Streamlit. */
async function conferirNativo(page: Page, alvo: Locator, texto: string | RegExp, ponto: string): Promise<Medida> {
  await passarMouse(page, alvo);
  const balao = balaoNativo(page).first();
  await expect(balao, ponto).toBeVisible();
  await expect(balao, ponto).toHaveText(texto);
  const estilo = await estiloDoBalao(balao);
  await fecharBaloes(page);
  return { ponto, estilo };
}

/** Mecanismo (b): tooltip em CSS — por hover ou por foco do teclado. */
async function conferirCss(page: Page, alvo: Locator, texto: string | RegExp, ponto: string,
                           modo: 'hover' | 'foco' = 'hover'): Promise<Medida> {
  if (modo === 'hover') await passarMouse(page, alvo);
  else await alvo.focus();
  const balao = balaoCss(alvo);
  await expect(balao, ponto).toBeVisible();
  await expect(balao, ponto).toHaveText(texto);
  await expect(balao).toHaveAttribute('role', 'tooltip');
  await expect(alvo).toHaveAttribute('aria-describedby', (await balao.getAttribute('id'))!);
  const estilo = await estiloDoBalao(balao);
  await fecharBaloes(page);
  await expect(balao).toBeHidden();
  return { ponto, estilo };
}

test.describe('Tooltips', () => {
  test('tooltips: hover e foco mostram o texto certo nos dois mecanismos, com o mesmo estilo', async ({ page }) => {
    const medidas: Medida[] = [];
    await abrir(page, 'Início');

    // (a) nativos
    medidas.push(await conferirNativo(page, page.getByTestId('stTopNavLink').filter({ hasText: t('nav.pedidos') }),
      t('tooltips.nav.pedidos'), 'navbar'));
    medidas.push(await conferirNativo(page, page.locator('.st-key-seletor_idioma button').first(),
      t('tooltips.idioma'), 'seletor de idioma'));
    const kpi = page.getByTestId('stMetric').filter({ hasText: t('inicio.kpi.total_vendido') });
    medidas.push(await conferirNativo(page, kpi.getByTestId('stTooltipHoverTarget'),
      t('tooltips.kpi.total_vendido'), 'KPI'));

    // (b) nossos, em CSS: faixa de status (hover e teclado) e card de último pedido
    const faixa = page.locator('.faixa-status .com-dica');
    medidas.push(await conferirCss(page, faixa.first(), t('tooltips.status.pedidos'), 'faixa (hover)'));
    medidas.push(await conferirCss(page, faixa.nth(2), t('tooltips.status.vendedores'), 'faixa (teclado)', 'foco'));
    medidas.push(await conferirCss(page, painel(page, 'ultimos').locator('.com-dica').first(),
      padrao('tooltips.ultimo_pedido'), 'card de último pedido'));

    // aba de relatório (CSS)
    await irPelaNavbar(page, 'Relatórios');
    const aba = await abrirAba(page, 'relatorios.abas.vendedor');
    medidas.push(await conferirCss(page, aba.locator('.linha-dica .com-dica'), t('tooltips.relatorios.vendedor'),
      'aba de relatório'));

    // comissão do pedido (nativo, campo) e coluna calculada "Total" (nativo, cabeçalho do grid)
    await irPelaNavbar(page, 'Pedidos');
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', 'Hotel');
    const campoComissao = corpo.getByTestId('stNumberInput')
      .filter({ hasText: t('pedidos.novo.campo_comissao') });
    medidas.push(await conferirNativo(page, campoComissao.getByTestId('stTooltipHoverTarget'),
      t('tooltips.pedido.comissao'), 'comissão do pedido'));
    const grade = painel(page, 'lista_pedidos').getByTestId('stDataFrame');
    const caixa = (await grade.boundingBox())!;
    await page.mouse.move(caixa.x + caixa.width - 30, caixa.y + 12);
    await page.mouse.move(caixa.x + caixa.width - 40, caixa.y + 17, { steps: 3 });
    const balaoColuna = balaoNativo(page).first();
    await expect(balaoColuna).toHaveText(t('tooltips.pedido.total'));
    medidas.push({ ponto: 'coluna Total', estilo: await estiloDoBalao(balaoColuna) });
    await fecharBaloes(page);

    // botão de excluir (nativo): o que acontece e quando é bloqueado
    await irPelaNavbar(page, 'Vendedores');
    await selecionarPorBusca(page, painel(page, 'lista_vendedores'), 'Carlos Mendes');
    medidas.push(await conferirNativo(page,
      painel(page, 'form_vendedores').getByRole('button', { name: t('cadastros.vendedores.excluir_botao') }),
      t('tooltips.excluir.vendedor'), 'botão excluir'));

    // o MESMO visual nos dois mecanismos
    expect(medidas.length).toBeGreaterThanOrEqual(6);
    const referencia = medidas[0].estilo;
    for (const m of medidas) expect(m.estilo, `estilo do tooltip em: ${m.ponto}`).toEqual(referencia);
    expect(referencia).toMatchObject({ fonte: '12px', padding: '6px 12px', raio: '6px', larguraMax: '260px',
                                       fundo: 'rgb(15, 23, 42)' });
  });

  test('tooltips: no tema escuro o balão fica claro com texto escuro', async ({ page }) => {
    await abrir(page, 'Início');
    await escolherTema(page, 'Dark');
    const kpi = page.getByTestId('stMetric').filter({ hasText: t('inicio.kpi.pedidos') });
    const nativo = await conferirNativo(page, kpi.getByTestId('stTooltipHoverTarget'), t('tooltips.kpi.pedidos'), 'KPI');
    const css = await conferirCss(page, page.locator('.faixa-status .com-dica').first(), t('tooltips.status.pedidos'), 'faixa');
    for (const m of [nativo, css]) {
      expect(m.estilo, m.ponto).toMatchObject({ fundo: 'rgb(248, 250, 252)', cor: 'rgb(15, 23, 42)' });
    }
    expect(css.estilo).toEqual(nativo.estilo);
  });
});
