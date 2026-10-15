"""
Etapa 4 - Insights em texto (Bolsa_Insights)

Le metricas.csv (gerado por calculos.py) e transforma os numeros em frases,
usando regras simples (se/entao). Imprime no terminal e salva em insights.txt.

Os limites das regras ficam na secao de configuracao para facilitar ajustes.
Estatistica descritiva sobre o passado - nao e recomendacao de investimento.
"""
import pandas as pd

# ---------------- Configuracao ----------------
ARQUIVO_METRICAS = "metricas.csv"
ARQUIVO_PRECOS = "precos.csv"
ARQUIVO_SAIDA = "insights.txt"
REFERENCIA = "IBOV"

# Hipotese de fator externo, usada quando a correlacao com o IBOV e baixa
CONTEXTO = {
    "PETR4": "preco do petroleo",
    "VALE3": "preco do minerio de ferro",
    "ITUB4": "juros e credito",
}

LIMITE_ESTICADO = 0.15        # preco > 15% acima da MM50
LIMITE_PERTO_MAXIMA = -0.03   # ate 3% abaixo da maxima de 12m
LIMITE_BETA_ALTO = 1.1
LIMITE_BETA_BAIXO = 0.8
LIMITE_CORR_BAIXA = 0.5


# ---------------- Formatacao ----------------
def pct(x, sinal=True):
    """0.123 -> '+12,3%' (padrao brasileiro)."""
    fmt = "{:+.1f}%" if sinal else "{:.1f}%"
    return fmt.format(x * 100).replace(".", ",")


def pp(x):
    """Diferenca entre duas taxas, em pontos percentuais."""
    return "{:+.1f}".format(x * 100).replace(".", ",") + " p.p."


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


# ---------------- Regras de insight ----------------
def insight_tendencia(m):
    preco, mm20, mm50 = m["Preco_Atual"], m["MM20"], m["MM50"]

    if preco > mm20 > mm50:
        frase = f"Tendencia de alta: preco acima das medias de 20 e 50 dias ({pct(m['Dist_MM50'])} da MM50)."
    elif preco < mm20 < mm50:
        frase = f"Tendencia de baixa: preco abaixo das medias de 20 e 50 dias ({pct(m['Dist_MM50'])} da MM50)."
    else:
        frase = "Tendencia indefinida: preco e medias moveis sem alinhamento claro."

    if m["Dist_MM50"] > LIMITE_ESTICADO:
        frase += " Subida rapida no curto prazo (preco bem acima da MM50); vale acompanhar se se sustenta."
    return frase


def insight_posicao(m):
    dist, dd = m["Dist_Maxima"], m["Drawdown_Max"]
    abaixo = pct(abs(dist), sinal=False)  # "23,9%" em vez de "-23,9%" (o "abaixo" ja da o sinal)

    if dist > -0.001:
        return "Esta na maxima de 12 meses."
    if dist >= LIMITE_PERTO_MAXIMA:
        return f"Esta perto da maxima de 12 meses ({abaixo} abaixo)."
    if abs(dist - dd) < 0.005:
        return f"Esta na maior queda do periodo: {abaixo} abaixo da maxima de 12 meses."
    return f"Esta {abaixo} abaixo da maxima de 12 meses (pior queda do periodo: {pct(dd)})."


def insight_momento(m):
    r1, r3 = m["Retorno_1m"], m["Retorno_3m"]

    if r1 > 0 and r3 > 0:
        return f"Momento positivo: alta em 1 mes ({pct(r1)}) e em 3 meses ({pct(r3)})."
    if r1 < 0 and r3 < 0:
        return f"Momento negativo: queda em 1 mes ({pct(r1)}) e em 3 meses ({pct(r3)})."
    if r1 > 0:
        return f"Recuperacao recente: {pct(r1)} no ultimo mes, apos {pct(r3)} em 3 meses."
    return f"Perda de folego: {pct(r1)} no ultimo mes, apesar de {pct(r3)} em 3 meses."


