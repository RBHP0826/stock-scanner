import yfinance as yf
import FinanceDataReader as fdr
import time

print("KRX 종목 목록 로드 중...")
df_krx = fdr.StockListing('KRX')
if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
    df_krx['Code'] = df_krx['Symbol']

yf_tickers = []
for _, row in df_krx.iterrows():
    symbol = str(row['Code'])
    market = str(row.get('Market', ''))
    if market == 'KOSPI':
        yf_symbol = f"{symbol}.KS"
    elif market == 'KOSDAQ':
        yf_symbol = f"{symbol}.KQ"
    else:
        yf_symbol = f"{symbol}.KS"
    yf_tickers.append(yf_symbol)

print(f"총 {len(yf_tickers)}개 종목 yfinance 다운로드 시작...")
start_time = time.time()
chunk = yf_tickers[:500]  # 500개만 먼저 테스트
df_chunk = yf.download(chunk, start="2026-06-17", end="2026-06-18", group_by='ticker', threads=True, progress=False)
end_time = time.time()
print(f"500개 다운로드 완료! 소요시간: {end_time - start_time:.2f}초")
print("columns:", df_chunk.columns.levels[0][:5] if hasattr(df_chunk.columns, 'levels') else df_chunk.columns[:5])
