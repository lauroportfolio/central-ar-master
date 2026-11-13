/**
 * Ações na interface do app Streamlit.
 *
 * - Nada de waitForTimeout: a espera usa o atributo data-test-script-state do <stApp>
 *   ("running"/"notRunning") e as asserções com auto-wait do Playwright.
 * - Escopos estáveis: cada painel do app é um container com key "painel_..." e o
 *   Streamlit gera a classe .st-key-painel_... (ex.: .st-key-painel_form_clientes).
 * - Tabelas (st.dataframe) são desenhadas em canvas (glide-data-grid). Para LER usamos a
 *   tabela de acessibilidade escondida que o glide mantém no DOM (table[role=grid]);
 *   para SELECIONAR uma linha filtramos pela busca até sobrar 1 e clicamos na 1ª linha do canvas.
 */
import { expect, Locator, Page } from '@playwright/test';

// ------------------------------------------------------------------ navegação

export const PAGINAS = {
  'Início': '',
  Pedidos: 'pedidos',
  'Relatórios': 'relatorios',
  Vendedores: 'vendedores',
  'Regiões': 'regioes',
  Clientes: 'clientes',
  Produtos: 'produtos',
} as const;
export type NomePagina = keyof typeof PAGINAS;
const CADASTROS: NomePagina[] = ['Vendedores', 'Regiões', 'Clientes', 'Produtos'];

// Limite (não é espera fixa: as esperas terminam assim que a condição vale). Telas pesadas,
// como Relatórios com muitos vendedores, podem levar mais de 15 s com 6 navegadores em paralelo.
const LIMITE_EXECUCAO = 60_000;

/** Espera o Streamlit ficar ocioso: conectado, script parado e nada "stale" na tela. */
export async function esperarStreamlit(page: Page): Promise<void> {
  const app = page.getByTestId('stApp');
  await expect(app).toHaveAttribute('data-test-connection-state', 'CONNECTED', { timeout: LIMITE_EXECUCAO });
  await expect(app).toHaveAttribute('data-test-script-state', 'notRunning', { timeout: LIMITE_EXECUCAO });
  await expect(page.locator('[data-stale="true"]')).toHaveCount(0, { timeout: LIMITE_EXECUCAO });
}

// Tráfego do WebSocket do Streamlit, por página (ver monitorarStreamlit).
// `seq` é um relógio único: cada mensagem enviada/recebida ganha o próximo número.
type Trafego = { seq: number; ultimaEnviada: number; ultimaRecebida: number };
const trafego = new WeakMap<Page, Trafego>();

/**
 * Registra a ORDEM das mensagens do WebSocket do Streamlit (enviadas pelo navegador e
 * recebidas do servidor). Uma ação que dispara rerun ENVIA um pedido ao servidor; a
 * execução do script RESPONDE com mensagens. "Recebi algo depois do meu pedido" prova
 * que o rerun aconteceu — mesmo quando é tão rápido que "running" nem aparece no DOM —
 * e mensagens atrasadas de execuções anteriores não enganam a espera.
 * Instalado para todo teste pela fixture `page` (helpers/fixtures.ts).
 */
export function monitorarStreamlit(page: Page): void {
  const t: Trafego = { seq: 0, ultimaEnviada: 0, ultimaRecebida: 0 };
  trafego.set(page, t);
  page.on('websocket', (ws) => {
    ws.on('framesent', () => { t.ultimaEnviada = ++t.seq; });
    ws.on('framereceived', () => { t.ultimaRecebida = ++t.seq; });
  });
}

/**
 * Executa uma ação que dispara um rerun do Streamlit e espera ele terminar.
 * Sinais de que o rerun aconteceu (basta um): o servidor respondeu DEPOIS de um pedido
 * enviado depois da ação, ou o MutationObserver viu o estado "running".
 * Depois espera o app ficar ocioso.
 */
