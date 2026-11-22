"""Lógica principal: leitura, limpeza, consolidação e geração do relatório."""

from __future__ import annotations

import csv
import logging
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

log = logging.getLogger(__name__)

EXTENSOES_SUPORTADAS = {".csv", ".xlsx", ".xls"}
COLUNAS_OBRIGATORIAS = ["data", "produto", "quantidade", "valor_unitario"]
COLUNAS_MONETARIAS = {"valor_unitario", "total"}


class PlanilhaInvalidaError(ValueError):
    """Arquivo ilegível ou sem as colunas obrigatórias."""


def normalizar_nome_coluna(nome) -> str:
    """'Valor Unitário ' -> 'valor_unitario' (sem acentos, minúsculo, com _)."""
    sem_acento = (
        unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    )
    return "_".join(sem_acento.strip().lower().split())


def _para_numero(serie: pd.Series) -> pd.Series:
    """Converte texto em número, aceitando o formato brasileiro (1.234,56)."""
    texto = serie.astype("string").str.replace("R$", "", regex=False).str.strip()
    tem_virgula = texto.str.contains(",", na=False)
    brasileiro = texto.str.replace(".", "", regex=False).str.replace(
        ",", ".", regex=False
    )
    texto = texto.where(~tem_virgula, brasileiro)
    return pd.to_numeric(texto, errors="coerce")


def _para_data(serie: pd.Series) -> pd.Series:
    """Converte texto em data: ISO (2026-01-10) primeiro, depois dd/mm/aaaa.

    Usar dayfirst direto em tudo inverteria dia e mês de datas ISO.
    """
    texto = serie.astype("string").str.strip()
    iso = pd.to_datetime(texto, format="ISO8601", errors="coerce")
    brasileira = pd.to_datetime(texto, dayfirst=True, format="mixed", errors="coerce")
    return iso.fillna(brasileira)


def ler_arquivo(caminho: str | Path) -> pd.DataFrame:
    """Lê um CSV ou Excel como texto e padroniza os nomes das colunas."""
    caminho = Path(caminho)
    sufixo = caminho.suffix.lower()
    if sufixo not in EXTENSOES_SUPORTADAS:
        raise PlanilhaInvalidaError(f"{caminho.name}: extensão não suportada")

    try:
        if sufixo == ".csv":
            try:
                # sep=None detecta automaticamente ',' ou ';'
                df = pd.read_csv(
                    caminho, sep=None, engine="python", dtype=str, encoding="utf-8-sig"
                )
            except UnicodeDecodeError:
                df = pd.read_csv(
                    caminho, sep=None, engine="python", dtype=str, encoding="latin-1"
                )
        else:
            df = pd.read_excel(caminho, dtype=str)
    except (
        csv.Error,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        ValueError,
    ) as erro:
        raise PlanilhaInvalidaError(f"{caminho.name}: não foi possível ler ({erro})")

    df.columns = [normalizar_nome_coluna(c) for c in df.columns]
    return df


def limpar(df: pd.DataFrame, origem: str) -> pd.DataFrame:
    """Valida colunas, converte tipos e descarta linhas inválidas."""
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise PlanilhaInvalidaError(f"{origem}: colunas ausentes: {', '.join(faltando)}")

    df = df[COLUNAS_OBRIGATORIAS].copy()
    df["produto"] = df["produto"].astype("string").str.strip().str.title()
    df["data"] = _para_data(df["data"])
    df["quantidade"] = _para_numero(df["quantidade"])
    df["valor_unitario"] = _para_numero(df["valor_unitario"])

    def mascara(condicao: pd.Series) -> np.ndarray:
        return condicao.fillna(False).to_numpy(dtype=bool)

    validas = (
        mascara(df["data"].notna())
        & mascara(df["produto"].fillna("").str.len().gt(0))
        & mascara(df["quantidade"] > 0)
        & mascara(df["quantidade"] % 1 == 0)
        & mascara(df["valor_unitario"] >= 0)
    )
    descartadas = int(np.count_nonzero(~validas))
    if descartadas:
        log.warning("%s: %d linha(s) inválida(s) descartada(s)", origem, descartadas)

    df = df[validas].copy()
    df["quantidade"] = df["quantidade"].astype("int64")
    df["produto"] = df["produto"].astype(str)
    return df


def consolidar(
    pasta: str | Path,
    manter_duplicados: bool = False,
    excluir: Iterable[str | Path] = (),
) -> pd.DataFrame:
    """Lê todas as planilhas da pasta e devolve um único DataFrame limpo."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")

    ignorados = {Path(p).resolve() for p in excluir}
    arquivos = sorted(
        p
        for p in pasta.iterdir()
        if p.suffix.lower() in EXTENSOES_SUPORTADAS
        and not p.name.startswith(("~$", "."))
        and p.resolve() not in ignorados
    )

    partes = []
    for arquivo in arquivos:
        try:
            parte = limpar(ler_arquivo(arquivo), arquivo.name)
        except PlanilhaInvalidaError as erro:
            log.warning("Arquivo ignorado -> %s", erro)
            continue
        parte["origem"] = arquivo.name
        partes.append(parte)
        log.info("%s: %d linha(s) lida(s)", arquivo.name, len(parte))

    if not partes:
        raise PlanilhaInvalidaError(f"Nenhuma planilha válida encontrada em {pasta}")

    df = pd.concat(partes, ignore_index=True)

    if not manter_duplicados:
        antes = len(df)
        df = df.drop_duplicates(subset=COLUNAS_OBRIGATORIAS, keep="first")
        if antes - len(df):
            log.info("%d linha(s) duplicada(s) removida(s)", antes - len(df))

    df["total"] = (df["quantidade"] * df["valor_unitario"]).round(2)
    return df.sort_values(["data", "produto"]).reset_index(drop=True)


def resumo_por_produto(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("produto", as_index=False)
        .agg(quantidade=("quantidade", "sum"), total=("total", "sum"))
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )


def resumo_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    mes = df["data"].dt.strftime("%Y-%m").rename("mes")
    return (
        df.groupby(mes, as_index=False)
        .agg(
            vendas=("produto", "count"),
            quantidade=("quantidade", "sum"),
            total=("total", "sum"),
        )
        .sort_values("mes")
        .reset_index(drop=True)
    )


def _formatar_aba(ws) -> None:
    cabecalho = [c.value for c in ws[1]]
    for indice, nome in enumerate(cabecalho, start=1):
        letra = get_column_letter(indice)
        valores = [str(c.value) for c in ws[letra] if c.value is not None]
        ws.column_dimensions[letra].width = min(max(map(len, valores)) + 2, 40)
        if nome in COLUNAS_MONETARIAS:
            for celula in ws[letra][1:]:
                celula.number_format = "#,##0.00"
    ws.freeze_panes = "A2"


def gerar_relatorio(df: pd.DataFrame, saida: str | Path) -> Path:
    """Grava o Excel com as abas Consolidado, Por produto e Por mês."""
    saida = Path(saida)
    with pd.ExcelWriter(
        saida, engine="openpyxl", datetime_format="DD/MM/YYYY"
    ) as escritor:
        df.to_excel(escritor, sheet_name="Consolidado", index=False)
        resumo_por_produto(df).to_excel(escritor, sheet_name="Por produto", index=False)
        resumo_por_mes(df).to_excel(escritor, sheet_name="Por mes", index=False)
        for aba in escritor.book.worksheets:
            _formatar_aba(aba)
    return saida
