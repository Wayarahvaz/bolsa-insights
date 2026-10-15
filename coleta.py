"""
Etapa 2 - Coleta de precos de fechamento (Bolsa_Insights)

Baixa 1 ano de precos de fechamento ajustados de algumas acoes da B3
e do Ibovespa via yfinance, organiza em uma tabela (1 coluna por ativo)
e salva em precos.csv para as proximas etapas.
"""
from datetime import datetime

import pandas as pd
import yfinance as yf

# ---------------- Configuracao ----------------
TICKERS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "^BVSP"]
PERIODO = "1y"
ARQUIVO_SAIDA = "precos.csv"
HORA_FECHAMENTO_B3 = 18  # depois desse horario, o fechamento do dia e considerado final


def baixar_fechamentos(tickers, periodo):
    """Baixa os precos e devolve so a coluna Close, com nomes curtos."""
    dados = yf.download(tickers, period=periodo, auto_adjust=True, progress=False)

    if dados.empty:
        raise ValueError("Nenhum dado retornado. Verifique os tickers e a conexao.")

    fechamentos = dados["Close"].copy()

    # PETR4.SA -> PETR4 | ^BVSP -> IBOV
    fechamentos.columns = [
        "IBOV" if t == "^BVSP" else t.replace(".SA", "") for t in fechamentos.columns
    ]
    fechamentos.index.name = "Data"
    return fechamentos


def remover_pregao_em_andamento(df):
    """Remove a linha de hoje se o pregao ainda nao terminou (preco parcial)."""
    agora = datetime.now()
    ultima_data = df.index[-1].date()

    if ultima_data == agora.date() and agora.hour < HORA_FECHAMENTO_B3:
        print(f"Aviso: pregao de {ultima_data} ainda aberto - linha removida.")
        return df.iloc[:-1]
    return df


def tratar_faltantes(df):
    """Mostra quantos valores faltam por ativo e remove datas incompletas."""
    faltantes = df.isna().sum()
    if faltantes.sum() > 0:
        print("Valores faltantes por ativo (datas removidas):")
        print(faltantes[faltantes > 0].to_string())
    return df.dropna()


def main():
    print(f"Baixando {', '.join(TICKERS)} - periodo {PERIODO}...")

    precos = baixar_fechamentos(TICKERS, PERIODO)
    precos = remover_pregao_em_andamento(precos)
    precos = tratar_faltantes(precos)

    precos.to_csv(ARQUIVO_SAIDA)

    # ---------------- Conferencia ----------------
    print("\n=== Conferencia ===")
    print(f"Pregoes: {len(precos)}")
    print(f"Periodo: {precos.index.min().date()} a {precos.index.max().date()}")
    print(f"Ativos:  {list(precos.columns)}")
    print("\nUltimos 5 pregoes:")
    print(precos.tail().round(2))
    print(f"\nArquivo salvo: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()