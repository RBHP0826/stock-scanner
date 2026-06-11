import FinanceDataReader as fdr
try:
    df_desc = fdr.StockListing('KRX-DESC')
    print("KRX-DESC Columns:", df_desc.columns.tolist())
    print(df_desc[['Code', 'Name', 'Sector', 'Industry']].head(5))
except Exception as e:
    print("KRX-DESC Error:", e)
