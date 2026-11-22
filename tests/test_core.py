import pandas as pd
import pytest

from consolidador import (
    PlanilhaInvalidaError,
    consolidar,
    gerar_relatorio,
    ler_arquivo,
    limpar,
    normalizar_nome_coluna,
    resumo_por_mes,
    resumo_por_produto,
)


def escrever(caminho, texto, encoding="utf-8"):
    caminho.write_text(texto, encoding=encoding)
    return caminho


def test_normalizar_nome_coluna():
    assert normalizar_nome_coluna(" Valor Unitário ") == "valor_unitario"
    assert normalizar_nome_coluna("DATA") == "data"


def test_ler_csv_com_ponto_e_virgula(tmp_path):
    arq = escrever(
        tmp_path / "a.csv",
        "Data;Produto;Quantidade;Valor Unitário\n05/01/2026;Mouse;2;49,90\n",
    )
    df = ler_arquivo(arq)
    assert list(df.columns) == ["data", "produto", "quantidade", "valor_unitario"]
    assert len(df) == 1


def test_ler_csv_latin1(tmp_path):
    arq = escrever(
        tmp_path / "a.csv",
        "Data,Produto,Quantidade,Valor Unitário\n2026-01-05,Cafeteira,1,199.90\n",
        encoding="latin-1",
    )
    assert "valor_unitario" in ler_arquivo(arq).columns


def test_extensao_nao_suportada(tmp_path):
    arq = escrever(tmp_path / "a.txt", "x")
    with pytest.raises(PlanilhaInvalidaError):
        ler_arquivo(arq)


def test_limpar_converte_tipos_e_formato_brasileiro():
    bruto = pd.DataFrame(
        {
            "data": ["05/01/2026"],
            "produto": ["  notebook gamer "],
            "quantidade": ["2"],
            "valor_unitario": ["R$ 3.500,50"],
        }
    )
    df = limpar(bruto, "teste")
    assert df.loc[0, "produto"] == "Notebook Gamer"
    assert df.loc[0, "data"] == pd.Timestamp("2026-01-05")
    assert df.loc[0, "quantidade"] == 2
    assert df.loc[0, "valor_unitario"] == pytest.approx(3500.50)


def test_limpar_nao_inverte_dia_e_mes_de_datas_iso():
    bruto = pd.DataFrame(
        {
            "data": ["2026-01-10", "10/01/2026", "2026-03-02 00:00:00"],
            "produto": ["A", "B", "C"],
            "quantidade": ["1", "1", "1"],
            "valor_unitario": ["1", "1", "1"],
        }
    )
    df = limpar(bruto, "teste")
    assert list(df["data"]) == [
        pd.Timestamp("2026-01-10"),
        pd.Timestamp("2026-01-10"),
        pd.Timestamp("2026-03-02"),
    ]


def test_limpar_descarta_linhas_invalidas():
    bruto = pd.DataFrame(
        {
            "data": ["2026-01-05", "data ruim", "2026-01-07", "2026-01-08", "2026-01-09"],
            "produto": ["A", "B", "C", "", "E"],
            "quantidade": ["1", "1", "abc", "1", "-3"],
            "valor_unitario": ["10", "10", "10", "10", "10"],
        }
    )
    df = limpar(bruto, "teste")
    assert list(df["produto"]) == ["A"]


def test_limpar_exige_colunas():
    with pytest.raises(PlanilhaInvalidaError, match="colunas ausentes"):
        limpar(pd.DataFrame({"data": ["2026-01-01"]}), "teste")


def montar_pasta(tmp_path):
    escrever(
        tmp_path / "jan.csv",
        "Data,Produto,Quantidade,Valor Unitário\n"
        "2026-01-05,Mouse,2,50.00\n"
        "2026-01-10,Teclado,1,120.00\n",
    )
    escrever(
        tmp_path / "fev.csv",
        "Data;Produto;Quantidade;Valor Unitário\n"
        "05/01/2026;mouse;2;50,00\n"  # duplicada da de janeiro
        "03/02/2026;Mouse;3;50,00\n",
    )
    escrever(tmp_path / "quebrada.csv", "foo,bar\n1,2\n")
    return tmp_path


def test_consolidar_junta_remove_duplicadas_e_ignora_quebrados(tmp_path):
    df = consolidar(montar_pasta(tmp_path))
    assert len(df) == 3
    assert set(df["origem"]) == {"jan.csv", "fev.csv"}
    assert df["total"].sum() == pytest.approx(100 + 120 + 150)
    assert df["data"].is_monotonic_increasing


def test_consolidar_mantem_duplicadas_quando_pedido(tmp_path):
    df = consolidar(montar_pasta(tmp_path), manter_duplicados=True)
    assert len(df) == 4


def test_consolidar_pasta_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        consolidar(tmp_path / "nao_existe")


def test_consolidar_sem_planilhas_validas(tmp_path):
    escrever(tmp_path / "ruim.csv", "foo,bar\n1,2\n")
    with pytest.raises(PlanilhaInvalidaError):
        consolidar(tmp_path)


def test_resumos(tmp_path):
    df = consolidar(montar_pasta(tmp_path))
    por_produto = resumo_por_produto(df)
    assert por_produto.iloc[0]["produto"] == "Mouse"  # maior total
    assert por_produto.iloc[0]["quantidade"] == 5

    por_mes = resumo_por_mes(df)
    assert list(por_mes["mes"]) == ["2026-01", "2026-02"]
    assert list(por_mes["vendas"]) == [2, 1]


def test_gerar_relatorio_cria_tres_abas(tmp_path):
    df = consolidar(montar_pasta(tmp_path))
    saida = gerar_relatorio(df, tmp_path / "rel.xlsx")
    abas = pd.read_excel(saida, sheet_name=None)
    assert set(abas) == {"Consolidado", "Por produto", "Por mes"}
    assert len(abas["Consolidado"]) == 3


def test_relatorio_na_mesma_pasta_nao_e_lido_de_volta(tmp_path):
    pasta = montar_pasta(tmp_path)
    saida = pasta / "rel.xlsx"
    gerar_relatorio(consolidar(pasta), saida)
    df = consolidar(pasta, excluir=[saida])
    assert "rel.xlsx" not in set(df["origem"])
