import os
import time
import ccxt
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

VOLUME_MULTIPLIER = 3.0
INTERVALO_SEGUNDOS = 300
TIMEFRAME = "5m"
LIMITE_PARES = 40


def enviar_telegram(mensagem: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Aviso: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            print(f"Erro ao enviar no Telegram: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Exceção ao enviar no Telegram: {e}")


def buscar_bases_coingecko(top_n: int = 120) -> set[str]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": top_n,
        "page": 1,
        "sparkline": "false",
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    dados = resp.json()
    return {item.get("symbol", "").upper() for item in dados if item.get("symbol")}


def criar_exchange():
    return ccxt.okx({
        "enableRateLimit": True,
    })


def get_anomaly_detection() -> None:
    print("Cruzando bases (OKX + CoinGecko) para achar ativos em comum e anomalias de volume...")
    bases_segunda_fonte = buscar_bases_coingecko(top_n=120)

    exchange = criar_exchange()
    markets = exchange.load_markets()

    simbolos_em_comum = [
        symbol for symbol, market in markets.items()
        if (
            market.get("active")
            and market.get("quote") == "USDT"
            and market.get("spot")
            and str(market.get("base", "")).upper() in bases_segunda_fonte
        )
    ][:LIMITE_PARES]

    alertas = []

    for symbol in simbolos_em_comum:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=22)
            if not ohlcv or len(ohlcv) < 6:
                continue

            ultimo_candle = ohlcv[-1]
            volume_atual = ultimo_candle[5] or 0
            preco_atual = ultimo_candle[4] or 0

            volumes_anteriores = [c[5] for c in ohlcv[:-1] if c[5] is not None]
            if not volumes_anteriores:
                continue

            media_volume = sum(volumes_anteriores) / len(volumes_anteriores)
            if media_volume > 0 and volume_atual >= media_volume * VOLUME_MULTIPLIER:
                ratio = volume_atual / media_volume
                alertas.append(
                    f"• {symbol} | Preço: {preco_atual} | Vol: {ratio:.1f}x a média"
                )
        except Exception as e:
            print(f"Erro ao analisar {symbol}: {e}")
            time.sleep(0.2)

    if alertas:
        msg = (
            "🚨 Anomalias em ativos filtrados nas 2 bases:\n\n"
            + "\n".join(alertas)
            + "\n\nConfirme visualmente na corretora."
        )
        print(msg)
        enviar_telegram(msg)
    else:
        msg = (
            f"✅ Ciclo concluído ({TIMEFRAME}): nenhuma anomalia ({VOLUME_MULTIPLIER:.1f}x) "
            f"nos {len(simbolos_em_comum)} ativos filtrados nas 2 bases."
        )
        print(msg)
        enviar_telegram(msg)


if __name__ == "__main__":
    enviar_telegram("🤖 Scanner iniciado no Railway!")

    while True:
        try:
            get_anomaly_detection()
        except Exception as e:
            erro_msg = f"⚠️ Erro no ciclo do scanner: {e}"
            print(erro_msg)
            enviar_telegram(erro_msg)
        time.sleep(INTERVALO_SEGUNDOS)
