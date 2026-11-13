import { test, expect } from './helpers/fixtures';
import {
  abrir, coresDoPainel, escolherTema, irPelaNavbar, NomePagina, PAGINAS, recarregar, scrollDePagina,
} from './helpers/app';

const NAVBAR = 'rgb(15, 31, 61)';                  // azul-escuro nos dois temas
const TELAS = Object.keys(PAGINAS) as NomePagina[];

test.describe('Tema', () => {
  test('tema: alternar claro e escuro pelo menu ⋮', async ({ page }) => {
    await abrir(page, 'Início');
    await escolherTema(page, 'Light');
    const claro = await coresDoPainel(page);
    expect(claro.fundo).toBe('rgb(255, 255, 255)');
    expect(claro.navbar).toBe(NAVBAR);
    expect(claro.contraste).toBeGreaterThanOrEqual(4.5);

    await escolherTema(page, 'Dark');
    const escuro = await coresDoPainel(page);
    expect(escuro.fundo).toBe('rgb(17, 26, 40)');
    expect(escuro.navbar).toBe(NAVBAR);
    expect(escuro.contraste).toBeGreaterThanOrEqual(4.5);
    // o seletor Sistema/Claro/Escuro existe e o botão Deploy continua escondido
    await page.getByTestId('stMainMenuButton').click();
    await expect(page.getByTestId('stThemeSwitcher')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('stAppDeployButton')).toHaveCount(0);
  });

  for (const tema of ['Light', 'Dark'] as const) {
    test(`tema ${tema === 'Dark' ? 'escuro' : 'claro'}: todas as telas sem scroll de página e painéis legíveis`, async ({ page }) => {
      await abrir(page, 'Início');
      await escolherTema(page, tema);
      for (const tela of [...TELAS.filter((t) => t !== 'Início'), 'Início' as NomePagina]) {
        await irPelaNavbar(page, tela);
        await expect(page.getByTestId('stException')).toHaveCount(0);
        await expect.poll(() => scrollDePagina(page), { message: `scroll em ${tela}` })
          .toEqual({ documento: 0, principal: 0 });
        const cores = await coresDoPainel(page);
        expect(cores.contraste, `contraste do título em ${tela}`).toBeGreaterThanOrEqual(4.5);
      }
    });
  }

  test('tema escolhido continua depois do F5 em outra tela', async ({ page }) => {
    await abrir(page, 'Clientes');
    await escolherTema(page, 'Dark');
    await irPelaNavbar(page, 'Pedidos');
    await recarregar(page);
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'escuro');
    await irPelaNavbar(page, 'Relatórios');
    await recarregar(page);
    await expect(page.locator('html')).toHaveAttribute('data-tema', 'escuro');
  });
});
