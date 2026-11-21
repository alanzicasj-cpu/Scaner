import os
import time
import ccxt
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

VOLUME_MULTIPLIER = 3.0
INTERVALO_SEGUNDOS = 300
TIMEFRAME = "5m"
LIMITE_PARES = 30


def enviar_telegram(mensagem: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Falha ao enviar Telegram: {e}")


def rodar_ciclo() -> None:
    print("Iniciando varredura na OKX...")
    exchange = ccxt.okx({"enableRateLimit": True})
    markets = exchange.load_markets()

    pares = [
        symbol for symbol, market in markets.items()
        if market.get("active") and market.get("quote") == "USDT" and market.get("spot")
    ][:LIMITE_PARES]

    alertas = []

    for symbol in pares:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=21)
            if not candles or len(candles) < 6:
                continue

            ultimo = candles[-1]
            vol_atual = ultimo[5] or 0
            preco_atual = ultimo[4] or 0

            vols_anteriores = [c[5] for c in candles[:-1] if c[5] is not None]
            if not vols_anteriores:
                continue

            media_vol = sum(vols_anteriores) / len(vols_anteriores)
            if media_vol > 0 and vol_atual >= media_vol * VOLUME_MULTIPLIER:
                fator = vol_atual / media_vol
                alertas.append(f"• {symbol} | Preço: {preco_atual} | Vol: {fator:.1f}x")
        except Exception as e:
            print(f"Erro no par {symbol}: {e}")
            time.sleep(0.2)

    if alertas:
        msg = "🚨 Pico de volume (OKX - 5m):\n\n" + "\n".join(alertas)
        print(msg)
        enviar_telegram(msg)
    else:
        print(f"Ciclo finalizado ({TIMEFRAME}): sem picos >= {VOLUME_MULTIPLIER:.1f}x.")


if __name__ == "__main__":
    enviar_telegram("🤖 Scanner iniciado.")

    while True:
        try:
            rodar_ciclo()
        except Exception as e:
            print(f"Erro geral no ciclo: {e}")
        time.sleep(INTERVALO_SEGUNDOS)
