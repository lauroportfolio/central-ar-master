# Central de Ar Ltda. — Sistema de Vendas

Trabalho de Banco de Dados: sistema do setor de vendas da **Central de Ar Ltda.**
O banco é SQL Server e o aplicativo abre no navegador (Python + Streamlit).

- Cadastro de **vendedores, regiões, clientes e produtos**
- **Pedidos** com vários itens, comissão do vendedor **definida em cada pedido**
- **Região fechada**: cada região é atendida por um único vendedor
- **Relatórios**: total por região, por cliente, por vendedor, por produto,
  clientes de uma região e **extrato de comissão de cada vendedor separado por produto**

> **Regra do professor:** toda inclusão, alteração, exclusão e consulta é feita por
> **stored procedure**. O aplicativo nunca acessa as tabelas diretamente; ele só executa
> `EXEC usp_...` (veja a pasta `dados/`). Todas as tabelas estão na 3ª forma normal (3FN).

---

## Como instalar e abrir no Windows (passo a passo)

### 1. Instalar o que falta (só na primeira vez)

Você já tem o **SQL Server LocalDB** e o **SSMS**. Falta instalar:

**a) Python 3.12**

1. Acesse <https://www.python.org/downloads/windows/>, procure **Python 3.12.10** e clique em
   **Windows installer (64-bit)**. As versões 3.12 mais novas que essa não têm instalador
   para Windows; se não achar o link, use a **3.12.10**.
2. Na primeira tela do instalador, **marque a caixa "Add python.exe to PATH"**
   (fica embaixo). Esse passo é muito importante.
3. Clique em **Install Now** e espere terminar.

**b) Driver ODBC 18 do SQL Server** (é por ele que o Python conversa com o banco)

1. Clique com o botão direito no menu Iniciar e abra o **Terminal** (ou **PowerShell**).
2. Cole o comando abaixo e aperte Enter. Se o Windows pedir permissão, clique em **Sim**.

   ```
   winget install -e --id Microsoft.msodbcsql.18
   ```

### 2. Criar o banco no SSMS (só na primeira vez)

1. Abra o **SSMS**.
2. Na janela **Connect to Server**:
   - **Server name:** `(localdb)\MSSQLLocalDB`
   - **Authentication:** Windows Authentication
   - Se aparecer a opção **Trust server certificate**, marque.
   - Clique em **Connect**.
3. Rode os três scripts da pasta `sql`, **nesta ordem**. Para cada um, abra o arquivo
   em **File → Open → File...** (ou `Ctrl+O`) e aperte **F5** (ou clique em **Execute**):

   | Ordem | Arquivo | O que faz | Mensagem esperada no final |
   |---|---|---|---|
   | 1º | `sql/00_schema_reconstruido.sql` | Cria o banco `CentralDeAr`, as 6 tabelas e as procedures originais | `Commands completed successfully.` |
   | 2º | `sql/01_complemento.sql` | Cria as demais procedures, a trigger de estoque e a comissão por pedido | `Complemento aplicado com sucesso.` |
   | 3º | `sql/02_seed.sql` | Cadastra dados de exemplo: 3 vendedores, 4 regiões, 10 clientes, 8 produtos e 15 pedidos | `Seed concluido: ...` |

   - O `00` deve ser rodado **uma vez só**. Se rodar de novo, aparece
     "There is already an object named...", e o banco continua inteiro.
   - O `01` pode ser rodado de novo sem problema.
   - O `02` não duplica nada: se já houver vendedores, ele avisa e não faz nada.

### 3. Conferir o nome do banco

No SSMS, no painel **Object Explorer** à esquerda, abra **Databases** (se precisar,
clique com o botão direito em *Databases* → **Refresh**). Deve aparecer **CentralDeAr**.

O aplicativo usa esse nome, configurado no arquivo **`.env`** da pasta do projeto:

```
DB_MODE=localdb
DB_NAME=CentralDeAr
```

- O `.env` é criado sozinho na primeira vez que você abre o `rodar.bat`, como cópia do `.env.example`.
- Se o banco tiver **outro nome**, abra o `.env` com o **Bloco de Notas**, troque o
  valor de `DB_NAME` pelo nome que aparece no SSMS, salve e abra o sistema de novo.
- Não mexa em `DB_PASSWORD`. Ela só é usada no modo `docker`.

### 4. Abrir o sistema

Dê **dois cliques em `rodar.bat`**.

- Na **primeira vez**, ele prepara tudo sozinho (cria a pasta `.venv` e instala as
  bibliotecas). Isso leva alguns minutos e precisa de internet.
