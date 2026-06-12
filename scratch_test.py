from stock_scanner import StockScanner
scanner = StockScanner()
df = scanner.get_coin_symbols()
print('Checking COIN...')
c = 0
for _, r in df.head(50).iterrows():
    res = scanner.analyze_stock(r['Symbol'], 'COIN')
    if res and res['score'] >= 50:
        print(res['symbol'], res['score'])
        c += 1
print('Total >= 50:', c)
