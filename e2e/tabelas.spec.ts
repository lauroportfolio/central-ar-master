import { Locator, Page } from '@playwright/test';
import { test, expect } from './helpers/fixtures';
import { t } from './helpers/textos';
import { cpfUnico, sufixo } from './helpers/db';
import {
  abrir, abrirAba, adicionarItemNoEditor, buscar, campo, escolherComRerun, escolherTema, esperarStreamlit,
  estiloDoBalao, fecharBaloes, irPelaNavbar, larguraEsperada, linhasDaTabela, painel, passarMouse,
  selecionarPorBusca, trocarIdioma,
} from './helpers/app';

/**
 * Tabelas e textos longos:
 *  - nenhuma tabela com scroll horizontal (1920x1080, 1366x768, 1280x720);
 *  - a barra de rolagem vertical do grid não cobre a última coluna;
 *  - textos longos com "…" (no grid e nos elementos HTML), texto completo no tooltip
 *    (HTML) ou no formulário (grid); texto curto não ganha tooltip.
 *
 * Este arquivo roda com as barras de rolagem REAIS do Chromium: o Playwright esconde as
 * barras por padrão (--hide-scrollbars), e aí não haveria barra para cobrir nada.
 */
test.use({
  launchOptions: { slowMo: Number(process.env.SLOW_MO ?? 0), ignoreDefaultArgs: ['--hide-scrollbars'] },
});

const RESOLUCOES = [
  { width: 1920, height: 1080 },
  { width: 1366, height: 768 },
  { width: 1280, height: 720 },
];

/** Abre a tela já na resolução pedida (o app recebe a largura da janela e refaz as colunas). */
async function abrirEm(page: Page, tamanho: { width: number; height: number }, nome: Parameters<typeof abrir>[1]) {
  await page.setViewportSize(tamanho);
  await abrir(page, nome);
}

/** Grids visíveis com scroll horizontal: "rótulo: largura do conteúdo > largura visível". */
async function gridsComScrollHorizontal(page: Page, onde: string): Promise<string[]> {
  await esperarStreamlit(page);
  await expect(page.getByTestId('stDataFrame').filter({ visible: true }).first(), `${onde}: tabela na tela`)
    .toBeVisible();
  return page.$$eval('[data-testid="stDataFrame"]', (els, onde) => els
    .filter((e) => (e as HTMLElement).offsetParent && e.getBoundingClientRect().width > 0)
    .map((e, i) => {
      const s = e.querySelector('.dvn-scroller') as HTMLElement;
      return s && s.scrollWidth > s.clientWidth + 1 ? `${onde} #${i}: ${s.scrollWidth} > ${s.clientWidth}` : '';
    })
    .filter(Boolean), onde);
}

/**
 * Pixels de texto (escuros) no canvas do grid, numa faixa vertical das linhas de dados.
 * `daDireita`: distância (px CSS) da borda direita do canvas até o fim da faixa.
 */
async function pixelsDeTexto(grade: Locator, largura: number, daDireita = 0): Promise<number> {
  return grade.evaluate((el, { largura, daDireita }) => {
    const canvas = el.querySelector('canvas[data-testid="data-grid-canvas"]') as HTMLCanvasElement;
    const escala = canvas.width / canvas.getBoundingClientRect().width;
    const ctx = canvas.getContext('2d')!;
    const x0 = Math.round(canvas.width - (daDireita + largura) * escala);
    const y0 = Math.round(36 * escala);                                  // abaixo do cabeçalho
    const dados = ctx.getImageData(x0, y0, Math.round(largura * escala), canvas.height - y0).data;
    let escuros = 0;
    for (let i = 0; i < dados.length; i += 4) {
      const luminancia = 0.299 * dados[i] + 0.587 * dados[i + 1] + 0.114 * dados[i + 2];
      if (dados[i + 3] > 0 && luminancia < 140) escuros++;
    }
    return escuros;
  }, { largura, daDireita });
}

/** Estado do balão do texto cortado (::after do .corte). */
async function balaoDoCorte(el: Locator) {
  return el.evaluate((e) => {
    const cs = getComputedStyle(e, '::after');
    return { conteudo: cs.content, opacidade: cs.opacity, visivel: cs.visibility,
             fundo: cs.backgroundColor, cor: cs.color, fonte: cs.fontSize, padding: cs.padding,
             raio: cs.borderRadius, sombra: cs.boxShadow, larguraMax: cs.maxWidth };
  });
}

