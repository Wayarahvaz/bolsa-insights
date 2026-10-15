"""
Previsao D+1 do dolar (USD/BRL) por faixa de volatilidade (Bolsa_Insights)

Ideia: nao prever UM preco, e sim uma FAIXA provavel para o proximo dia,
a partir da oscilacao recente do cambio.

Formulas:
- Retorno log diario   = ln(preco_hoje / preco_ontem)
- Volatilidade diaria  = desvio padrao dos ultimos 21 retornos log
- Faixa D+1            = preco_atual * exp(+/- z * volatilidade_diaria)
    z = 1,00 -> ~68% de confianca | z = 1,96 -> ~95% de confianca

Backtest: refaz a previsao para cada dia do ultimo ano e mede quantas vezes
o dolar do dia seguinte ficou dentro da faixa (esperado: ~68% e ~95%).

Estatistica descritiva sobre o passado; nao e recomendacao de investimento.
"""
import numpy as np
import pandas as pd
import yfinance as yf

# ---------------- Configuracao ----------------
TICKER = "BRL=X"   # USD/BRL no Yahoo Finance
PERIODO = "1y"
JANELA_VOL = 21    # ~1 mes de pregoes
NIVEIS = {"~68%": 1.00, "~95%": 1.96}


def brl(x, casas=4):
    return f"R$ {x:.{casas}f}".replace(".", ",")


def pct(x, sinal=False):
    fmt = "{:+.2f}%" if sinal else "{:.2f}%"
    return fmt.format(x * 100).replace(".", ",")


def baixar_dolar():
    dados = yf.download(TICKER, period=PERIODO, auto_adjust=True, progress=False)
    if dados.empty:
        raise SystemExit("ERRO: nenhum dado retornado. Verifique o ticker e a conexao.")
    serie = dados["Close"].squeeze().dropna()  # Close vem como tabela de 1 coluna
    serie.name = "USDBRL"
    return serie


def faixa(preco, vol, z):
    return preco * np.exp(-z * vol), preco * np.exp(z * vol)


def backtest(retornos_log):
    """% de dias em que o retorno do dia seguinte ficou dentro de +/- z * vol."""
    vol_movel = retornos_log.rolling(JANELA_VOL).std()
    retorno_seguinte = retornos_log.shift(-1)
    base = pd.DataFrame({"vol": vol_movel, "seguinte": retorno_seguinte}).dropna()

    acertos = {
        nome: (base["seguinte"].abs() <= z * base["vol"]).mean()
        for nome, z in NIVEIS.items()
    }
    return acertos, len(base)


def main():
    serie = baixar_dolar()
    retornos_log = np.log(serie / serie.shift(1)).dropna()

    preco_atual = serie.iloc[-1]
    data_ref = serie.index[-1].strftime("%d/%m/%Y")
    vol_21d = retornos_log.tail(JANELA_VOL).std()
    vol_1a = retornos_log.std()

    print(f"=== Previsao D+1 do dolar (USD/BRL) ===")
    print(f"Cotacao de referencia: {brl(preco_atual)} em {data_ref}")
    print("  (se a data for hoje, e a cotacao do momento da coleta)\n")

    print("Oscilacao diaria tipica:")
    print(f"  - ultimos 21 dias: {pct(vol_21d)} por dia")
    print(f"  - ultimo ano:      {pct(vol_1a)} por dia")
    clima = "MAIS agitado" if vol_21d > vol_1a else "MAIS calmo"
    print(f"  -> o cambio esta {clima} que a media do ano.\n")

    print("Faixa provavel para o proximo dia util:")
    for nome, z in NIVEIS.items():
        minimo, maximo = faixa(preco_atual, vol_21d, z)
        print(f"  - {nome} de confianca: {brl(minimo)} a {brl(maximo)}")

    print(f"\nContexto do ano: maior alta diaria {pct(retornos_log.max(), True)}, "
          f"maior queda diaria {pct(retornos_log.min(), True)}")

    acertos, n_dias = backtest(retornos_log)
    print(f"\nBacktest ({n_dias} dias testados) - o metodo acerta o que promete?")
    for nome, taxa in acertos.items():
        print(f"  - faixa {nome}: dolar ficou dentro em {pct(taxa)} dos dias")

    print("\nEstatistica descritiva sobre o passado; nao e recomendacao de investimento.")


if __name__ == "__main__":
    main()