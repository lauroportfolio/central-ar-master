/**
 * Textos da interface lidos dos MESMOS arquivos do app (locale/pt.json e locale/en.json).
 * Os testes não têm texto de tela fixo: se uma frase mudar no idioma, os testes acompanham.
 *
 *   t('cadastros.vendedores.editar', { id: 5 })      -> "Editar vendedor 5"
 *   t('nav.pedidos', {}, 'en')                       -> "Orders"
 *   padrao('pedidos.novo.cadastrado')                -> /Pedido nº .+ cadastrado — total .+\./
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { RAIZ } from './env';

export type Idioma = 'pt' | 'en';
type Parametros = Record<string, string | number>;

const arvores: Partial<Record<Idioma, any>> = {};

function arvore(idioma: Idioma): any {
  return (arvores[idioma] ??= JSON.parse(readFileSync(join(RAIZ, 'locale', `${idioma}.json`), 'utf-8')));
}

function bruto(chave: string, idioma: Idioma): string | undefined {
  const valor = chave.split('.').reduce((no: any, parte) => (no == null ? undefined : no[parte]), arvore(idioma));
  return typeof valor === 'string' ? valor : undefined;
}

/** A chave existe no idioma? (os helpers usam para aceitar "chave ou texto") */
export function ehChave(texto: string, idioma: Idioma = 'pt'): boolean {
  return /^[a-z_]+(\.[a-z0-9_]+)+$/.test(texto) && bruto(texto, idioma) !== undefined;
}

/** Texto da chave com {marcadores} preenchidos. Chave inexistente é erro do teste. */
export function t(chave: string, parametros: Parametros = {}, idioma: Idioma = 'pt'): string {
  const valor = bruto(chave, idioma);
  if (valor === undefined) throw new Error(`Chave de idioma inexistente em ${idioma}.json: ${chave}`);
  return valor.replace(/\{(\w+)\}/g, (marca, nome) => (nome in parametros ? String(parametros[nome]) : marca));
}

/** Aceita chave ou texto pronto: se for chave do idioma, traduz; senão devolve como veio. */
export function texto(chaveOuTexto: string, idioma: Idioma = 'pt'): string {
  return ehChave(chaveOuTexto, idioma) ? t(chaveOuTexto, {}, idioma) : chaveOuTexto;
}

/** RegExp do texto da chave: marcadores não informados viram ".+" (ex.: o nº de um pedido novo).
 *  Marcação markdown (**negrito**) é removida, como na tela. */
export function padrao(chave: string, parametros: Parametros = {}, idioma: Idioma = 'pt'): RegExp {
  const partes = t(chave, parametros, idioma).replace(/\*\*/g, '').split(/\{\w+\}/);
  return new RegExp(partes.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.+'));
}

/** Plural como no app: <chave>.um (n == 1) ou <chave>.outros. */
export function tPlural(chave: string, n: number, idioma: Idioma = 'pt'): string {
  return t(`${chave}.${n === 1 ? 'um' : 'outros'}`, { n }, idioma);
}

/** Lê o valor de um marcador num texto da tela, usando o modelo da chave.
 *  Ex.: capturar('pedidos.novo.cadastrado', 'id', 'Pedido nº 18 cadastrado — total R$ 3.299,00.') -> '18' */
export function capturar(chave: string, marcador: string, textoDaTela: string, idioma: Idioma = 'pt'): string {
  const escapar = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const modelo = t(chave, {}, idioma).replace(/\*\*/g, '');
  const fonte = modelo.split(/(\{\w+\})/).map((parte) => {
    const m = parte.match(/^\{(\w+)\}$/);
    if (!m) return escapar(parte);
    return m[1] === marcador ? '(.+?)' : '.+?';
  }).join('');
  const achou = textoDaTela.match(new RegExp(fonte));
  if (!achou) throw new Error(`"${textoDaTela}" não segue o modelo de ${chave}`);
  return achou[1];
}
