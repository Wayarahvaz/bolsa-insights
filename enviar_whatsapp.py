"""
Etapa 6 - Envio do resumo por WhatsApp (Bolsa_Insights)

Mensagem simples, sem emojis:
- cotacao do dolar e do euro (com variacao do dia)
- acoes agrupadas pelo retorno de 12 meses: em alta / inalteradas / em queda
- insight do dolar para o proximo dia util:
    direcao = tendencia recente (cotacao x media movel de 20 dias)
    tamanho = faixa provavel (~68%) pela volatilidade dos ultimos 21 dias
Envia para o SEU WhatsApp via CallMeBot (API gratuita, uso pessoal, so texto).

Numero e apikey ficam em config_local.py (fora do GitHub).
"""
import sys
from datetime import date

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from previsao_dolar import JANELA_VOL, faixa

try:
    from config_local import WHATSAPP_APIKEY, WHATSAPP_TELEFONE
except ImportError:
    sys.exit("ERRO: crie o config_local.py a partir do config_local_exemplo.py.")

# ---------------- Configuracao ----------------
URL_API = "https://api.callmebot.com/whatsapp.php"
ARQUIVO_METRICAS = "metricas.csv"
ARQUIVO_PRECOS = "precos.csv"
REFERENCIA = "IBOV"
MOEDAS = {"Dólar": "BRL=X", "Euro": "EURBRL=X"}  # USD/BRL e EUR/BRL no Yahoo
EMOJI_MOEDA = {"Dólar": "💵", "Euro": "💶"}
EMOJI_GRUPO = {"Em alta": "📈", "Inalteradas": "➖", "Em queda": "📉"}
LIMITE_INALTERADA = 0.02   # retorno 12m entre -2% e +2% = inalterada
MEDIA_TENDENCIA = 20       # dias da media movel usada para a direcao do dolar
FECHAMENTO = "Beijinhos 😘"


# ---------------- Formatacao ----------------
def num(x, casas=2):
    """1234.5 -> '1.234,50' (padrao brasileiro)."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, sinal=True):
    fmt = "{:+.1f}%" if sinal else "{:.1f}%"
    return fmt.format(x * 100).replace(".", ",")


# ---------------- Dados ----------------
def baixar_moeda(ticker):
    dados = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
    if dados.empty:
        sys.exit(f"ERRO: nenhum dado retornado para {ticker}.")
    return dados["Close"].squeeze().dropna()


def proximo_dia_util():
    """Proximo dia util (seg-sex). Feriados nao sao considerados."""
    return (pd.Timestamp(date.today()) + pd.offsets.BDay(1)).strftime("%d/%m")


# ---------------- Blocos da mensagem ----------------
def bloco_moedas(series):
    linhas = []
    for nome, serie in series.items():
        variacao_dia = serie.iloc[-1] / serie.iloc[-2] - 1
        linhas.append(f"{EMOJI_MOEDA.get(nome, '*')} {nome}: R$ {num(serie.iloc[-1], 4)} ({pct(variacao_dia)} no dia)")
    return linhas


def bloco_acoes(metricas, data_ref):
    acoes = metricas.drop(REFERENCIA).sort_values("Retorno_12m", ascending=False)
    ret = acoes["Retorno_12m"]

    grupos = {
        "Em alta": ret[ret > LIMITE_INALTERADA],
        "Inalteradas": ret[ret.abs() <= LIMITE_INALTERADA],
        "Em queda": ret[ret < -LIMITE_INALTERADA],
    }

    linhas = [f"🏦 *Ações - relação 12 meses* (fechamento {data_ref})"]
    for titulo, grupo in grupos.items():
        linhas += ["", f"{EMOJI_GRUPO[titulo]} {titulo}:"]
        if grupo.empty:
            linhas.append("* nenhuma")
        for ativo, valor in grupo.items():
            linhas.append(f"* {ativo}: {pct(valor)}")
    return linhas


def insight_dolar(serie):
    preco = serie.iloc[-1]
    media = serie.tail(MEDIA_TENDENCIA).mean()
    direcao = "queda" if preco < media else "alta"

    retornos_log = np.log(serie / serie.shift(1)).dropna()
    vol_21d = retornos_log.tail(JANELA_VOL).std()
    minimo, maximo = faixa(preco, vol_21d, 1.0)  # ~68%

    return (
        f"💡 *Insights do dia:* Com base nesses números, o Dólar está em tendência de "
        f"{direcao.upper()} e, para {proximo_dia_util()}, a variação provável é de até "
        f"{pct(vol_21d, False)} (entre R$ {num(minimo)} e R$ {num(maximo)})."
    )


def montar_mensagem():
    metricas = pd.read_csv(ARQUIVO_METRICAS, index_col="Ativo")
    precos = pd.read_csv(ARQUIVO_PRECOS, index_col="Data", parse_dates=True)
    data_ref = precos.index.max().strftime("%d/%m")
    series = {nome: baixar_moeda(ticker) for nome, ticker in MOEDAS.items()}

    linhas = [f"📊 *Números da Bolsa de Hoje* - {date.today().strftime('%d/%m/%Y')}", ""]
    linhas += bloco_moedas(series)
    linhas.append("")
    linhas += bloco_acoes(metricas, data_ref)
    linhas += ["", insight_dolar(series["Dólar"]), "", FECHAMENTO]
    return "\n".join(linhas)


# ---------------- Envio ----------------
def enviar(texto):
    parametros = {"phone": WHATSAPP_TELEFONE, "text": texto, "apikey": WHATSAPP_APIKEY}
    try:
        resposta = requests.get(URL_API, params=parametros, timeout=30)
    except requests.exceptions.RequestException as erro:
        sys.exit(f"ERRO de conexao com o CallMeBot (rede bloqueada?): {erro}")

    # Remove as tags HTML da resposta para conseguir ler o status
    texto_resposta = " ".join(resposta.text.replace("<", " <").split())
    texto_limpo = "".join(
        parte.split(">", 1)[-1] for parte in texto_resposta.split("<")
    ).strip()

    # O status ("Message queued" ou o erro) fica no FINAL da resposta
    print(f"Resposta do CallMeBot (HTTP {resposta.status_code}), final: ...{texto_limpo[-200:]}")

    if resposta.status_code != 200 or "queued" not in texto_limpo.lower():
        sys.exit("ERRO: o servico nao confirmou 'Message queued' - veja a resposta acima.")
    print("Mensagem na fila do CallMeBot. Chega na conversa com o bot em alguns segundos.")


def main():
    texto = montar_mensagem()
    print("=== Mensagem ===")
    print(texto)
    print("================\n")
    enviar(texto)


if __name__ == "__main__":
    main()