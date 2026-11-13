/**
 * Recria o banco de TESTE (CentralDeAr_E2E) no container antes da suíte:
 * DROP se existir e roda 00_schema_reconstruido.sql, 01_complemento.sql e 02_seed.sql
 * com o nome do banco trocado só em memória. Os arquivos .sql e o banco CentralDeAr
 * não são tocados.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import sql from 'mssql';
import { BANCO_E2E, RAIZ, senhaSa } from './helpers/env';

const SCRIPTS = ['00_schema_reconstruido.sql', '01_complemento.sql', '02_seed.sql'];

/** Divide um script T-SQL nos lotes separados por GO (como o SSMS/sqlcmd fazem). */
function lotes(script: string): string[] {
  return script
    .replace(/^﻿/, '')
    .split(/^\s*GO\s*$/im)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
}

export default async function globalSetup(): Promise<void> {
  if (BANCO_E2E === 'CentralDeAr') throw new Error('O banco de teste não pode ser o banco real.');

  // max: 1 -> uma única conexão, para o "USE banco" de um lote valer para os próximos
  const pool = await new sql.ConnectionPool({
    server: 'localhost',
    port: 1433,
    user: 'sa',
    password: senhaSa(),
    database: 'master',
    options: { encrypt: true, trustServerCertificate: true },
    pool: { max: 1, min: 0 },
    requestTimeout: 120_000,
  }).connect();

  try {
    await pool.request().batch(`
      IF DB_ID('${BANCO_E2E}') IS NOT NULL
      BEGIN
          ALTER DATABASE [${BANCO_E2E}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
          DROP DATABASE [${BANCO_E2E}];
      END`);

    for (const arquivo of SCRIPTS) {
      const original = readFileSync(join(RAIZ, 'sql', arquivo), 'utf-8');
      const script = original.replace(/\bCentralDeAr\b/g, BANCO_E2E); // só em memória
      for (const lote of lotes(script)) {
        await pool.request().batch(lote);
      }
    }

    const r = await pool.request().query(`SELECT COUNT(*) AS n FROM [${BANCO_E2E}].dbo.PEDIDO`);
    console.log(`[e2e] banco ${BANCO_E2E} recriado com o seed (${r.recordset[0].n} pedidos).`);
  } finally {
    await pool.close();
  }
}