def insight_vs_mercado(m, ref):
    dif = m["Retorno_12m"] - ref["Retorno_12m"]
    resultado = "acima" if dif > 0 else "abaixo"
    return (f"Em 12 meses: {pct(m['Retorno_12m'])}, contra {pct(ref['Retorno_12m'])} do Ibovespa "
            f"({pp(dif)}, {resultado} do indice).")


def insight_risco(ativo, m, ref):
    vol_rel = m["Volatilidade_Anual"] / ref["Volatilidade_Anual"]
    frases = [f"Volatilidade de {pct(m['Volatilidade_Anual'], sinal=False)} ao ano, "
              f"{num(vol_rel, 1)}x a do Ibovespa."]

    beta = m["Beta_IBOV"]
    if beta > LIMITE_BETA_ALTO:
        frases.append(f"Beta {num(beta)}: tende a amplificar os movimentos do mercado.")
    elif beta < LIMITE_BETA_BAIXO:
        frases.append(f"Beta {num(beta)}: menos sensivel as oscilacoes do indice.")

    corr = m["Correlacao_IBOV"]
    if corr < LIMITE_CORR_BAIXA:
        frase = f"Correlacao baixa com o Ibovespa ({num(corr)}): o ativo se move por fatores proprios"
        if ativo in CONTEXTO:
            frase += f" (hipotese: {CONTEXTO[ativo]})"
        frases.append(frase + ".")

    return " ".join(frases)


# ---------------- Relatorio ----------------
def bloco_por_ativo(metricas):
    ref = metricas.loc[REFERENCIA]
    linhas = []
    for ativo, m in metricas.drop(REFERENCIA).iterrows():
        linhas.append(f"\n[{ativo}]  preco atual: R$ {num(m['Preco_Atual'])}")
        for frase in (
            insight_tendencia(m),
            insight_posicao(m),
            insight_momento(m),
            insight_vs_mercado(m, ref),
            insight_risco(ativo, m, ref),
        ):
            linhas.append(f"  - {frase}")
    return linhas


def bloco_ranking(metricas):
    acoes = metricas.drop(REFERENCIA)
    ret_por_risco = acoes["Retorno_12m"] / acoes["Volatilidade_Anual"]

    maior_ret = acoes["Retorno_12m"].idxmax()
    maior_vol = acoes["Volatilidade_Anual"].idxmax()
    melhor_rr = ret_por_risco.idxmax()
    mais_descolada = acoes["Correlacao_IBOV"].idxmin()

    return [
        "\n=== Ranking ===",
        f"  - Maior retorno em 12 meses: {maior_ret} ({pct(acoes.loc[maior_ret, 'Retorno_12m'])})",
        f"  - Maior volatilidade: {maior_vol} ({pct(acoes.loc[maior_vol, 'Volatilidade_Anual'], sinal=False)} ao ano)",
        f"  - Melhor retorno por unidade de risco: {melhor_rr} ({num(ret_por_risco[melhor_rr])} = retorno 12m / volatilidade)",
        f"  - Mais descolada do Ibovespa: {mais_descolada} (correlacao {num(acoes.loc[mais_descolada, 'Correlacao_IBOV'])})",
    ]


def main():
    metricas = pd.read_csv(ARQUIVO_METRICAS, index_col="Ativo")
    precos = pd.read_csv(ARQUIVO_PRECOS, index_col="Data", parse_dates=True)
    data_ref = precos.index.max().strftime("%d/%m/%Y")

    linhas = [f"=== Insights da bolsa - dados ate {data_ref} ==="]
    linhas += bloco_por_ativo(metricas)
    linhas += bloco_ranking(metricas)
    linhas.append("\nEstatistica descritiva sobre o passado; nao e recomendacao de investimento.")

    texto = "\n".join(linhas)
    print(texto)

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"\nArquivo salvo: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()