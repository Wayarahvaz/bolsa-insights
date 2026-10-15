"""
Etapa 3 - Calculo das metricas (Bolsa_Insights)

Le precos.csv (gerado por coleta.py) e calcula, para cada ativo,
metricas de retorno, tendencia, risco e relacao com o Ibovespa.
Salva o resultado em metricas.csv (1 linha por ativo).

Formulas:
- Retorno de n pregoes  = preco_hoje / preco_n_pregoes_atras - 1
- Media movel (MM)      = media dos ultimos n fechamentos
- Volatilidade anual    = desvio padrao dos retornos diarios * raiz(252)
- Drawdown maximo       = menor valor de (preco / maior_preco_ate_entao - 1)
- Correlacao            = correlacao de Pearson dos retornos diarios com o IBOV
- Beta                  = cov(retorno_ativo, retorno_ibov) / var(retorno_ibov)
"""
import numpy as np
import pandas as pd

# ---------------- Configuracao ----------------
ARQUIVO_ENTRADA = "precos.csv"
ARQUIVO_SAIDA = "metricas.csv"
REFERENCIA = "IBOV"
PREGOES_ANO = 252
PREGOES_1M = 21
PREGOES_3M = 63


def carregar_precos(caminho):
    """Le o CSV de precos com a coluna Data como indice de datas."""
    return pd.read_csv(caminho, index_col="Data", parse_dates=True)


def retorno_periodo(serie, n_pregoes):
    """Retorno entre o ultimo preco e o preco de n pregoes atras."""
    if len(serie) <= n_pregoes:
        return np.nan
    return serie.iloc[-1] / serie.iloc[-1 - n_pregoes] - 1


def drawdown_maximo(serie):
    """Maior queda percentual de um pico ate o vale seguinte."""
    pico_acumulado = serie.cummax()
    return (serie / pico_acumulado - 1).min()


def calcular_metricas(precos):
    """Devolve um DataFrame com 1 linha por ativo e as metricas nas colunas."""
    retornos = precos.pct_change().dropna()
    ret_ref = retornos[REFERENCIA]

    linhas = []
    for ativo in precos.columns:
        p = precos[ativo]
        r = retornos[ativo]

        preco_atual = p.iloc[-1]
        mm20 = p.rolling(20).mean().iloc[-1]
        mm50 = p.rolling(50).mean().iloc[-1]
        maxima = p.max()
        minima = p.min()

        linhas.append({
            "Ativo": ativo,
            "Preco_Atual": preco_atual,
            "Retorno_1m": retorno_periodo(p, PREGOES_1M),
            "Retorno_3m": retorno_periodo(p, PREGOES_3M),
            "Retorno_12m": p.iloc[-1] / p.iloc[0] - 1,
            "MM20": mm20,
            "MM50": mm50,
            "Dist_MM50": preco_atual / mm50 - 1,
            "Volatilidade_Anual": r.std() * np.sqrt(PREGOES_ANO),
            "Maxima_12m": maxima,
            "Minima_12m": minima,
            "Dist_Maxima": preco_atual / maxima - 1,
            "Drawdown_Max": drawdown_maximo(p),
            "Pct_Dias_Alta": (r > 0).mean(),
            "Correlacao_IBOV": r.corr(ret_ref),
            "Beta_IBOV": r.cov(ret_ref) / ret_ref.var(),
        })

    return pd.DataFrame(linhas).set_index("Ativo")


def exibir(metricas):
    """Imprime a tabela formatada (% e casas decimais) para conferencia."""
    colunas_pct = [
        "Retorno_1m", "Retorno_3m", "Retorno_12m", "Dist_MM50",
        "Volatilidade_Anual", "Dist_Maxima", "Drawdown_Max", "Pct_Dias_Alta",
    ]
    tabela = metricas.copy()
    for col in colunas_pct:
        tabela[col] = (tabela[col] * 100).map("{:.1f}%".format)
    for col in ["Preco_Atual", "MM20", "MM50", "Maxima_12m", "Minima_12m",
                "Correlacao_IBOV", "Beta_IBOV"]:
        tabela[col] = tabela[col].map("{:,.2f}".format)

    # Transposta: metricas nas linhas, ativos nas colunas (cabe melhor no terminal)
    print(tabela.T.to_string())


def main():
    precos = carregar_precos(ARQUIVO_ENTRADA)
    print(f"Precos carregados: {len(precos)} pregoes, ativos {list(precos.columns)}\n")

    metricas = calcular_metricas(precos)
    metricas.to_csv(ARQUIVO_SAIDA)

    exibir(metricas)
    print(f"\nArquivo salvo: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()