export async function comRerun(page: Page, acao: () => Promise<unknown>): Promise<void> {
  const t = trafego.get(page);
  const marco = t?.seq ?? 0;
  await page.evaluate(() => {
    const w = window as any;
    const app = document.querySelector('[data-testid="stApp"]')!;
    w.__e2eRodou = false;
    w.__e2eObs?.disconnect();
    w.__e2eObs = new MutationObserver(() => {
      if (app.getAttribute('data-test-script-state') === 'running') w.__e2eRodou = true;
    });
    w.__e2eObs.observe(app, { attributes: true, attributeFilter: ['data-test-script-state'] });
  });
  await acao();
  await expect.poll(
    async () => (!!t && t.ultimaEnviada > marco && t.ultimaRecebida > t.ultimaEnviada)
      || await page.evaluate(() => (window as any).__e2eRodou === true),
    { message: 'o Streamlit não rodou o script depois da ação', timeout: 30_000 },
  ).toBe(true);
  await esperarStreamlit(page);
}

/** Abre o app e navega pela NAVBAR até a tela (como um usuário faria). */
export async function abrir(page: Page, nome: NomePagina): Promise<void> {
  await page.goto('/');
  await expect(page.getByTestId('stTopNav')).toBeVisible();
  await expect(page.locator('.faixa-status')).toBeVisible();
  await esperarStreamlit(page);
  if (nome !== 'Início') await irPelaNavbar(page, nome);
}

/** Recarrega a tela atual (ex.: para o formulário enxergar dados criados pelo teste)
 *  e espera o Streamlit terminar — senão o primeiro render pode zerar o que o teste preencheu. */
export async function recarregar(page: Page): Promise<void> {
  await page.reload();
  await expect(page.getByTestId('stTopNav')).toBeVisible();
  await expect(page.locator('.faixa-status')).toBeVisible();
  await esperarStreamlit(page);
}

export async function irPelaNavbar(page: Page, nome: NomePagina): Promise<void> {
  if (CADASTROS.includes(nome)) {
    await page.getByTestId('stTopNavSection').click();
    await comRerun(page, () => page.getByTestId('stTopNavDropdownLink').filter({ hasText: nome }).click());
  } else {
    await comRerun(page, () => page.getByTestId('stTopNavLink').filter({ hasText: nome }).click());
  }
  await expect(page).toHaveURL(new RegExp(`/${PAGINAS[nome]}$`));
}

/** Painel do app pelo key (ex.: painel(page, 'form_clientes') -> .st-key-painel_form_clientes). */
export function painel(page: Page, chave: string): Locator {
  return page.locator(`.st-key-painel_${chave}`);
}

// ------------------------------------------------------------------ formulários

export function campo(escopo: Locator, rotulo: string): Locator {
  return escopo.getByLabel(rotulo, { exact: true });
}

export async function preencher(escopo: Locator, valores: Record<string, string | number>): Promise<void> {
  for (const [rotulo, valor] of Object.entries(valores)) {
    await campo(escopo, rotulo).fill(String(valor));
  }
}

/**
 * Abre o selectbox, digita para filtrar e clica na opção. Confere que o campo passou a
 * mostrar o RÓTULO COMPLETO da opção (ex.: "5 — E2E Vendedor xyz"): o texto digitado
 * sozinho não prova a seleção. Se o clique não "pegou", tenta de novo.
 */
async function selecionarOpcao(page: Page, caixa: Locator, texto: string, aoClicar?: (clique: () => Promise<void>) => Promise<void>) {
  await expect(async () => {
    await caixa.click();
    await caixa.fill(texto);
    const opcao = page.getByRole('option').filter({ hasText: texto }).first();
    await expect(opcao).toBeVisible({ timeout: 3_000 });
    const rotuloCompleto = (await opcao.innerText()).trim();
    const clique = () => opcao.click();
    await (aoClicar ? aoClicar(clique) : clique());
    await expect(caixa).toHaveValue(rotuloCompleto, { timeout: 3_000 });
  }).toPass({ timeout: LIMITE_EXECUCAO + 30_000 });
}

/** Escolhe uma opção num selectbox dentro de formulário (não dispara rerun). */
export async function escolher(page: Page, escopo: Locator, rotulo: string, texto: string): Promise<void> {
  await selecionarOpcao(page, campo(escopo, rotulo), texto);
}

