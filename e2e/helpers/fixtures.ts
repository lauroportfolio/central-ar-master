/**
 * `test` com:
 * - `page`: a página do Playwright já monitorando o WebSocket do Streamlit (para saber
 *   quando um rerun aconteceu — ver comRerun em helpers/app.ts);
 * - `db`: conexão ao banco de teste, uma por worker;
 * - `travaBanco` (automática): trava COMPARTILHADA do banco de teste em todo teste;
 *   testes com a tag @exclusivo (o "fluxo completo") pegam a trava EXCLUSIVA e rodam sozinhos.
 * Os specs importam daqui: import { test, expect } from './helpers/fixtures';
 */
import { test as base, expect } from '@playwright/test';
import { monitorarStreamlit } from './app';
import { Banco, TravaBanco } from './db';

export const test = base.extend<{ travaBanco: void }, { db: Banco }>({
  travaBanco: [
    async ({}, use, testInfo) => {
      const trava = await TravaBanco.adquirir(testInfo.tags.includes('@exclusivo') ? 'Exclusive' : 'Shared');
      await use();
      await trava.liberar();
    },
    // tempo próprio: esperar o fluxo completo terminar não conta no tempo do teste
    { auto: true, timeout: 15 * 60_000 },
  ],
  page: async ({ page }, use) => {
    monitorarStreamlit(page);
    await use(page);
  },
  db: [
    async ({}, use) => {
      const banco = await Banco.abrir();
      await use(banco);
      await banco.fechar();
    },
    { scope: 'worker' },
  ],
});

export { expect };
