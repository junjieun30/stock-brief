"""상승/하락 상위 스캔용 기본 유니버스 — 미국 대형주 약 120종목.

S&P 500 전체를 매일 긁으면 느리고 실패율이 높아서, 시가총액 상위 위주로
고정 리스트를 둔다. 종목을 추가/제거하려면 이 리스트만 편집하면 된다.
"""

DEFAULT_UNIVERSE: list[str] = [
    # 메가캡 테크
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "TSM", "ORCL",
    "NFLX", "AMD", "CRM", "ADBE", "CSCO", "INTC", "QCOM", "TXN", "MU", "AMAT",
    "LRCX", "KLAC", "ARM", "PLTR", "SNOW", "NOW", "PANW", "CRWD", "DDOG", "SHOP",
    "UBER", "ABNB", "INTU", "IBM", "SMCI", "MRVL", "ANET", "DELL", "APP", "COIN",
    # 금융
    "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "SCHW",
    "BLK", "C", "SPGI", "PGR", "KKR",
    # 헬스케어
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN", "DHR",
    "ISRG", "BMY", "GILD", "VRTX", "REGN",
    # 소비재 / 리테일
    "WMT", "COST", "HD", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT",
    "LOW", "TJX", "BKNG", "CMG", "DIS",
    # 산업 / 에너지 / 소재
    "GE", "CAT", "BA", "HON", "UNP", "LMT", "RTX", "DE", "UPS", "MMM",
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "OXY", "LIN", "SHW", "FCX",
    # 통신 / 유틸 / 부동산 / 기타
    "T", "VZ", "TMUS", "CMCSA", "NEE", "DUK", "SO", "AMT", "PLD", "EQIX",
    "MO", "PM", "CVS", "MDLZ", "CL",
]
