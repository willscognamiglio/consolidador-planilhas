# Consolidador de Planilhas

Ferramenta de linha de comando em Python que junta várias planilhas de vendas (CSV e Excel) em um único relatório `.xlsx`, já limpo, sem duplicidades e com resumos por produto e por mês.

Nasceu de uma tarefa comum no dia a dia: receber planilhas de origens diferentes, cada uma com seu formato, e ter que juntar tudo à mão.

## O que ele faz

- Lê todos os `.csv`, `.xlsx` e `.xls` de uma pasta
- Detecta sozinho o separador do CSV (`,` ou `;`) e a codificação (UTF-8 ou Latin-1)
- Padroniza os nomes das colunas (`Valor Unitário` → `valor_unitario`)
- Entende números no formato brasileiro (`R$ 3.650,00`) e datas em `2026-01-10` ou `10/01/2026`
- Descarta linhas inválidas (data, quantidade ou valor impossíveis de ler) e avisa quantas foram
- Remove linhas idênticas que apareçam em mais de um arquivo
- Ignora arquivos que não tenham as colunas esperadas, sem interromper o processo
- Gera o Excel com três abas: **Consolidado**, **Por produto** e **Por mes**

## Instalação

Requer Python 3.10 ou superior.

```bash
git clone https://github.com/SEU_USUARIO/consolidador-planilhas.git
cd consolidador-planilhas
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python -m consolidador dados_exemplo -o relatorio.xlsx
```

Opções:

| Opção | Descrição |
|---|---|
| `pasta` | Pasta com as planilhas de origem (obrigatório) |
| `-o`, `--saida` | Arquivo Excel de saída (padrão: `relatorio_consolidado.xlsx`) |
| `--manter-duplicados` | Não remove linhas idênticas entre arquivos |
| `-v`, `--verbose` | Mostra mais detalhes |

### Formato esperado das planilhas

Cada arquivo precisa ter estas colunas (a ordem e a caixa não importam):

| Data | Produto | Quantidade | Valor Unitário |
|---|---|---|---|
| 2026-01-05 | Notebook | 2 | 3500.00 |

## Exemplo de execução

Com os arquivos da pasta `dados_exemplo/` (um CSV com vírgula, um CSV com ponto e vírgula e um Excel):

```
INFO: vendas_fev.csv: 5 linha(s) lida(s)
WARNING: vendas_jan.csv: 1 linha(s) inválida(s) descartada(s)
INFO: vendas_jan.csv: 5 linha(s) lida(s)
INFO: vendas_mar.xlsx: 4 linha(s) lida(s)
INFO: 2 linha(s) duplicada(s) removida(s)
Relatório gerado em relatorio.xlsx (12 vendas, total R$ 36.625,50)
```

Aba **Por produto**:

| produto | quantidade | total |
|---|---|---|
| Notebook | 6 | 21150.0 |
| Monitor 24 | 10 | 8990.0 |
| Teclado Mecânico | 10 | 2890.0 |
| Mouse Sem Fio | 45 | 2695.5 |
| Webcam | 6 | 900.0 |

## Testes

```bash
python -m pytest
```

Os testes cobrem leitura de CSV com diferentes separadores e codificações, conversão de números e datas, descarte de linhas inválidas, remoção de duplicadas, geração do Excel e a interface de linha de comando.

## Estrutura

```
consolidador-planilhas/
├── consolidador/
│   ├── core.py        # leitura, limpeza, consolidação e relatório
│   ├── cli.py         # interface de linha de comando
│   └── __main__.py    # permite rodar com python -m consolidador
├── dados_exemplo/     # planilhas fictícias para testar
├── tests/
└── requirements.txt
```

## Decisões de projeto

- **Datas ISO primeiro:** o formato `2026-01-10` é lido antes do `dd/mm/aaaa`. Aplicar "dia primeiro" em tudo inverteria dia e mês das datas ISO (esse bug foi encontrado pelos testes e ficou coberto por um teste de regressão).
- **Duplicadas:** consideradas as linhas com a mesma data, produto, quantidade e valor. Se vendas idênticas legítimas forem comuns nos seus dados, use `--manter-duplicados`.
- **Quando há duplicata entre arquivos**, vale a linha do primeiro arquivo em ordem alfabética.

## Ideias para evoluir

- Gráfico de vendas por mês dentro do Excel
- Filtro por período (`--de` e `--ate`)
- Suporte a mais colunas (cliente, região, vendedor)

## Licença

MIT
