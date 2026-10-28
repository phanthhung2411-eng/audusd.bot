import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

# ==================== CẤU HÌNH CỦA BẠN ====================
BOT_TOKEN = "9207280539:AAFfKSPIDfl6ZuB4s8GUDvpH_8x-iXMKhPc"
CHAT_ID = 7183246588
SYMBOL = "AUDUSD=X"
# ==========================================================

def get_vietnam_time():
    utc_now = datetime.now(timezone.utc)
    vn_time = utc_now + timedelta(hours=7)
    return vn_time.strftime('%Y-%m-%d %H:%M:%S')

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get("ok", False)
    except:
        return False

def fetch_forex_data(symbol, interval, period):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df = df.reset_index()
        time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        df = df.rename(columns={time_col: 'timestamp', 'Close': 'close'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if df['timestamp'].dt.tz is not None:
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Ho_Chi_Minh')
        else:
            df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=7)
        return df
    except Exception as e:
        print(f"Lỗi tải dữ liệu: {e}")
        return None

def check_strategy():
    print(f"[{get_vietnam_time()}] Đang quét dữ liệu Forex AUDUSD...")
    
    df_h1 = fetch_forex_data(SYMBOL, interval='60m', period='5d')
    df_m5 = fetch_forex_data(SYMBOL, interval='5m', period='2d')
    
    if df_h1 is None or df_m5 is None or len(df_h1) < 25 or len(df_m5) < 25:
        print("Đang chờ dữ liệu thị trường...")
        return

    h1_close = float(df_h1['close'].iloc[-1])
    h1_time = df_h1['timestamp'].iloc[-1]
    m5_close = float(df_m5['close'].iloc[-1])
    m5_time = df_m5['timestamp'].iloc[-1]

    # Tính EMA H1
    df_h1['ema8'] = df_h1['close'].ewm(span=8, adjust=False).mean()
    df_h1['ema21'] = df_h1['close'].ewm(span=21, adjust=False).mean()
    h1_ema8 = float(df_h1['ema8'].iloc[-1])
    h1_ema21 = float(df_h1['ema21'].iloc[-1])

    # Tính EMA M5
    df_m5['ema8'] = df_m5['close'].ewm(span=8, adjust=False).mean()
    df_m5['ema13'] = df_m5['close'].ewm(span=13, adjust=False).mean()
    df_m5['ema21'] = df_m5['close'].ewm(span=21, adjust=False).mean()
    m5_ema8 = float(df_m5['ema8'].iloc[-1])
    m5_ema13 = float(df_m5['ema13'].iloc[-1])
    m5_ema21 = float(df_m5['ema21'].iloc[-1])

    print(f"-> H1: {h1_close:.5f} | M5: {m5_close:.5f}")

    # Điều kiện MUA
    cond_h1_buy = (h1_close > h1_ema8) and (h1_ema8 > h1_ema21)
    cond_m5_buy = (m5_close > m5_ema8) and (m5_ema8 > m5_ema13) and (m5_ema13 > m5_ema21)

    if cond_h1_buy and cond_m5_buy:
        msg = f"TÍN HIỆU MUA (LONG) - AUDUSD\n\nKhung H1: {h1_close:.5f} > EMA8 > EMA21\nKhung M5: {m5_close:.5f} > EMA8 > EMA13 > EMA21\nThời gian M5: {m5_time}"
        send_telegram_alert(msg)
        return True

    # Điều kiện BÁN
    cond_h1_sell = (h1_close < h1_ema8) and (h1_ema8 < h1_ema21)
    cond_m5_sell = (m5_close < m5_ema8) and (m5_ema8 < m5_ema13) and (m5_ema13 < m5_ema21)

    if cond_h1_sell and cond_m5_sell:
        msg = f"TÍN HIỆU MUA / TÍN HIỆU BÁN (SHORT) - AUDUSD\n\nKhung H1: {h1_close:.5f} < EMA8 < EMA21\nKhung M5: {m5_close:.5f} < EMA8 < EMA13 < EMA21\nThời gian M5: {m5_time}"
        send_telegram_alert(msg)
        return True

    return False

if __name__ == "__main__":
    send_telegram_alert("Bot quét tín hiệu Forex AUDUSD đã khởi động trên Cloud 24/7!")
    while True:
        try:
            check_strategy()
        except Exception as e:
            print(f"Lỗi: {e}")
        time.sleep(180)