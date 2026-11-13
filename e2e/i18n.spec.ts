/**
 * Verificações automáticas de tradução (não abrem o navegador).
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test, expect } from './helpers/fixtures';
import { RAIZ } from './helpers/env';

function achatar(arvore: Record<string, unknown>, prefixo = ''): Record<string, string> {
  return Object.entries(arvore).reduce((saida, [chave, valor]) => {
    const caminho = prefixo ? `${prefixo}.${chave}` : chave;
    return typeof valor === 'object' && valor !== null
      ? { ...saida, ...achatar(valor as Record<string, unknown>, caminho) }
      : { ...saida, [caminho]: String(valor) };
  }, {} as Record<string, string>);
}

const ler = (idioma: string) => achatar(JSON.parse(readFileSync(join(RAIZ, 'locale', `${idioma}.json`), 'utf-8')));

test.describe('Idioma (arquivos)', () => {
  test('idioma: pt.json e en.json têm exatamente as mesmas chaves e marcadores', () => {
    const pt = ler('pt');
    const en = ler('en');
    expect(Object.keys(en).sort()).toEqual(Object.keys(pt).sort());
    const marcadores = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const chave of Object.keys(pt)) {
      expect(marcadores(en[chave]), `marcadores de ${chave}`).toEqual(marcadores(pt[chave]));
    }
  });

  test('idioma: nenhuma string de tela fora dos arquivos de idioma (varredura AST)', async ({}, testInfo) => {
    let saida = '';
    let codigo = 0;
    try {
      saida = execFileSync(join(RAIZ, '.venv/bin/python'), ['ferramentas/verificar_i18n.py'], { cwd: RAIZ, encoding: 'utf-8' });
    } catch (erro: any) {
      saida = `${erro.stdout ?? ''}${erro.stderr ?? ''}`;
      codigo = erro.status ?? 1;
    }
    await testInfo.attach('verificar_i18n.txt', { body: saida, contentType: 'text/plain' });
    expect(codigo, saida).toBe(0);
    expect(saida).toContain('0 string(s) visível(is) fora do idioma');
  });
});
