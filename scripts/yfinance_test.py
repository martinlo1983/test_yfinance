# ============================================================
# PRUEBA YFINANCE - SOLO CONSOLA (SIN EXCEL)
# ============================================================
import yfinance as yf
import pandas as pd
from datetime import datetime

TICKERS = ["OXY","MU","ADBE", "MSFT", "CRM", "NOW", "UBER", "ORCL"]


# ============================================================
# HELPERS
# ============================================================

def safe_value(df, row_name, col):
    if df is None or df.empty:
        return None
    if row_name not in df.index:
        return None
    try:
        return df.loc[row_name, col]
    except Exception:
        return None


def safe_get(obj, attr):
    try:
        value = getattr(obj, attr)
        if value is None:
            return pd.DataFrame()
        return value
    except Exception as e:
        print(f"Error obteniendo {attr}: {e}")
        return pd.DataFrame()


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


def format_raw(x):
    if x is None or pd.isna(x):
        return ""
    return x


def print_df(title, df):
    print(f"\n[{title}]")

    if df is None or df.empty:
        print("Sin datos disponibles")
        return

    print(df.to_string())


# ============================================================
# PRECIO / TECNICO
# ============================================================

def print_price_block(tk):
    hist = tk.history(period="1y", interval="1d")

    if hist.empty:
        print("\n[PRECIO / TECNICO]")
        print("Sin datos disponibles")
        return

    hist["EMA100"] = hist["Close"].ewm(span=100, adjust=False).mean()
    hist["EMA200"] = hist["Close"].ewm(span=200, adjust=False).mean()

    last = hist.iloc[-1]

    price = float(last["Close"])
    ema100 = float(last["EMA100"])
    ema200 = float(last["EMA200"])
    max_52w = float(hist["Close"].max())

    vol_5d = float(hist["Volume"].tail(5).mean())
    vol_20d = float(hist["Volume"].tail(20).mean())

    print("\n[PRECIO / TECNICO]")
    print(f"Precio actual:       {price:.2f}")
    print(f"EMA100:              {ema100:.2f}")
    print(f"EMA200:              {ema200:.2f}")
    print(f"% vs Max 52W:        {format_pct(price / max_52w - 1)}")
    print(f"% vs EMA100:         {format_pct(price / ema100 - 1)}")
    print(f"% vs EMA200:         {format_pct(price / ema200 - 1)}")
    print(f"Vol relativo 5/20d:  {vol_5d / vol_20d:.2f}" if vol_20d else "Vol relativo: sin dato")


# ============================================================
# INFO ACTUAL
# ============================================================

def print_info_block(tk):
    try:
        info = tk.info
    except Exception:
        info = {}

    print("\n[INFO ACTUAL]")
    fields = {
        "Short Name": "shortName",
        "Sector": "sector",
        "Industria": "industry",
        "Trailing PE": "trailingPE",
        "Forward PE": "forwardPE",
        "PEG": "pegRatio",
        "Trailing EPS": "trailingEps",
        "Forward EPS": "forwardEps",
        "Revenue Growth": "revenueGrowth",
        "Earnings Growth": "earningsGrowth",
        "Operating Margin": "operatingMargins",
        "Net Margin": "profitMargins",
        "Free Cash Flow": "freeCashflow",
        "Operating Cash Flow": "operatingCashflow",
        "Total Debt": "totalDebt",
        "Total Cash": "totalCash",
        "Next Earnings Date": "earningsDate",
        "Ex Dividend Date": "exDividendDate",
    }

    for label, key in fields.items():
        value = info.get(key)

        if key in ["revenueGrowth", "earningsGrowth", "operatingMargins", "profitMargins"]:
            value = format_pct(value)
        elif key in ["freeCashflow", "operatingCashflow", "totalDebt", "totalCash"]:
            value = format_number(value)

        print(f"{label}: {value}")


# ============================================================
# INCOME STATEMENT
# ============================================================

def build_income_table(financials):
    if financials is None or financials.empty:
        return pd.DataFrame()

    rows = []
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


# ============================================================
# CASHFLOW / FCF
# ============================================================

def build_cashflow_table(cashflow):
    if cashflow is None or cashflow.empty:
        return pd.DataFrame()

    rows = []
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


# ============================================================
# TTM
# ============================================================