/** Passa o mouse e espera o balão do texto cortado aparecer com o texto completo. */
async function conferirBalaoDoCorte(page: Page, el: Locator, textoCompleto: string) {
  await expect(el, 'texto marcado como cortado').toHaveAttribute('data-cortado', '');
  await expect(el.locator('.corte-texto')).toHaveText(textoCompleto);           // o DOM tem o texto inteiro
  await passarMouse(page, el.locator('.corte-texto'));
  await expect.poll(async () => (await balaoDoCorte(el)).opacidade, { message: 'balão visível' }).toBe('1');
  const balao = await balaoDoCorte(el);
  expect(balao.conteudo).toBe(JSON.stringify(textoCompleto));
  expect(balao.visivel).toBe('visible');
  return balao;
}

test.describe('Tabelas e textos longos', () => {
  test('nenhuma tabela tem scroll horizontal em 1920x1080, 1366x768 e 1280x720', async ({ page, db }) => {
    test.setTimeout(240_000);
    const s = sufixo();
    const c = await db.criarCenario(s);
    const idProduto = await db.criarProduto(`E2E Produto Tabelas ${s}`, 100, 50);
    await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto, quantidade: 1 }]);

    const problemas: string[] = [];
    for (const tamanho of RESOLUCOES) {
      const r = `${tamanho.width}x${tamanho.height}`;
      for (const tela of ['Vendedores', 'Regiões', 'Clientes', 'Produtos'] as const) {
        await abrirEm(page, tamanho, tela);
        problemas.push(...await gridsComScrollHorizontal(page, `${r} ${tela}`));
      }

      // Pedidos: lista + itens de um pedido + resumo do pedido novo
      await abrirEm(page, tamanho, 'Pedidos');
      const lista = painel(page, 'lista_pedidos');
      await selecionarPorBusca(page, lista, c.cliente);
      problemas.push(...await gridsComScrollHorizontal(page, `${r} Pedidos (lista e itens)`));
      await page.getByRole('button', { name: t('pedidos.botao_novo') }).click();
      await esperarStreamlit(page);
      const corpo = painel(page, 'pedido_corpo');
      await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', c.cliente);
      await adicionarItemNoEditor(page, corpo, `E2E Produto Tabelas ${s}`, 0);
      await expect(corpo.getByTestId('stDataFrame')).toHaveCount(2);
      problemas.push(...await gridsComScrollHorizontal(page, `${r} Pedido novo (resumo)`));

      // Relatórios: todas as abas
      await irPelaNavbar(page, 'Relatórios');
      for (const aba of ['regiao', 'cliente', 'vendedor', 'clientes_regiao', 'produto', 'comissao']) {
        const conteudo = await abrirAba(page, `relatorios.abas.${aba}`);
        if (aba === 'clientes_regiao') {
          await escolherComRerun(page, conteudo, 'relatorios.campo_regiao', c.regiao);
        }
        problemas.push(...await gridsComScrollHorizontal(page, `${r} Relatórios/${aba}`));
      }
    }
    expect(problemas, 'tabelas com scroll horizontal').toEqual([]);
  });

  test('a barra de rolagem vertical não cobre a última coluna (Total da lista de pedidos)', async ({ page, db }) => {
    // pedidos suficientes para a lista ter barra de rolagem até em 1920x1080
    const c = await db.criarCenario(sufixo());
    const idProduto = await db.criarProduto(`E2E Produto Barra ${sufixo()}`, 1234.56, 100);
    for (let i = 0; i < 20; i++) await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto, quantidade: 1 }]);

    for (const tamanho of RESOLUCOES) {
      await abrirEm(page, tamanho, 'Pedidos');
      const grade = painel(page, 'lista_pedidos').getByTestId('stDataFrame');
      await expect(grade).toBeVisible();
      await expect(linhasDaTabela(painel(page, 'lista_pedidos')).first()).toBeAttached();
      const barra = await grade.locator('.dvn-scroller').evaluate((s) => (s as HTMLElement).offsetWidth - (s as HTMLElement).clientWidth);
      expect(barra, `${tamanho.width}: a lista de pedidos tem barra de rolagem vertical`).toBeGreaterThan(0);

      // a faixa onde a barra é desenhada (com a barra transparente, para enxergar o que há embaixo)
      await page.addStyleTag({ content: '.dvn-scroller { scrollbar-color: transparent transparent !important; }' });
      await page.mouse.move(2, 2);
      const sobABarra = await pixelsDeTexto(grade, barra + 1);
      // controle: logo à esquerda da barra há texto (os valores do Total), então o método enxerga texto
      const aoLado = await pixelsDeTexto(grade, 40, barra + 4);
      expect(aoLado, `${tamanho.width}: há valores na coluna Total`).toBeGreaterThan(20);
      expect(sobABarra, `${tamanho.width}: nenhum pixel de texto embaixo da barra`).toBe(0);
    }
  });

  test('toolbar do grid não cobre a busca: só restam os botões do editor de itens', async ({ page }) => {
    await abrir(page, 'Pedidos');
    const lista = painel(page, 'lista_pedidos');
    const grade = lista.getByTestId('stDataFrame');
    await passarMouse(page, grade);
    await expect(grade.getByTestId('stElementToolbar')).toBeHidden();

    // pedido selecionado: o botão "limpar seleção" também não aparece por cima da busca
    await selecionarPorBusca(page, lista, 'Hotel');
    await passarMouse(page, grade);
    await expect(grade.getByTestId('stElementToolbar')).toBeHidden();

    // o editor de itens do pedido novo continua com o botão de adicionar linha
    await page.getByRole('button', { name: t('pedidos.botao_novo') }).click();
    await esperarStreamlit(page);
    const corpo = painel(page, 'pedido_corpo');
    await escolherComRerun(page, corpo, 'pedidos.novo.campo_cliente', 'Hotel');
    const editor = corpo.getByTestId('stDataFrame').first();
    await passarMouse(page, editor);
    const botoes = editor.getByTestId('stElementToolbarButton').filter({ visible: true });
    await expect(botoes).toHaveCount(1);
    await expect(botoes.locator('button')).toHaveAttribute('aria-label', 'Add row');
  });

  test('endereço longo no grid sai com "…" e o texto completo aparece no formulário', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const nome = `E2E Endereço ${s}`;
    const endereco = `Avenida Engenheiro Luís Carlos Berrini, 1748, Conjunto 1203, Torre Norte, Cidade Monções, ` +
                     `São Paulo - SP, CEP 04571-000 (ref. ${s})`;
    await db.criarCliente(nome, cpfUnico(), c.idRegiao, { endereco, email: `contato.${s}@exemplo.test` });

    // o que o servidor manda para o grid: o valor exibido (cortado com "…") vai junto com o dado
    const recebido: Buffer[] = [];
    page.on('websocket', (ws) => ws.on('framereceived', (f) => {
      if (typeof f.payload !== 'string') recebido.push(f.payload);
    }));
    await abrirEm(page, { width: 1280, height: 720 }, 'Clientes');
    const lista = painel(page, 'lista_clientes');
    await buscar(page, lista, nome);
    await expect(linhasDaTabela(lista)).toHaveCount(1);

    // DOM de acessibilidade do grid (leitor de tela): o endereço inteiro
    await expect(linhasDaTabela(lista).first()).toContainText(endereco);
    // na tela: um começo do endereço + "…" (o texto inteiro não cabe na coluna)
    const textos = recebido.map((b) => b.toString('utf8'));
    const comecos = Array.from({ length: endereco.length - 4 }, (_, n) => endereco.slice(0, n + 4).trimEnd() + '…');
    expect(textos.some((txt) => comecos.some((c) => txt.includes(c))), 'valor exibido no grid com "…"').toBe(true);

    // clicando na linha, o formulário mostra o endereço completo
    await selecionarPorBusca(page, lista, nome);
    const form = painel(page, 'form_clientes');
    await expect(campo(form, 'comum.endereco')).toHaveValue(endereco);
  });

  test('texto HTML longo: "…" + tooltip com o texto completo; texto curto: sem tooltip', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const longo = `E2E Cliente com Razão Social Muito Comprida Indústria e Comércio de Climatização ${s}`;
    const idLongo = await db.criarCliente(longo, cpfUnico(), c.idRegiao);
    const idProduto = await db.criarProduto(`E2E Produto Corte ${s}`, 10, 50);
    const pedidoLongo = await db.criarPedido(idLongo, c.idVendedor, [{ idProduto, quantidade: 1 }]);
    const pedidoCurto = await db.criarPedido(c.idCliente, c.idVendedor, [{ idProduto, quantidade: 1 }]);

    await abrirEm(page, { width: 1366, height: 768 }, 'Início');
    const ultimos = painel(page, 'ultimos');

    // (c) card com nome longo: "…" e o tooltip com o texto completo
    const tituloLongo = t('inicio.item_titulo', { id: pedidoLongo, cliente: longo });
    const corteLongo = ultimos.locator('.cliente .corte').filter({ hasText: tituloLongo });
    const balao = await conferirBalaoDoCorte(page, corteLongo, tituloLongo);
    await expect(corteLongo.locator('.corte-texto')).toHaveCSS('text-overflow', 'ellipsis');
    // sobre o texto cortado, o tooltip do card (comissão do pedido) não aparece junto
    await expect(corteLongo.locator('xpath=ancestor::*[contains(@class,"com-dica")][1]/*[contains(@class,"dica")]'))
      .toBeHidden();
    // o mesmo visual dos outros tooltips do app (.dica)
    const estiloDica = await estiloDoBalao(page.locator('.faixa-status .com-dica .dica').first());
    expect({ fundo: balao.fundo, cor: balao.cor, fonte: balao.fonte, padding: balao.padding, raio: balao.raio,
             sombra: balao.sombra, larguraMax: balao.larguraMax }).toEqual(estiloDica);
    await fecharBaloes(page);

    // (d) card com nome curto: não está cortado, então não há tooltip nem foco pelo teclado
    const tituloCurto = t('inicio.item_titulo', { id: pedidoCurto, cliente: c.cliente });
    const corteCurto = ultimos.locator('.cliente .corte').filter({ hasText: tituloCurto });
    await expect(corteCurto).toBeVisible();
    await expect(corteCurto).not.toHaveAttribute('data-cortado');
    await expect(corteCurto).not.toHaveAttribute('tabindex');
    await passarMouse(page, corteCurto.locator('.corte-texto'));
    expect((await balaoDoCorte(corteCurto)).conteudo).toBe('none');
    await fecharBaloes(page);

    // ficha do pedido e subtítulo do formulário: o nome longo também é cortado com tooltip
    await irPelaNavbar(page, 'Pedidos');
    await selecionarPorBusca(page, painel(page, 'lista_pedidos'), longo);
    await conferirBalaoDoCorte(page, painel(page, 'pedido').locator('.ficha .corte').filter({ hasText: longo }), longo);
    await fecharBaloes(page);

    // recalcula ao redimensionar: na tela larga o mesmo título cabe e o tooltip some
    await page.setViewportSize({ width: 3840, height: 1080 });
    await esperarStreamlit(page);
    const ficha = painel(page, 'pedido').locator('.ficha .corte').filter({ hasText: longo });
    await expect(ficha).not.toHaveAttribute('data-cortado');
    await page.setViewportSize({ width: 1366, height: 768 });
    await esperarStreamlit(page);
    await expect(ficha).toHaveAttribute('data-cortado', '');
  });

  test('texto cortado funciona no tema escuro e em inglês', async ({ page, db }) => {
    const s = sufixo();
    const c = await db.criarCenario(s);
    const longo = `E2E Customer With a Remarkably Long Corporate Name for Air Conditioning Services ${s}`;
    const idLongo = await db.criarCliente(longo, cpfUnico(), c.idRegiao);
    const idProduto = await db.criarProduto(`E2E Produto Corte EN ${s}`, 10, 50);
    const pedido = await db.criarPedido(idLongo, c.idVendedor, [{ idProduto, quantidade: 1 }]);

    await abrirEm(page, { width: 1280, height: 720 }, 'Início');
    await escolherTema(page, 'Dark');
    await trocarIdioma(page, 'en');
    const titulo = t('inicio.item_titulo', { id: pedido, cliente: longo }, 'en');
    const corte = painel(page, 'ultimos').locator('.cliente .corte').filter({ hasText: titulo });
    const balao = await conferirBalaoDoCorte(page, corte, titulo);
    expect(balao).toMatchObject({ fundo: 'rgb(248, 250, 252)', cor: 'rgb(15, 23, 42)' });
  });
});

test('o app recebe a largura da janela', async ({ page }) => {
  await abrirEm(page, { width: 1366, height: 768 }, 'Início');
  await expect(page.locator('#largura-janela')).toHaveAttribute('data-largura', String(larguraEsperada(page)));
});
