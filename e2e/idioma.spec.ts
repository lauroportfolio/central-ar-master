import { test, expect } from './helpers/fixtures';
import { t } from './helpers/textos';
import {
  abrir, abrirAba, balaoNativo, botao, campo, esperarErro, esperarStreamlit, fecharBaloes, irPelaNavbar, painel,
  passarMouse, recarregar, trocarIdioma,
} from './helpers/app';

test.describe('Idioma', () => {
  test('idioma: trocar para inglês, F5 mantém e voltar para português', async ({ page }) => {
    await abrir(page, 'Início');
    await expect(page.getByTestId('stTopNavLink').filter({ hasText: t('nav.pedidos') })).toBeVisible();

    // português -> inglês pelo seletor da navbar
    await trocarIdioma(page, 'en');
    await expect(page).toHaveURL(/[?&]lang=en/);
    for (const chave of ['nav.inicio', 'nav.pedidos', 'nav.relatorios']) {
      await expect(page.getByTestId('stTopNavLink').filter({ hasText: t(chave, {}, 'en') })).toBeVisible();
    }
    await expect(page.getByTestId('stTopNavSection')).toContainText(t('nav.cadastros', {}, 'en'));
    await expect(page.locator('.faixa-status')).toContainText(t('status.vendidos', {}, 'en'));
    await expect(page.getByText(t('inicio.visao_geral', {}, 'en'))).toBeVisible();

    // um tooltip em inglês (KPI do Início)
    const kpi = page.getByTestId('stMetric').filter({ hasText: t('inicio.kpi.total_vendido', {}, 'en') });
    await passarMouse(page, kpi.getByTestId('stTooltipHoverTarget'));
    await expect(balaoNativo(page).first()).toHaveText(t('tooltips.kpi.total_vendido', {}, 'en'));
    await fecharBaloes(page);

    // um formulário e um erro do banco (THROW 50001) em inglês
    await irPelaNavbar(page, 'Vendedores', 'en');
    const form = painel(page, 'form_vendedores');
    await expect(form.getByText(t('cadastros.vendedores.novo', {}, 'en'))).toBeVisible();
    await expect(campo(form, 'cadastros.vendedores.campo_nome', 'en')).toBeVisible();
    await botao(form, 'cadastros.vendedores.botao_cadastrar', 'en').click();
    await esperarErro(form, 'erros.50001', 'en');

    // um relatório em inglês
    await irPelaNavbar(page, 'Relatórios', 'en');
    const conteudo = await abrirAba(page, 'relatorios.abas.regiao', 'en');
    await expect(conteudo.getByTestId('stMetric').filter({ hasText: t('relatorios.total_geral', {}, 'en') })).toBeVisible();
    await expect(page.getByRole('tab', { name: t('relatorios.abas.comissao', {}, 'en') })).toBeVisible();

    // F5 mantém o inglês (o idioma vem do ?lang=en da URL)
    await recarregar(page);
    await expect(page).toHaveURL(/[?&]lang=en/);
    await expect(page.getByTestId('stTopNavLink').filter({ hasText: t('nav.relatorios', {}, 'en') })).toBeVisible();
    await expect(page.getByRole('tab', { name: t('relatorios.abas.regiao', {}, 'en') })).toBeVisible();

    // de volta ao português: a URL perde o ?lang
    await trocarIdioma(page, 'pt');
    await esperarStreamlit(page);
    await expect(page).not.toHaveURL(/lang=/);
    await expect(page.getByRole('tab', { name: t('relatorios.abas.regiao') })).toBeVisible();
    await expect(page.locator('.faixa-status')).toContainText(t('status.vendidos'));
  });
});
