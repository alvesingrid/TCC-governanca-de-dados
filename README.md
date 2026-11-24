# Governança de dados na prática: diagnóstico do banco do Ministério das Cidades no Gov Hub

Código e resultados do Trabalho de Conclusão de Curso de **Ingrid Alves Rocha** (Engenharia de Software, UnB), orientado por Isaque Alves.

O trabalho diagnostica a qualidade dos dados e da documentação do banco de dados que o projeto [Gov Hub](https://github.com/GovHub-br) mantém para o Ministério das Cidades. São oito bases: a Conjuntura Habitacional, que é pública, e sete bases internas do programa Minha Casa Minha Vida. Este repositório traz os scripts e os resultados do **piloto** feito no TCC 1.

## Resultados do piloto

| Medida | Resultado | Data |
|---|---|---|
| Tamanho do banco | 592 tabelas, 13.688 colunas e 161.083.898 linhas | 20/11 e 23/11/2026 |
| Colunas com descrição na documentação oficial | 1.519 de 13.688 (11,1%) | 20/11/2026 |
| Tabelas sem nenhuma entrada na documentação | 303 de 592 | 20/11/2026 |
| Testes de qualidade na Conjuntura Habitacional | 4 de 4 aprovados | 20/11/2026 |

A "documentação oficial" são os arquivos `.yml` do dbt no repositório [data-application-cidades](https://github.com/GovHub-br/data-application-cidades).

## Organização

```
.
├── scripts/                 código do piloto
│   ├── conexao.py           conexão somente leitura com o banco e caminhos comuns
│   ├── dbt_docs.py          lê as descrições dos arquivos .yml do dbt
│   ├── testar_conexao.py    confere se o acesso ao banco funciona
│   ├── conferir_env.py      confere o .env sem mostrar a senha
│   ├── piloto_inventario.py etapas 1 e 3: inventário e cobertura da documentação
│   ├── piloto_linhas.py     conta as linhas de todas as tabelas, por camada
│   ├── piloto_recorte.py    tamanho e colunas das tabelas públicas da Conjuntura
│   ├── piloto_testes.py     um teste de qualidade por dimensão (Great Expectations)
│   └── piloto_copia.py      cópia datada das tabelas públicas da Conjuntura
├── resultados/              resultados de cada execução, numa pasta por data
│   ├── 2026-11-20/
│   └── 2026-11-23/
├── requirements.txt
└── README.md
```

| Arquivo em `resultados/` | O que tem |
|---|---|
| `inventario_tabelas_*.csv` | uma linha por tabela do banco: base, camada, colunas e colunas descritas |
| `inventario_colunas_*.csv` | uma linha por coluna, dizendo se ela tem descrição |
| `resumo_*.txt` | a cobertura da documentação por camada e por base |
| `linhas_*.csv` | o número de linhas de cada tabela |
| `recorte_*.csv` | tabelas e colunas públicas da Conjuntura usadas nos testes |
| `testes_*.csv` e `.json` | o resultado dos quatro testes de qualidade |

## Como reproduzir

### 1. Pré-requisitos

- Python 3.11 ou superior.
- Um clone do [data-application-cidades](https://github.com/GovHub-br/data-application-cidades) em `~/TCC/data-application-cidades`. Se ele estiver em outro lugar, informe o caminho na variável `CIDADES_REPO`.
- Acesso ao banco do Gov Hub: as credenciais `DB_DW_*_MCID` no `.env` desse clone e a VPN do laboratório ligada. O acesso é concedido pela equipe do Gov Hub.

### 2. Instalar as dependências

Com o ambiente do próprio data-application-cidades, que já tem tudo instalado:

```bash
uv run --project ~/TCC/data-application-cidades python scripts/testar_conexao.py
```

Ou num ambiente separado:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Rodar o piloto

Execute a partir da pasta deste repositório. Cada script pede a senha do banco e grava em `resultados/<data de hoje>/`.

Se estiver usando o ambiente do data-application-cidades, troque `python` por `uv run --project ~/TCC/data-application-cidades python`.

```bash
python scripts/testar_conexao.py      # confere o acesso
python scripts/piloto_inventario.py   # inventário e cobertura da documentação
python scripts/piloto_linhas.py       # contagem de linhas (pode levar minutos)
python scripts/piloto_recorte.py      # recorte público da Conjuntura
python scripts/piloto_testes.py       # testes de qualidade
python scripts/piloto_copia.py        # cópia datada da Conjuntura (opcional)
```

O banco muda com o tempo: entre 20 e 23 de novembro de 2026 surgiram 74 tabelas novas. Por isso cada resultado fica na pasta da data em que foi medido.

## Cuidados com os dados

- Todos os scripts abrem a conexão em **modo somente leitura** e não alteram o banco.
- Das bases internas, este repositório guarda só **metadados e números agregados**: nomes de tabelas e colunas, contagens e percentuais. Nenhum valor dessas bases sai do servidor do Gov Hub.
- Só os dados da Conjuntura Habitacional, que vêm de fontes públicas, podem ser copiados para cá, com o `piloto_copia.py`.
- Credenciais (`.env`) e arquivos da VPN nunca vão para o repositório. O `.gitignore` já bloqueia esses arquivos.
