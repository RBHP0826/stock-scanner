import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import datetime
import html
import concurrent.futures

JSON_PATH = "shadowing_dictionary.json"

def fetch_historical_news(stock_name, target_date_str):
    try:
        dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        # 구글 뉴스는 날짜 포맷이 YYYY-MM-DD
        start_date = (dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        
        query = f"{stock_name} 특징주 OR 급등 after:{start_date} before:{end_date}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        if items:
            for item in items[:3]:
                title = item.find('title').text
                if title:
                    title = html.unescape(title)
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    if stock_name in title:
                        return f"[뉴스] {title}"
                        
            first_title = html.unescape(items[0].find('title').text)
            if " - " in first_title:
                first_title = first_title.rsplit(" - ", 1)[0]
            return f"[뉴스] {first_title}"
            
    except Exception as e:
        pass
    
    return None

def process_stock(s, target_date_str):
    if "[과거데이터]" in s.get("reason", ""):
        news_reason = fetch_historical_news(s["name"], target_date_str)
        if news_reason:
            s["reason"] = news_reason
            return True
    return False

def run_news_update():
    print("과거 쉐도잉 데이터 뉴스 기사 검색 시작...")
    if not os.path.exists(JSON_PATH):
        return
        
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
        
    tasks = []
    # Collect tasks
    for r in d.get("records", []):
        target_date = r["date"]
        for s in r.get("details", []):
            if "[과거데이터]" in s.get("reason", ""):
                tasks.append((s, target_date))
                
    print(f"총 {len(tasks)}개의 종목에 대해 과거 뉴스 검색을 진행합니다...")
    
    import threading
    progress = 0
    lock = threading.Lock()
    
    def worker(task):
        nonlocal progress
        s, target_date = task
        changed = process_stock(s, target_date)
        with lock:
            progress += 1
            if progress % 20 == 0:
                print(f"진행 상황: {progress} / {len(tasks)}", flush=True)
        return changed

    updated = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(worker, tasks))
        if any(results):
            updated = True
            
    if updated:
        # Re-aggregate reasons in records
        for r in d.get("records", []):
            r["reason"] = " | ".join([f"{s['name']}: {s['reason']}" for s in r.get("details", [])])
            
        # Re-aggregate dictionary reasons
        for entry in d.get("dictionary", []):
            stocks_in_entry = [s.strip() for s in entry.get("stocks", "").split(",") if s.strip()]
            
            # Find the latest reasons from records
            reason_map = {}
            for r in d.get("records", []):
                for s in r.get("details", []):
                    reason_map[s["name"]] = s["reason"]
                    
            entry_reasons = []
            for stock_name in stocks_in_entry:
                r_str = reason_map.get(stock_name, entry.get("reason"))
                entry_reasons.append(f"{stock_name}: {r_str}")
            entry["reason"] = " | ".join(entry_reasons)
            
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        print("모든 과거 뉴스가 업데이트 되었습니다!")
    else:
        print("업데이트할 항목이 없습니다.")

if __name__ == "__main__":
    run_news_update()