/** Escolhe opção num selectbox que fica FORA de formulário (dispara rerun).
 *  Se a opção já é a escolhida, não faz nada (o Streamlit não rodaria de novo). */
export async function escolherComRerun(page: Page, escopo: Locator, rotulo: string, texto: string): Promise<void> {
  const caixa = campo(escopo, rotulo);
  if ((await caixa.inputValue()).includes(texto)) return;
  await selecionarOpcao(page, caixa, texto, (clique) => comRerun(page, clique));
}

export function botao(escopo: Locator, nome: string): Locator {
  return escopo.getByRole('button', { name: nome, exact: true });
}

/** Clica num botão que grava/consulta (dispara rerun) e espera terminar. */
export async function clicar(page: Page, escopo: Locator, nome: string): Promise<void> {
  await comRerun(page, () => botao(escopo, nome).click());
}

export async function esperarToast(page: Page, texto: string | RegExp): Promise<string> {
  const toast = page.getByTestId('stToast').filter({ hasText: texto }).first();
  await expect(toast).toBeVisible();
  return (await toast.innerText()).trim();
}

export async function esperarErro(escopo: Locator, texto: string | RegExp): Promise<void> {
  await expect(escopo.getByTestId('stAlertContentError').filter({ hasText: texto }).first()).toBeVisible();
}

/** Marca "Confirmo que quero excluir..." e clica em "Excluir <entidade>". */
export async function excluirComConfirmacao(page: Page, escopo: Locator, entidade: string): Promise<void> {
  await escopo.getByText(`Confirmo que quero excluir este ${entidade}`).click();
  await clicar(page, escopo, `Excluir ${entidade}`);
}

// ------------------------------------------------------------------ tabelas (st.dataframe)

/** Linhas de dados (DOM de acessibilidade do glide-data-grid) da N-ésima tabela do escopo.
 *  Atenção: esse DOM guarda os valores BRUTOS (6.5, 2848.1), sem a formatação R$/% da tela. */
export function linhasDaTabela(escopo: Locator, indice = 0): Locator {
  return escopo.getByTestId('stDataFrame').nth(indice).locator('table[role="grid"] tbody tr[role="row"]');
}

/**
 * Encontra a linha da tabela que contém o texto. O DOM de acessibilidade só tem as linhas
 * VISÍVEIS do grid; se a linha não estiver na tela, rola o grid com a roda do mouse até
 * ela aparecer (ou o grid chegar ao fim). Devolve o Locator da linha (exatamente 1).
 */
export async function encontrarLinha(page: Page, escopo: Locator, texto: string, indice = 0): Promise<Locator> {
  const grade = escopo.getByTestId('stDataFrame').nth(indice);
  const linhas = linhasDaTabela(escopo, indice);
  const linha = linhas.filter({ hasText: texto });
  await expect(grade).toBeVisible();
  await expect.poll(() => linhas.count(), { message: 'a tabela não carregou' }).toBeGreaterThan(0);
  const ultimaVisivel = () => linhas.last().getAttribute('aria-rowindex');

  for (let rolagens = 0; rolagens < 40 && (await linha.count()) === 0; rolagens++) {
    const antes = await ultimaVisivel();
    const caixa = (await grade.boundingBox())!;
    await page.mouse.move(caixa.x + caixa.width / 2, caixa.y + caixa.height / 2);
    await page.mouse.wheel(0, caixa.height * 0.6);
    try {
      // espera o grid redesenhar (linha apareceu ou a janela de linhas andou)
      await expect.poll(async () => (await linha.count()) > 0 || (await ultimaVisivel()) !== antes,
        { timeout: 3_000 }).toBe(true);
    } catch {
      break;   // não andou mais: chegou ao fim da tabela
    }
  }
  await expect(linha, `linha com "${texto}" na tabela`).toHaveCount(1);
  return linha;
}

