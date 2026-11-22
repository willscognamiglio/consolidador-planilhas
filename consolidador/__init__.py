"""Consolidador de planilhas: junta CSV/XLSX de vendas em um único relatório."""

from .core import (
    COLUNAS_OBRIGATORIAS,
    PlanilhaInvalidaError,
    consolidar,
    gerar_relatorio,
    ler_arquivo,
    limpar,
    normalizar_nome_coluna,
    resumo_por_mes,
    resumo_por_produto,
)

__all__ = [
    "COLUNAS_OBRIGATORIAS",
    "PlanilhaInvalidaError",
    "consolidar",
    "gerar_relatorio",
    "ler_arquivo",
    "limpar",
    "normalizar_nome_coluna",
    "resumo_por_mes",
    "resumo_por_produto",
]
