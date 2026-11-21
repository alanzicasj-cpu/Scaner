import ccxt
import pandas as pd
import time

# Configurações de API (Apenas leitura, não precisa de chaves privadas para scan)
exchange = ccxt.binance()

def get_anomaly_detection():
    print("Escaneando mercado em busca de anomalias de volume...")
    
    # Busca todos os pares de USDT
    markets = exchange.load_markets()
    symbols = [symbol for symbol in markets if '/USDT' in symbol]
    
    for symbol in symbols:
        try:
            # Busca candles de 1 minuto
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Cálculo Matemático
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].iloc[-60:-1].mean()
            price_change = ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
            
            # Critério: Volume 5x maior que a média E alta de preço > 0.5% no minuto
            if current_volume > (avg_volume * 5) and price_change > 0.5:
                print(f"🚨 ALERTA DE PUMP: {symbol}")
                print(f"Volume Atual: {current_volume:.2f} | Média: {avg_volume:.2f}")
                print(f"Variação no minuto: {price_change:.2f}%")
                print("-" * 30)
                
        except Exception:
            continue

# Loop de execução a cada 30 segundos
while True:
    get_anomaly_detection()
    time.sleep(30)
