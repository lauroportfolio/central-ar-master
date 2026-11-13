/**
 * Configuração dos testes E2E.
 *
 * A senha do sa é lida do .env do projeto (o mesmo do app, que está no .gitignore).
 * Nada de senha em arquivo versionado.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

export const RAIZ = join(__dirname, '..', '..');
export const BANCO_E2E = 'CentralDeAr_E2E';
export const PORTA_APP = 8502;

/** Lê KEY=valor do .env (ignora comentários e linhas vazias). */
function lerDotEnv(): Record<string, string> {
  const caminho = join(RAIZ, '.env');
  if (!existsSync(caminho)) return {};
  const valores: Record<string, string> = {};
  for (const linha of readFileSync(caminho, 'utf-8').split(/\r?\n/)) {
    const m = linha.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m && !linha.trimStart().startsWith('#')) valores[m[1]] = m[2].replace(/^(['"])(.*)\1$/, '$2');
  }
  return valores;
}

export function senhaSa(): string {
  const senha = process.env.DB_PASSWORD ?? lerDotEnv().DB_PASSWORD;
  if (!senha || senha === 'troque_aqui') {
    throw new Error('Defina DB_PASSWORD (senha do sa do container) no .env para rodar os testes E2E.');
  }
  return senha;
}
