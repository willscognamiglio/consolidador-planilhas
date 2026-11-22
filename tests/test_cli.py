import pandas as pd

from consolidador.cli import main


def test_cli_gera_relatorio(tmp_path, capsys):
    (tmp_path / "vendas.csv").write_text(
        "Data,Produto,Quantidade,Valor Unitário\n2026-01-05,Mouse,2,50.00\n",
        encoding="utf-8",
    )
    saida = tmp_path / "rel.xlsx"
    codigo = main([str(tmp_path), "-o", str(saida)])

    assert codigo == 0
    assert saida.exists()
    assert "1 vendas" in capsys.readouterr().out
    assert len(pd.read_excel(saida, sheet_name="Consolidado")) == 1


def test_cli_pasta_inexistente(tmp_path, capsys):
    codigo = main([str(tmp_path / "nada")])
    assert codigo == 1
    assert "Erro" in capsys.readouterr().err