- Depois, o navegador abre em **http://localhost:8501**. Se não abrir, digite esse endereço no navegador.
- Se o Windows perguntar sobre o **Firewall**, pode permitir em redes privadas.
- Para **fechar o sistema**, feche a janela preta do `rodar.bat`.

---

## Usando o sistema

O menu fica no topo: **Início · Pedidos · Relatórios · Cadastros** (Vendedores, Regiões,
Clientes, Produtos). Logo abaixo, uma faixa mostra o resumo: pedidos, total vendido,
vendedores e alerta de estoque baixo. A tela inteira cabe na janela; quando uma lista é
grande, ela rola **dentro** do próprio painel.

| Página | O que dá para fazer |
|---|---|
| **Início** | Indicadores (total vendido, pedidos, ticket médio, comissões...), gráfico de vendas por região e lista dos últimos pedidos |
| **Cadastros** | Tabela com busca à esquerda e formulário à direita. Sem nada selecionado, o formulário **cadastra**. **Clique numa linha** para editar ou excluir aquele registro; o botão **Novo** volta para o cadastro |
| **Pedidos** | Lista de pedidos à esquerda. **Novo pedido:** escolha o cliente e o vendedor da região aparece sozinho. A comissão começa com a padrão do vendedor e pode ser mudada. Adicione os itens na tabela; o **total** aparece em destaque no alto. **Clique num pedido** para ver os itens, adicionar, alterar ou remover itens, mudar os dados ou excluir o pedido |
| **Relatórios** | Uma aba para cada relatório, com gráfico de barras de um lado e tabela do outro, valores em R$ |

**Mensagens de erro:** quando o banco recusa alguma coisa, a mensagem aparece em vermelho
com o texto vindo do SQL Server. Exemplos: excluir um cliente que tem pedidos, vender
mais do que há em estoque, CPF/CNPJ repetido.

---

## O que foi reconstruído (para a apresentação)

O backup do laboratório (`central_ar.bak`) estava **incompleto**. Ele era a parte 2 de 2
de um backup dividido em dois arquivos, e por isso não podia ser restaurado.
Do que dava para ler nele, foram recuperados:

- as **6 tabelas** com colunas, chaves e restrições (mesmos nomes);
- o código das **5 procedures de cadastro**: `usp_CadastrarVendedor`,
  `usp_CadastrarRegiao`, `usp_CadastrarCliente`, `usp_CadastrarProduto` e `usp_CadastrarPedido`.

Das outras procedures só sobrou o nome. Estas **8 procedures foram reescritas** em
`sql/01_complemento.sql`:

| Procedure | O que mudou ou foi refeito |
|---|---|
| `usp_CadastrarPedido` | **Alterada**: recebe `@percentual_comissao` (opcional; se vazio, usa a comissão fixa do vendedor) e `@data_pedido` (opcional) |
| `usp_CadastrarItemPedido` | **Reescrita**: inclui um item; se o preço não for informado, usa o preço atual do produto |
| `usp_ConsultarVendasPorRegiao` | **Reescrita**: total vendido por região (região do cliente) |
| `usp_ConsultarVendasPorCliente` | **Reescrita**: total comprado por cliente |
| `usp_ConsultarVendasPorVendedor` | **Reescrita**: total vendido e comissão total por vendedor |
| `usp_ConsultarClientesPorRegiao` | **Reescrita**: clientes de uma região (`@id_regiao` obrigatório) |
| `usp_ConsultarVendasPorProduto` | **Reescrita**: quantidade e total vendido por produto |
| `usp_ConsultarComissaoPorVendedor` | **Reescrita**: extrato de comissão **separado por produto** (`@id_vendedor` opcional; vazio = todos) |

Também foram **adicionados**:

- coluna **`PEDIDO.percentual_comissao`** (0 a 100). Assim a comissão pode ser diferente em
  cada pedido, e mudar a comissão do vendedor não altera pedidos antigos;
- **trigger `trg_ITEM_PEDIDO_Estoque`**: ao incluir, alterar ou excluir itens de pedido, ela baixa,
  ajusta ou devolve o estoque, e dá erro claro se o estoque ficaria negativo;
- procedures de **listagem** (`usp_Listar...`) e de **alteração e exclusão**
  (`usp_Atualizar...` e `usp_Excluir...`) para todas as entidades. As exclusões são bloqueadas
  quando há registros dependentes, exceto `usp_ExcluirPedido`, que apaga os itens e o pedido
  numa transação, e a trigger devolve o estoque.

**Como os valores são calculados:** valor do item = quantidade × preço unitário × (1 − desconto/100).
A comissão de cada item usa o percentual gravado **no pedido**. Por isso o extrato por produto
mostra o "% efetivo", que pode variar quando o mesmo produto foi vendido com percentuais diferentes.

