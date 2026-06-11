import os
import json
import time
import random
import datetime
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr

JSON_PATH = "shadowing_dictionary.json"

def load_shadowing_data():
    if not os.path.exists(JSON_PATH):
        return {"dictionary": [], "records": []}
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"dictionary": [], "records": []}

def save_shadowing_data(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_backfill_yf(start_date_str, end_date_str):
    print(f"[{start_date_str} ~ {end_date_str}] yfinance 기반 백필 시작...")
    shadow_data = load_shadowing_data()
    existing_dates = {r.get("date") for r in shadow_data.get("records", [])}

    print("KRX 종목 목록 및 섹터 정보 로드 중...")
    df_krx = fdr.StockListing('KRX')
    if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
        df_krx['Code'] = df_krx['Symbol']
        
    try:
        df_desc = fdr.StockListing('KRX-DESC')[['Code', 'Sector', 'Industry']]
        sector_dict = dict(zip(df_desc['Code'], df_desc['Industry']))
        sector_dict_fallback = dict(zip(df_desc['Code'], df_desc['Sector']))
    except:
        sector_dict = {}
        sector_dict_fallback = {}

    # yfinance 형식으로 티커 변환
    yf_tickers = []
    symbol_to_name = {}
    for _, row in df_krx.iterrows():
        symbol = str(row['Code'])
        name = str(row['Name'])
        market = str(row.get('Market', ''))
        
        yf_symbol = ""
        if market == 'KOSPI':
            yf_symbol = f"{symbol}.KS"
        elif market == 'KOSDAQ':
            yf_symbol = f"{symbol}.KQ"
        else:
            yf_symbol = f"{symbol}.KS" # 기본
            
        yf_tickers.append(yf_symbol)
        symbol_to_name[yf_symbol] = (symbol, name)

    print(f"총 {len(yf_tickers)}개 종목 yfinance 다운로드 시작...")
    
    # yfinance는 한 번에 수천 개를 다운로드할 수 있습니다 (청크 단위 추천)
    chunk_size = 500
    all_daily_records = []
    
    for i in range(0, len(yf_tickers), chunk_size):
        chunk = yf_tickers[i:i+chunk_size]
        print(f"청크 다운로드 중: {i} ~ {i+len(chunk)}")
        
        # yfinance 다중 종목 다운로드 시 MultiIndex 반환
        df_chunk = yf.download(chunk, start=start_date_str, end=end_date_str, group_by='ticker', threads=True, progress=False)
        
        for yf_symbol in chunk:
            if yf_symbol not in df_chunk.columns.levels[0]:
                continue
                
            df_sym = df_chunk[yf_symbol].dropna(subset=['Close'])
            if df_sym.empty:
                continue
                
            symbol, name = symbol_to_name[yf_symbol]
            
            # Amount 및 ChagesRatio 계산
            df_sym['Amount'] = df_sym['Close'] * df_sym['Volume']
            df_sym['ChagesRatio'] = df_sym['Close'].pct_change() * 100.0
            
            df_filtered = df_sym[(df_sym['ChagesRatio'] >= 15.0) & (df_sym['Amount'] >= 50000000000)]
            
            for date_idx, day_row in df_filtered.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d")
                all_daily_records.append({
                    'Date': date_str,
                    'Symbol': symbol,
                    'Name': name,
                    'ChagesRatio': round(float(day_row['ChagesRatio']), 2) if not pd.isna(day_row['ChagesRatio']) else 0.0,
                    'Amount': float(day_row['Amount']),
                    'Close': int(day_row['Close'])
                })

    if not all_daily_records:
        print("조건에 맞는 데이터가 없습니다.")
        return

    # 날짜별 그룹핑
    date_groups = {}
    for r in all_daily_records:
        dt = r['Date']
        if dt not in date_groups:
            date_groups[dt] = []
        date_groups[dt].append(r)

    print(f"총 {len(date_groups)}일의 기록 생성 시작...")
    
    for today_str in sorted(date_groups.keys()):
        if today_str in existing_dates:
            continue
            
        day_records = date_groups[today_str]
        
        detected_stocks = []
        for row in day_records:
            symbol = row['Symbol']
            name = row['Name']
            change_rate = row['ChagesRatio']
            amount_val_krw = row['Amount']
            close_val = row['Close']
            amount_hundred_million = round(amount_val_krw / 100000000.0, 2)
            
            ind = sector_dict.get(symbol, "")
            if not ind or str(ind) == 'nan': ind = sector_dict_fallback.get(symbol, "")
            if not ind or str(ind) == 'nan': ind = "테마미분류"
            sector_name = str(ind).strip()
            
            reason_str = f"[과거데이터] 거래대금 폭발 및 급등 (섹터: {sector_name})"
            detected_stocks.append({
                "name": name,
                "code": symbol,
                "rate": change_rate,
                "amount": amount_hundred_million,
                "close": close_val,
                "industry": sector_name,
                "reason": reason_str
            })
            
        industry_groups = {}
        for s in detected_stocks:
            ind = s["industry"]
            if ind not in industry_groups: industry_groups[ind] = []
            industry_groups[ind].append(s)
            
        stock_names = [s["name"] for s in detected_stocks]
        reasons_list = [f"{s['name']}: {s['reason']}" for s in detected_stocks]
        new_stocks_str = ", ".join(stock_names)
        new_reasons_str = " | ".join(reasons_list)
        avg_rate = round(sum(s["rate"] for s in detected_stocks) / len(detected_stocks), 2)
        total_amount = int(sum(s["amount"] for s in detected_stocks))
        
        record_payload = {
            "date": today_str,
            "stocks": new_stocks_str,
            "reason": new_reasons_str,
            "keyword": "과거주도주_일괄수집",
            "average_rate": avg_rate,
            "cumulative_amount": total_amount,
            "details": detected_stocks
        }
        shadow_data["records"].append(record_payload)
        
        for ind_name, stocks_in_ind in industry_groups.items():
            stock_count = len(stocks_in_ind)
            theme_tag = "[주도테마]" if stock_count >= 3 else "[개별이슈]"
            display_theme_name = f"{theme_tag} {ind_name}"
            
            ind_stocks_str = ", ".join([s["name"] for s in stocks_in_ind])
            ind_reasons_str = " | ".join([f"{s['name']}: {s['reason']}" for s in stocks_in_ind])
            ind_avg_rate = round(sum(s["rate"] for s in stocks_in_ind) / stock_count, 2)
            ind_total_amount = int(sum(s["amount"] for s in stocks_in_ind))
            
            dict_idx = -1
            for idx, entry in enumerate(shadow_data.get("dictionary", [])):
                if ind_name in entry.get("theme", ""):
                    dict_idx = idx
                    break
                    
            if dict_idx != -1:
                existing_stocks = [s.strip() for s in shadow_data["dictionary"][dict_idx]["stocks"].split(",") if s.strip()]
                for s in stocks_in_ind:
                    if s["name"] not in existing_stocks:
                        existing_stocks.append(s["name"])
                shadow_data["dictionary"][dict_idx]["theme"] = display_theme_name
                shadow_data["dictionary"][dict_idx]["stocks"] = ", ".join(existing_stocks)
                shadow_data["dictionary"][dict_idx]["reason"] = f"({today_str} 업데이트) " + ind_reasons_str
                shadow_data["dictionary"][dict_idx]["last_updated"] = today_str
                shadow_data["dictionary"][dict_idx]["average_rate"] = ind_avg_rate
                shadow_data["dictionary"][dict_idx]["cumulative_amount"] = ind_total_amount
            else:
                shadow_data["dictionary"].append({
                    "id": f"theme_auto_backfill_{random.randint(10000, 99999)}",
                    "theme": display_theme_name,
                    "keyword": ind_name,
                    "stocks": ind_stocks_str,
                    "reason": f"({today_str} 신규 등록) " + ind_reasons_str,
                    "last_updated": today_str,
                    "average_rate": ind_avg_rate,
                    "cumulative_amount": ind_total_amount
                })
                
    shadow_data["records"].sort(key=lambda x: x["date"])
    save_shadowing_data(shadow_data)
    print("완료되었습니다!")

if __name__ == "__main__":
    # yfinance는 end date가 exclusive이므로 하루 더해줍니다.
    run_backfill_yf("2026-01-01", "2026-06-01")