def build_ttm_table(q_income, q_cashflow):
    if q_income is None or q_income.empty:
        return pd.DataFrame()

    last_4q = q_income.head(4).copy()

    revenue_ttm = last_4q["Revenue"].sum(skipna=True)
    op_income_ttm = last_4q["Operating Income"].sum(skipna=True)
    net_income_ttm = last_4q["Net Income"].sum(skipna=True)

    fcf_ttm = None
    if q_cashflow is not None and not q_cashflow.empty:
        fcf_ttm = q_cashflow.head(4)["Free Cash Flow Calc"].sum(skipna=True)

    rows = [{
        "Revenue TTM": revenue_ttm,
        "Operating Income TTM": op_income_ttm,
        "Net Income TTM": net_income_ttm,
        "Op Margin TTM": op_income_ttm / revenue_ttm if revenue_ttm else None,
        "Net Margin TTM": net_income_ttm / revenue_ttm if revenue_ttm else None,
        "FCF TTM": fcf_ttm,
        "FCF Margin TTM": fcf_ttm / revenue_ttm if revenue_ttm and fcf_ttm is not None else None,
    }]

    return pd.DataFrame(rows)


# ============================================================
# EXPECTATIVAS / ANALYSIS
# ============================================================

def print_analysis_block(tk):
    print("\n" + "-" * 80)
    print("[EXPECTATIVAS / ANALYSIS]")
    print("-" * 80)

    analysis_items = {
        "EARNINGS ESTIMATE": "earnings_estimate",
        "REVENUE ESTIMATE": "revenue_estimate",
        "EARNINGS HISTORY": "earnings_history",
        "EPS TREND": "eps_trend",
        "EPS REVISIONS": "eps_revisions",
        "GROWTH ESTIMATES": "growth_estimates",
    }

    for title, attr in analysis_items.items():
        df = safe_get(tk, attr)
        print_df(title, df)


# ============================================================
# PRINT TABLAS FORMATEADAS
# ============================================================

def print_financial_table(title, df):
    print(f"\n[{title}]")

    if df is None or df.empty:
        print("Sin datos disponibles")
        return

    dfp = df.copy()

    money_cols = [
        "Revenue",
        "Operating Income",
        "Net Income",
        "Operating Cash Flow",
        "CapEx",
        "Free Cash Flow Calc",
        "Revenue TTM",
        "Operating Income TTM",
        "Net Income TTM",
        "FCF TTM",
    ]

    pct_cols = [
        "Op Margin",
        "Net Margin",
        "Revenue Growth vs Prev",
        "Net Income Growth vs Prev",
        "FCF Growth vs Prev",
        "Op Margin TTM",
        "Net Margin TTM",
        "FCF Margin TTM",
    ]

    for col in money_cols:
        if col in dfp.columns:
            dfp[col] = dfp[col].apply(format_number)

    for col in pct_cols:
        if col in dfp.columns:
            dfp[col] = dfp[col].apply(format_pct)

    print(dfp.to_string(index=False))


# ============================================================
# PROCESO POR TICKER
# ============================================================

def process_ticker(ticker):
    print("\n" + "=" * 100)
    print(f"TICKER: {ticker} | RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    tk = yf.Ticker(ticker)

    print_price_block(tk)
    print_info_block(tk)

    annual_income = build_income_table(safe_get(tk, "financials"))
    quarterly_income = build_income_table(safe_get(tk, "quarterly_financials"))

    annual_cashflow = build_cashflow_table(safe_get(tk, "cashflow"))
    quarterly_cashflow = build_cashflow_table(safe_get(tk, "quarterly_cashflow"))

    ttm_table = build_ttm_table(quarterly_income, quarterly_cashflow)

    print_financial_table("INCOME ANUAL - ULTIMOS 4 PERIODOS", annual_income)
    print_financial_table("INCOME TRIMESTRAL - ULTIMOS 4 PERIODOS", quarterly_income)
    print_financial_table("CASHFLOW ANUAL - ULTIMOS 4 PERIODOS", annual_cashflow)
    print_financial_table("CASHFLOW TRIMESTRAL - ULTIMOS 4 PERIODOS", quarterly_cashflow)
    print_financial_table("TTM - CALCULADO DESDE ULTIMOS 4 TRIMESTRES", ttm_table)

    print_analysis_block(tk)


# ============================================================
# MAIN
# ============================================================

def main():
    for ticker in TICKERS:
        try:
            process_ticker(ticker)
        except Exception as e:
            print(f"\nERROR procesando {ticker}: {e}")


if __name__ == "__main__":
    main()