**3FN:** `PEDIDO.fk_vendedor` e `ITEM_PEDIDO.preco_unitario` não são redundâncias. Eles guardam
**quem vendeu** e **por quanto vendeu** no momento da venda, porque a região pode trocar de vendedor
e o produto pode mudar de preço depois.

---

## Estrutura do código (para a apresentação)

O código Python é dividido em **camadas**. Cada camada tem uma responsabilidade, e uma camada
só "conversa" com as de baixo. A ideia vem da *Clean Architecture*, simplificada: neste sistema
as **regras de negócio ficam no banco** (procedures e trigger), então o Python não tem uma camada
de regras própria. Ele só mostra as telas e chama as procedures.

```
   app.py ............ porta de entrada: monta o menu e abre a tela escolhida
     │
   paginas/ .......... as TELAS (Início, Pedidos, Relatórios, Cadastros)
     │      ╲
     │    componentes/ ... PEÇAS de tela reaproveitadas (painel, tabela, gráfico...)
     │
   dados/ ............ ACESSO AO BANCO: só executa stored procedures (EXEC)
     │
   SQL Server ........ tabelas + procedures + trigger (as regras de negócio)

   util/ ............. ferramentas usadas por todos (formatar R$, datas, %)
   config.py ......... lê o arquivo .env (qual banco, modo de conexão)
```

| Pasta / arquivo | O que tem | Exemplo |
|---|---|---|
| `app.py` | Configuração da página, menu do topo, faixa de status | escolhe qual tela mostrar |
| `paginas/` | Uma tela por arquivo, cada uma com a função `render()` | `paginas/cadastros/clientes.py` |
| `componentes/` | Peças de tela usadas por várias telas. **Não acessam o banco** | `painel()`, `tabela()`, `grafico_barras()` |
| `dados/` | Um arquivo por assunto, com funções de nome claro. **Único lugar que fala com o banco** | `dados/clientes.py`: `listar()`, `cadastrar()`, `atualizar()`, `excluir()` |
| `dados/conexao.py` | Conecta no SQL Server e executa as procedures | monta o `EXEC usp_...` |
| `util/` | Formatação (R$ 1.234,56, 12/11/2026, 5,00%) e o erro de banco | `brl()`, `ErroBanco` |
| `config.py` | Lê o `.env` | `DB_MODE`, `DB_NAME` |
| `ui/` | Visual: CSS do layout e logo | `estilo.css` |

**Exemplo do caminho de um clique** — cadastrar um cliente:

1. A tela `paginas/cadastros/clientes.py` mostra o formulário e, no clique, chama `dados.clientes.cadastrar(...)`.
2. `dados/clientes.py` executa `EXEC usp_CadastrarCliente ...` pela `dados/conexao.py`.
3. A **procedure** valida (nome, CPF, região) e grava. Se algo estiver errado, ela dá `THROW`.
4. O erro volta como `ErroBanco` e a tela mostra a mensagem do banco em vermelho.

**Por que separar assim?**

- A regra do professor ("só procedures") fica fácil de provar: só a pasta `dados/` tem `EXEC`,
  e nenhuma tela importa o `pyodbc`.
- Para mudar o visual, mexe-se em `paginas/`, `componentes/` ou `ui/`, sem tocar no acesso ao banco.
- Se uma procedure mudar de nome, o ajuste é num lugar só (`dados/`).

---

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| **Python nao encontrado** (na janela do `rodar.bat`) | Reinstale o Python 3.12 marcando **Add python.exe to PATH** |
| Abre a **Microsoft Store** em vez de rodar | Instale o Python pelo site (passo 1a) e rode o `rodar.bat` de novo |
| **Driver ODBC nao encontrado** | Rode o `winget install ...` do passo 1b |
| **Banco 'CentralDeAr' nao encontrado** | Rode o `00_schema_reconstruido.sql` no SSMS ou ajuste `DB_NAME` no `.env` |
| **Could not find stored procedure** | Rode o `01_complemento.sql` (e o `02_seed.sql`) no SSMS |
| **Nao foi possivel conectar ao SQL Server** | Confira se `DB_MODE=localdb` no `.env`. No SSMS, conecte em `(localdb)\MSSQLLocalDB`; isso também liga o LocalDB |
| Mudou o `.env` e nada aconteceu | Feche a janela do `rodar.bat` e abra de novo |

---

## Para quem desenvolve (Linux / WSL com Docker)

