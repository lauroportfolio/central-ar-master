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
> `EXEC usp_...` (veja `db.py`). Todas as tabelas estão na 3ª forma normal (3FN).

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

| Página | O que dá para fazer |
|---|---|
| **Início** | Resumo: total vendido, pedidos, ticket médio, comissões, vendas por região, últimos pedidos e aviso de estoque baixo |
| **Vendedores, Regiões, Clientes, Produtos** | Tabela com tudo, aba **Incluir** e aba **Editar / excluir**: escolha o registro na lista, altere e salve, ou marque a confirmação e exclua |
| **Pedidos** | **Novo pedido:** escolha o cliente e o vendedor da região aparece sozinho. A comissão começa com a padrão do vendedor e pode ser mudada. Adicione os itens na tabela; o total é calculado na hora. **Detalhes / editar:** mude dados do pedido, adicione, altere ou remova itens, exclua o pedido |
| **Relatórios** | Uma aba para cada relatório, com valores em R$ e gráfico de barras |

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
app.py                      telas (Streamlit)
db.py                       acesso ao banco — só EXEC de stored procedures
requirements.txt            dependências Python (com versões fixas)
.env.example                modelo de configuração (copiado para .env)
rodar.bat / rodar.sh        abrem o sistema no Windows / Linux
.streamlit/config.toml      configuração visual do Streamlit
sql/00_schema_reconstruido.sql   tabelas + 5 procedures originais
sql/01_complemento.sql           comissão por pedido, trigger, CRUD e relatórios
sql/02_seed.sql                  dados de exemplo
```
