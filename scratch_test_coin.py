from stock_scanner import StockScanner
scanner = StockScanner()
symbols_df = scanner.get_coin_symbols().head(5)
print('Symbols:', len(symbols_df))
results = []
for _, row in symbols_df.iterrows():
    res = scanner.analyze_stock(row['Symbol'], 'COIN')
    print(row['Symbol'], res['score'] if res else 'None')
    if res:
        results.append(res)
print('Total:', len(results))
