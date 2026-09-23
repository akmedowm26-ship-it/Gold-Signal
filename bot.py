import os
import time
import requests
import pandas as pd

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = "5m"
CHECK_SECONDS = 60

RSI_PERIOD = 1000
MACD_FAST = 10
MACD_SLOW = 22
MACD_SIGNAL = 4

SYMBOLS = {
    "XAUUSD": "GC=F",
    "BTCUSD": "BTC-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDCHF": "CHF=X",
    "USDCAD": "CAD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "EURAUD": "EURAUD=X",
    "EURCAD": "EURCAD=X",
    "EURCHF": "EURCHF=X",
    "EURNZD": "EURNZD=X",
    "GBPJPY": "GBPJPY=X",
    "GBPAUD": "GBPAUD=X",
    "GBPCAD": "GBPCAD=X",
    "GBPCHF": "GBPCHF=X",
    "GBPNZD": "GBPNZD=X",
    "AUDJPY": "AUDJPY=X",
    "AUDCAD": "AUDCAD=X",
    "AUDCHF": "AUDCHF=X",
    "AUDNZD": "AUDNZD=X",
    "CADJPY": "CADJPY=X",
    "CADCHF": "CADCHF=X",
    "CHFJPY": "CHFJPY=X",
    "NZDJPY": "NZDJPY=X",
    "NZDCAD": "NZDCAD=X",
    "NZDCHF": "NZDCHF=X",
}

last_signal = {}
tp_sent = {}


def send_message(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram secrets yok!")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )


def get_data(ticker):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{ticker}?interval=5m&range=5d"
    )

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    r.raise_for_status()

    data = r.json()["chart"]["result"][0]

    close = data["indicators"]["quote"][0]["close"]

    df = pd.DataFrame({"close": close})
    df = df.dropna()

    return df


def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-10)

    return 100 - (100 / (1 + rs))


def check_symbol(name, ticker):
    try:
        df = get_data(ticker)

        if len(df) < RSI_PERIOD + 30:
            print(name, "data az")
            return

        close = df["close"]

        rsi = calculate_rsi(close, RSI_PERIOD)

        ema_fast = close.ewm(
            span=MACD_FAST,
            adjust=False
        ).mean()

        ema_slow = close.ewm(
            span=MACD_SLOW,
            adjust=False
        ).mean()

        macd = ema_fast - ema_slow
        signal = macd.ewm(
            span=MACD_SIGNAL,
            adjust=False
        ).mean()

        rsi_now = rsi.iloc[-1]

        macd_prev = macd.iloc[-2]
        signal_prev = signal.iloc[-2]

        macd_now = macd.iloc[-1]
        signal_now = signal.iloc[-1]

        bullish_cross = (
            macd_prev <= signal_prev
            and macd_now > signal_now
        )

        bearish_cross = (
            macd_prev >= signal_prev
            and macd_now < signal_now
        )

        price = close.iloc[-1]

        if 10 <= rsi_now <= 15 and bullish_cross:
            if last_signal.get(name) != "BUY":
                send_message(
                    f"🟢 BUY SIGNAL\n\n"
                    f"Symbol: {name}\n"
                    f"Timeframe: M5\n"
                    f"Price: {price:.5f}\n"
                    f"RSI: {rsi_now:.2f}\n"
                    f"MACD: 10/22/4\n\n"
                    f"TP1: RSI 50"
                )

                last_signal[name] = "BUY"
                tp_sent[name] = False

        elif 85 <= rsi_now <= 90 and bearish_cross:
            if last_signal.get(name) != "SELL":
                send_message(
                    f"🔴 SELL SIGNAL\n\n"
                    f"Symbol: {name}\n"
                    f"Timeframe: M5\n"
                    f"Price: {price:.5f}\n"
                    f"RSI: {rsi_now:.2f}\n"
                    f"MACD: 10/22/4\n\n"
                    f"TP1: RSI 50"
                )

                last_signal[name] = "SELL"
                tp_sent[name] = False

        current_signal = last_signal.get(name)

        if current_signal and not tp_sent.get(name, False):
            if 48 <= rsi_now <= 52:
                send_message(
                    f"🎯 TP1\n\n"
                    f"Symbol: {name}\n"
                    f"RSI reached 50\n"
                    f"Original signal: {current_signal}"
                )

                tp_sent[name] = True

        print(
            name,
            "Price:", price,
            "RSI:", round(rsi_now, 2)
        )

    except Exception as e:
        print(name, "ERROR:", e)


def main():
    send_message(
        "🤖 RSI + MACD Signal Bot started\n"
        "Timeframe: M5"
    )

    while True:
        for name, ticker in SYMBOLS.items():
            check_symbol(name, ticker)
            time.sleep(2)

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