```bash
# SQL Server em container (a senha do sa vai só no seu .env, nunca no Git)
docker run -d --name central-ar-sql -e ACCEPT_EULA=Y -e 'MSSQL_SA_PASSWORD=<sua senha>' \
  -p 1433:1433 mcr.microsoft.com/mssql/server:2025-latest

# Criar o banco
for f in sql/00_schema_reconstruido.sql sql/01_complemento.sql sql/02_seed.sql; do
  /opt/mssql-tools18/bin/sqlcmd -S localhost,1433 -U sa -P '<sua senha>' -C -b -i "$f"
done

# .env para o modo docker
cp .env.example .env   # e ajuste: DB_MODE=docker, DB_PASSWORD=<sua senha>

./rodar.sh
```

### Estrutura

```
app.py                      ponto de entrada: página, CSS, menu, faixa de status
config.py                   leitura do .env
paginas/                    telas: inicio, pedidos, relatorios, cadastros/{vendedores,regioes,clientes,produtos}
componentes/                peças de tela: painel, tabela, gráfico, faixa de status, formulários de cadastro
dados/                      acesso ao banco (só EXEC): conexao + um arquivo por assunto
util/                       formatação (R$, datas, %) e o erro de banco compartilhado
requirements.txt            dependências Python (com versões fixas)
.env.example                modelo de configuração (copiado para .env)
rodar.bat / rodar.sh        abrem o sistema no Windows / Linux
.streamlit/config.toml      tema (cores, fonte) e opções do Streamlit
ui/estilo.css               layout em painéis (página sem scroll) e navbar
ui/logo.svg                 logo da navbar
sql/00_schema_reconstruido.sql   tabelas + 5 procedures originais
sql/01_complemento.sql           comissão por pedido, trigger, CRUD e relatórios
sql/02_seed.sql                  dados de exemplo
e2e/                        testes automatizados (Playwright) — só para desenvolvimento
package.json                dependências dos testes (Node) — o app não usa
```

### Testes automatizados (desenvolvimento)

> **Para usar o sistema você não precisa de nada disto** (nem Node, nem Playwright).
> É só para quem desenvolve, no Linux/WSL com o container `central-ar-sql` rodando.

Os testes abrem o app num navegador de verdade (Chromium), clicam como um usuário e
conferem no banco se os dados entraram e saíram. Eles usam um **banco só de teste**,
`CentralDeAr_E2E`, recriado do zero a cada execução a partir dos mesmos `.sql`. O banco
`CentralDeAr` e o seu `.env` não são alterados (a senha do `sa` é lida do `.env`).

```bash
npm install                      # 1ª vez: dependências dos testes
npx playwright install chromium  # 1ª vez: navegador dos testes

npm run e2e                      # suíte inteira, sem janela (rápido)
npm run e2e:ver                  # com janela, devagar (SLOW_MO=500), um teste por vez
npm run e2e:ui                   # modo UI: lista de testes, linha do tempo, rodar um a um
npm run e2e:relatorio            # relatório HTML da última execução

# assistir um spec inteiro / um teste específico (filtro pelo título)
SLOW_MO=500 npx playwright test e2e/pedidos.spec.ts --headed --workers=1
SLOW_MO=500 npx playwright test e2e/clientes.spec.ts --headed --workers=1 -g "CPF"
```

Se a janela não abrir (WSL sem interface gráfica), use o modo UI pelo navegador do Windows:
`npx playwright test --ui-host=0.0.0.0 --ui-port=9323` e abra <http://localhost:9323>.

| Arquivo | O que testa |
|---|---|
| `e2e/vendedores.spec.ts`, `regioes`, `clientes`, `produtos` | cadastrar, buscar, editar, excluir; campos obrigatórios, comissão > 100, CPF/CNPJ repetido, exclusão bloqueada por dependentes |
| `e2e/pedidos.spec.ts` | pedido com vendedor da região, comissão personalizada, itens com estoque (trigger), estoque insuficiente, excluir pedido |
| `e2e/relatorios.spec.ts` | as 6 abas; pedido novo nos totais; totais por região = vendedor = produto |
| `e2e/navegacao.spec.ts` | todas as telas sem erro e sem scroll de página em 1920×1080, 1366×768 e 1280×720 |
| `e2e/fluxo-completo.spec.ts` | **demonstração**: um único teste em 17 etapas, do cadastro à exclusão, conferindo tela e banco a cada passo |

O **fluxo completo** compara números gerais (pedidos, total vendido, comissões), então ele
pede exclusividade do banco de teste enquanto roda: os outros testes esperam ele terminar.
Para assistir: `SLOW_MO=500 npx playwright test e2e/fluxo-completo.spec.ts --headed --workers=1`
(no modo UI, cada etapa aparece com o nome em português).
