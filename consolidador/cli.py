"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .core import PlanilhaInvalidaError, consolidar, gerar_relatorio


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="consolidador",
        description="Consolida planilhas CSV/XLSX de vendas em um relatório Excel.",
    )
    parser.add_argument("pasta", help="pasta com as planilhas de origem")
    parser.add_argument(
        "-o",
        "--saida",
        default="relatorio_consolidado.xlsx",
        help="arquivo Excel de saída (padrão: %(default)s)",
    )
    parser.add_argument(
        "--manter-duplicados",
        action="store_true",
        help="não remove linhas idênticas encontradas em mais de um arquivo",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="mostra mais detalhes"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    saida = Path(args.saida)
    try:
        df = consolidar(
            args.pasta, manter_duplicados=args.manter_duplicados, excluir=[saida]
        )
    except (FileNotFoundError, PlanilhaInvalidaError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    gerar_relatorio(df, saida)
    total = f"{df['total'].sum():,.2f}".replace(",", "X").replace(".", ",")
    total = total.replace("X", ".")
    print(f"Relatório gerado em {saida} ({len(df)} vendas, total R$ {total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
