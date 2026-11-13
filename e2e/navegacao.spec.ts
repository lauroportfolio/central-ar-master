import { test, expect } from './helpers/fixtures';
import { abrir, irPelaNavbar, NomePagina, PAGINAS, scrollDePagina } from './helpers/app';

const RESOLUCOES = [
  { largura: 1920, altura: 1080 },
  { largura: 1366, altura: 768 },
  { largura: 1280, altura: 720 },
];

for (const { largura, altura } of RESOLUCOES) {
  test(`navegação: todas as telas abrem sem erro e sem scroll de página em ${largura}x${altura}`, async ({ page }) => {
    await page.setViewportSize({ width: largura, height: altura });
    await abrir(page, 'Início');
    const telas = [...(Object.keys(PAGINAS) as NomePagina[]).filter((n) => n !== 'Início'), 'Início' as NomePagina];

    for (const tela of telas) {
      await irPelaNavbar(page, tela);
      await expect(page.getByTestId('stException'), `exceção em ${tela}`).toHaveCount(0);
      await expect(page.getByTestId('stAlertContentError'), `erro em ${tela}`).toHaveCount(0);
      await expect.poll(() => scrollDePagina(page), { message: `scroll de página em ${tela}` })
        .toEqual({ documento: 0, principal: 0 });
    }
  });
}
