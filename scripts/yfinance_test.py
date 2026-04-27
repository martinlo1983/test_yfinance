# ============================================================
# PRUEBA YFINANCE - SOLO CONSOLA (SIN EXCEL)
# ============================================================
import yfinance as yf
import pandas as pd
from datetime import datetime

TICKERS = ["ADBE", "MSFT", "CRM", "NOW", "UBER", "ORCL"]


def safe_value(df, row_name, col):
    if df is None or df.empty:
        return None
    if row_name not in df.index:
        return None
    try:
        return df.loc[row_name, col]
    except Exception:
        return None


def format_number(x):
    if x is None or pd.isna(x):
        return ""
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return str(x)


def format_pct(x):
    if x is None or pd.isna(x):
        return ""
    try:
        return f"{float(x) * 100:.2f}%"
    except Exception:
        return str(x)


def print_price_block(ticker_obj):
    hist = ticker_obj.history(period="1y", interval="1d")

    if hist.empty:
        print("PRECIO: sin datos")
        return

    hist["EMA100"] = hist["Close"].ewm(span=100, adjust=False).mean()
    hist["EMA200"] = hist["Close"].ewm(span=200, adjust=False).mean()

    last = hist.iloc[-1]
    price = float(last["Close"])
    ema100 = float(last["EMA100"])
    ema200 = float(last["EMA200"])
    max_52w = float(hist["Close"].max())

    print("\n[PRECIO / TECNICO]")
    print(f"Precio actual:      {price:.2f}")
    print(f"EMA100:             {ema100:.2f}")
    print(f"EMA200:             {ema200:.2f}")
    print(f"% vs Max 52W:       {format_pct(price / max_52w - 1)}")
    print(f"% vs EMA200:        {format_pct(price / ema200 - 1)}")


def print_info_block(ticker_obj):
    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    print("\n[INFO ACTUAL]")
    fields = {
        "Sector": "sector",
        "Industria": "industry",
        "Trailing PE": "trailingPE",
        "Forward PE": "forwardPE",
        "PEG": "pegRatio",
        "Revenue Growth": "revenueGrowth",
        "Earnings Growth": "earningsGrowth",
        "Operating Margin": "operatingMargins",
        "Net Margin": "profitMargins",
        "Free Cash Flow": "freeCashflow",
    }

    for label, key in fields.items():
        value = info.get(key)
        if key in ["revenueGrowth", "earningsGrowth", "operatingMargins", "profitMargins"]:
            value = format_pct(value)
        elif key == "freeCashflow":
            value = format_number(value)
        print(f"{label}: {value}")


def build_income_table(financials):
    rows = []

    if financials is None or financials.empty:
        return pd.DataFrame()

    cols = list(financials.columns[:4])

    for col in cols:
        revenue = safe_value(financials, "Total Revenue", col)
        op_income = safe_value(financials, "Operating Income", col)
        net_income = safe_value(financials, "Net Income", col)
        diluted_eps = safe_value(financials, "Diluted EPS", col)
        basic_eps = safe_value(financials, "Basic EPS", col)

        rows.append({
            "Periodo": str(col.date()) if hasattr(col, "date") else str(col),
            "Revenue": revenue,
            "Operating Income": op_income,
            "Net Income": net_income,
            "Op Margin": op_income / revenue if revenue not in [None, 0] and op_income is not None else None,
            "Net Margin": net_income / revenue if revenue not in [None, 0] and net_income is not None else None,
            "Diluted EPS": diluted_eps,
            "Basic EPS": basic_eps,
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["Revenue Growth vs Prev"] = df["Revenue"].pct_change(periods=-1)
        df["Net Income Growth vs Prev"] = df["Net Income"].pct_change(periods=-1)

    return df


def build_cashflow_table(cashflow):
    rows = []

    if cashflow is None or cashflow.empty:
        return pd.DataFrame()

    cols = list(cashflow.columns[:4])

    for col in cols:
        operating_cf = safe_value(cashflow, "Operating Cash Flow", col)
        capex = safe_value(cashflow, "Capital Expenditure", col)

        fcf = operating_cf + capex if operating_cf is not None and capex is not None else None

        rows.append({
            "Periodo": str(col.date()) if hasattr(col, "date") else str(col),
            "Operating Cash Flow": operating_cf,
            "CapEx": capex,
            "Free Cash Flow Calc": fcf,
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["FCF Growth vs Prev"] = df["Free Cash Flow Calc"].pct_change(periods=-1)

    return df


def print_table(title, df):
    print(f"\n[{title}]")

    if df.empty:
        print("Sin datos disponibles")
        return

    df_print = df.copy()

    money_cols = [
        "Revenue",
        "Operating Income",
        "Net Income",
        "Operating Cash Flow",
        "CapEx",
        "Free Cash Flow Calc",
    ]

    pct_cols = [
        "Op Margin",
        "Net Margin",
        "Revenue Growth vs Prev",
        "Net Income Growth vs Prev",
        "FCF Growth vs Prev",
    ]

    for col in money_cols:
        if col in df_print.columns:
            df_print[col] = df_print[col].apply(format_number)

    for col in pct_cols:
        if col in df_print.columns:
            df_print[col] = df_print[col].apply(format_pct)

    print(df_print.to_string(index=False))


def process_ticker(ticker):
    print("\n" + "=" * 100)
    print(f"TICKER: {ticker} | RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    tk = yf.Ticker(ticker)

    print_price_block(tk)
    print_info_block(tk)

    annual_income = build_income_table(tk.financials)
    quarterly_income = build_income_table(tk.quarterly_financials)

    annual_cashflow = build_cashflow_table(tk.cashflow)
    quarterly_cashflow = build_cashflow_table(tk.quarterly_cashflow)

    print_table("INCOME ANUAL - ULTIMOS 4 PERIODOS", annual_income)
    print_table("INCOME TRIMESTRAL - ULTIMOS 4 PERIODOS", quarterly_income)
    print_table("CASHFLOW ANUAL - ULTIMOS 4 PERIODOS", annual_cashflow)
    print_table("CASHFLOW TRIMESTRAL - ULTIMOS 4 PERIODOS", quarterly_cashflow)


def main():
    for ticker in TICKERS:
        try:
            process_ticker(ticker)
        except Exception as e:
            print(f"\nERROR procesando {ticker}: {e}")


if __name__ == "__main__":
    main()
