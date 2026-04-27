# ============================================================
# PRUEBA YFINANCE - SOLO CONSOLA (SIN EXCEL)
# ============================================================

import yfinance as yf
import pandas as pd
from datetime import datetime


TICKERS = [
    "ADBE",
    "MSFT",
    "CRM",
    "NOW",
    "UBER",
    "ORCL"
]


def safe_get(dictionary, key):
    try:
        return dictionary.get(key, None)
    except Exception:
        return None


# =========================
# PRECIO
# =========================
def get_price_data(ticker):
    tk = yf.Ticker(ticker)
    hist = tk.history(period="1y", interval="1d")

    if hist.empty:
        return {}

    hist["EMA100"] = hist["Close"].ewm(span=100, adjust=False).mean()
    hist["EMA200"] = hist["Close"].ewm(span=200, adjust=False).mean()

    last = hist.iloc[-1]

    precio_actual = float(last["Close"])
    ema100 = float(last["EMA100"])
    ema200 = float(last["EMA200"])
    max_52w = float(hist["Close"].max())

    vol_5d = float(hist["Volume"].tail(5).mean())
    vol_20d = float(hist["Volume"].tail(20).mean())

    return {
        "PRECIO_ACTUAL": precio_actual,
        "EMA100": ema100,
        "EMA200": ema200,
        "PCT_VS_MAX_52W": precio_actual / max_52w - 1 if max_52w else None,
        "PCT_VS_EMA200": precio_actual / ema200 - 1 if ema200 else None,
        "VOL_RELATIVO": vol_5d / vol_20d if vol_20d else None,
    }


# =========================
# INFO GENERAL
# =========================
def get_info_data(ticker):
    tk = yf.Ticker(ticker)
    info = tk.info

    return {
        "SECTOR": safe_get(info, "sector"),
        "TRAILING_PE": safe_get(info, "trailingPE"),
        "FORWARD_PE": safe_get(info, "forwardPE"),
        "PEG": safe_get(info, "pegRatio"),
        "REV_GROWTH": safe_get(info, "revenueGrowth"),
        "EPS_GROWTH": safe_get(info, "earningsGrowth"),
        "OP_MARGIN": safe_get(info, "operatingMargins"),
        "NET_MARGIN": safe_get(info, "profitMargins"),
        "FCF_INFO": safe_get(info, "freeCashflow"),
    }


# =========================
# FINANCIALES
# =========================
def get_financials(ticker):
    tk = yf.Ticker(ticker)
    data = {}

    try:
        qf = tk.quarterly_financials

        if not qf.empty:
            latest = qf.columns[0]
            prev = qf.columns[1] if len(qf.columns) > 1 else None

            rev = qf.loc["Total Revenue", latest] if "Total Revenue" in qf.index else None
            op = qf.loc["Operating Income", latest] if "Operating Income" in qf.index else None
            net = qf.loc["Net Income", latest] if "Net Income" in qf.index else None

            data["Q_REV"] = rev
            data["Q_OP"] = op
            data["Q_NET"] = net

            if prev is not None:
                prev_rev = qf.loc["Total Revenue", prev] if "Total Revenue" in qf.index else None
                data["REV_QOQ"] = rev / prev_rev - 1 if rev and prev_rev else None

            data["OP_MARGIN_CALC"] = op / rev if rev and op else None
            data["NET_MARGIN_CALC"] = net / rev if rev and net else None

    except Exception as e:
        data["FIN_ERROR"] = str(e)

    return data


# =========================
# CASHFLOW (FCF)
# =========================
def get_cashflow(ticker):
    tk = yf.Ticker(ticker)
    data = {}

    try:
        qcf = tk.quarterly_cashflow

        if not qcf.empty:
            latest = qcf.columns[0]
            prev = qcf.columns[1] if len(qcf.columns) > 1 else None

            op_cf = qcf.loc["Operating Cash Flow", latest] if "Operating Cash Flow" in qcf.index else None
            capex = qcf.loc["Capital Expenditure", latest] if "Capital Expenditure" in qcf.index else None

            fcf = op_cf + capex if op_cf and capex else None

            data["Q_FCF"] = fcf

            if prev is not None:
                prev_op_cf = qcf.loc["Operating Cash Flow", prev] if "Operating Cash Flow" in qcf.index else None
                prev_capex = qcf.loc["Capital Expenditure", prev] if "Capital Expenditure" in qcf.index else None
                prev_fcf = prev_op_cf + prev_capex if prev_op_cf and prev_capex else None

                data["FCF_QOQ"] = fcf / prev_fcf - 1 if fcf and prev_fcf else None

    except Exception as e:
        data["CF_ERROR"] = str(e)

    return data


# =========================
# PROCESAMIENTO
# =========================
def process_ticker(ticker):
    print(f"\n--- {ticker} ---")

    row = {
        "TICKER": ticker,
        "DATE": datetime.now().strftime("%Y-%m-%d"),
    }

    try:
        row.update(get_price_data(ticker))
        row.update(get_info_data(ticker))
        row.update(get_financials(ticker))
        row.update(get_cashflow(ticker))

    except Exception as e:
        row["ERROR"] = str(e)

    return row


# =========================
# MAIN
# =========================
def main():
    results = []

    for ticker in TICKERS:
        results.append(process_ticker(ticker))

    df = pd.DataFrame(results)

    print("\n================ RESULTADO ================\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
