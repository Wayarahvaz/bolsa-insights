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

import os


def carregar_destinatarios():
    """
    Lista de (telefone, apikey).
    - No PC: le o config_local.py (formato novo DESTINATARIOS ou antigo, de um numero).
    - No GitHub Actions: le o Secret WHATSAPP_DESTINATARIOS,
      no formato "telefone:apikey;telefone:apikey".
    """
    try:
        import config_local
        return getattr(
            config_local,
            "DESTINATARIOS",
            [(config_local.WHATSAPP_TELEFONE, config_local.WHATSAPP_APIKEY)],
        )
    except ImportError:
        pass

    segredo = os.environ.get("WHATSAPP_DESTINATARIOS", "").strip()
    if not segredo:
        sys.exit("ERRO: sem config_local.py e sem o Secret WHATSAPP_DESTINATARIOS.")
    pares = [item.split(":") for item in segredo.split(";") if item.strip()]
    return [(tel.strip(), chave.strip()) for tel, chave in pares]


DESTINATARIOS = carregar_destinatarios()

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
def enviar(texto, telefone, apikey):
    """Envia para um numero. Devolve True se o servico confirmou 'Message queued'."""
    parametros = {"phone": telefone, "text": texto, "apikey": apikey}
    try:
        resposta = requests.get(URL_API, params=parametros, timeout=30)
    except requests.exceptions.RequestException as erro:
        print(f"ERRO de conexao com o CallMeBot (rede bloqueada?): {erro}")
        return False

    # Remove as tags HTML da resposta para conseguir ler o status
    texto_resposta = " ".join(resposta.text.replace("<", " <").split())
    texto_limpo = "".join(
        parte.split(">", 1)[-1] for parte in texto_resposta.split("<")
    ).strip()

    # O status ("Message queued" ou o erro) fica no FINAL da resposta
    print(f"[{telefone}] Resposta (HTTP {resposta.status_code}), final: ...{texto_limpo[-200:]}")

    if resposta.status_code != 200 or "queued" not in texto_limpo.lower():
        print(f"[{telefone}] ERRO: o servico nao confirmou 'Message queued'.")
        return False
    print(f"[{telefone}] Mensagem na fila. Chega em alguns segundos.")
    return True


def main():
    texto = montar_mensagem()
    print("=== Mensagem ===")
    print(texto)
    print("================\n")

    resultados = [enviar(texto, tel, chave) for tel, chave in DESTINATARIOS]
    print(f"\nEnviado para {sum(resultados)} de {len(resultados)} numero(s).")
    if not all(resultados):
        sys.exit(1)


if __name__ == "__main__":
    main()