/** Textos das células de uma linha (valores brutos do grid). */
export async function celulas(linha: Locator): Promise<string[]> {
  await expect(linha).toHaveCount(1);
  return (await linha.locator('td').allInnerTexts()).map((t) => t.trim());
}

/** Digita na busca do painel e confirma (Enter dispara o rerun que filtra a tabela).
 *  Se a busca já tem esse texto, o Streamlit não roda de novo: só espera ficar ocioso. */
export async function buscar(page: Page, escopo: Locator, termo: string): Promise<void> {
  const busca = escopo.getByPlaceholder(/^Buscar/);
  if ((await busca.inputValue()) === termo) {
    await esperarStreamlit(page);
    return;
  }
  await busca.fill(termo);
  await comRerun(page, () => busca.press('Enter'));
}

// Medidas padrão do glide-data-grid no Streamlit: cabeçalho e linhas com 35 px;
// a 1ª coluna é a das caixinhas de seleção.
const ALTURA_LINHA = 35;
const X_SELECAO = 16;

/**
 * Busca pelo termo, garante que sobrou exatamente 1 linha e a seleciona
 * (clique na caixinha de seleção da 1ª linha de dados do canvas).
 */
export async function selecionarPorBusca(page: Page, escopo: Locator, termo: string): Promise<void> {
  await buscar(page, escopo, termo);
  const linhas = linhasDaTabela(escopo);
  await expect(linhas).toHaveCount(1);
  await expect(linhas.first()).toContainText(termo);
  const grade = escopo.getByTestId('stDataFrame').first();
  await expect(grade).toBeVisible();
  const caixa = (await grade.boundingBox())!;
  await comRerun(page, () => page.mouse.click(caixa.x + X_SELECAO, caixa.y + ALTURA_LINHA + ALTURA_LINHA / 2));
  await expect(linhas.first()).toHaveAttribute('aria-selected', 'true');
  // confirmação na tela: abriu o formulário de edição ("Editar ...") ou o pedido ("Pedido nº ...")
  await expect(page.locator('.painel-titulo').filter({ hasText: /^(Editar |Pedido nº )/ })).toBeVisible();
  await esperarStreamlit(page);
}

// ------------------------------------------------------------------ pedido novo (st.data_editor)

/**
 * Adiciona um produto ao editor de itens do pedido novo: clica na linha "adicionar"
 * do canvas (abre a lista de produtos da nova linha), digita o nome e confirma.
 */
export async function adicionarItemNoEditor(page: Page, escopo: Locator, produto: string, linhasAtuais: number): Promise<void> {
  const editor = escopo.getByTestId('stDataFrame').first();
  const caixa = (await editor.boundingBox())!;
  await page.mouse.click(caixa.x + 200, caixa.y + ALTURA_LINHA * (linhasAtuais + 1) + ALTURA_LINHA / 2);
  await expect(page.getByRole('option').filter({ hasText: produto }).first()).toBeVisible();
  await page.keyboard.type(produto);
  await comRerun(page, () => page.keyboard.press('Enter'));
  // o resumo abaixo do editor passa a listar o produto
  await expect(linhasDaTabela(escopo, 1).filter({ hasText: produto })).toHaveCount(1);
}

/** Espera o destaque de TOTAL do pedido mostrar o valor (com auto-wait: a tela pode
 *  ainda estar no segundo rerun depois de gravar). */
export async function esperarTotalEmDestaque(escopo: Locator, valor: number): Promise<void> {
  await expect(escopo.locator('.total-destaque strong')).toHaveText(brl(valor));
}

export function paraNumero(textoBr: string): number {
  return Number(textoBr.replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.'));
}

export function brl(valor: number): string {
  return 'R$ ' + valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ------------------------------------------------------------------ layout

/** Diferença entre altura do conteúdo e da janela (0 = sem scroll de página). */
export async function scrollDePagina(page: Page): Promise<{ documento: number; principal: number }> {
  return page.evaluate(() => {
    const d = document.scrollingElement!;
    const m = document.querySelector('[data-testid="stMain"]')!;
    return { documento: d.scrollHeight - d.clientHeight, principal: m.scrollHeight - m.clientHeight };
  });
}
