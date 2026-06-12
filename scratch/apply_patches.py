import os
import shutil

app_path = r"c:\Users\zxc02\OneDrive\Desktop\stock-scanner-main\stock_app.py"
backup_path = r"c:\Users\zxc02\OneDrive\Desktop\stock-scanner-main\stock_app.py.bak"

# 1. 백업 복사
if os.path.exists(app_path):
    shutil.copy(app_path, backup_path)
    print("★ stock_app.py 백업 완료!")

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# 2. SHADOWING_FILE 상수 및 헬퍼 함수 정의 텍스트 준비
helper_code = """# 쉐도잉 & 백과사전 파일 경로 설정
SHADOWING_FILE = os.path.join(BASE_DIR, "shadowing_dictionary.json")

def initialize_default_shadowing_data():
    \"\"\"기본 주도 테마 백과사전 및 쉐도잉 일지 예시 데이터를 반환합니다.\"\"\"
    import datetime
    t_day = datetime.datetime.now().strftime('%Y-%m-%d')
    return {
        "dictionary": [
            {
                "id": "theme_001",
                "theme": "반도체 HBM / CXL",
                "stocks": "한미반도체, 네오셈, 삼성전자, SK하이닉스",
                "reason": "엔비디아향 HBM3E/HBM4 공급 경쟁 본격화 및 AI 고성능 컴퓨팅을 위한 차세대 CXL 2.0 규격 메모리 모듈 부각",
                "last_updated": t_day
            },
            {
                "id": "theme_002",
                "theme": "인공지능 (AI) 온디바이스",
                "stocks": "제주반도체, 오픈엣지테크놀로지, 리노공업, 칩스앤미디어",
                "reason": "클라우드를 거치지 않고 단말기 자체에서 AI를 수행하는 온디바이스 기기 개화로 저전력 메모리 반도체 및 NPU IP 설계 가치 폭등",
                "last_updated": t_day
            },
            {
                "id": "theme_003",
                "theme": "초전도체 (LK-99 / PCPOSOS)",
                "stocks": "신성델타테크, 파워로직스, 서남, 덕성",
                "reason": "상온 초전도체 개발 주장 및 국내외 연구진의 학회 발표, 교차 검증 소식이 전해질 때마다 테마 전체가 극도의 변동성을 보이며 급등락",
                "last_updated": t_day
            },
            {
                "id": "theme_004",
                "theme": "2차전지 (양극재 / 리튬)",
                "stocks": "에코프로, 에코프로비엠, 포스코퓨처엠, 금양, 엘앤에프",
                "reason": "글로벌 친환경 탄소 제로 정책 수혜 및 북미 시장 중심의 대규모 배터리 핵심 양극소재 장기 공급 계약 수주에 따른 고성장성 부각",
                "last_updated": t_day
            }
        ],
        "records": [
            {
                "date": t_day,
                "keyword": "반도체",
                "stocks": "한미반도체, 네오셈",
                "reason": "기관/외인의 HBM 대량 순매수 유입 및 차세대 반도체 공정 가속화에 따른 강력한 상승 국면 진입"
            }
        ]
    }

def load_shadowing_data():
    \"\"\"로컬 JSON에서 쉐도잉 데이터를 불러옵니다. 파일이 없을 경우 기본값을 생성합니다.\"\"\"
    if os.path.exists(SHADOWING_FILE):
        try:
            with open(SHADOWING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 데이터 정합성 검증
                if "dictionary" not in data: data["dictionary"] = []
                if "records" not in data: data["records"] = []
                
                # [자동 보정] 과거 샘플 구식 날짜(2026-05-23 등)를 오늘 날짜로 자동 마이그레이션 최신화
                import datetime
                t_day = datetime.datetime.now().strftime('%Y-%m-%d')
                updated_flag = False
                for entry in data.get("dictionary", []):
                    if entry.get("last_updated") == "2026-05-23":
                        entry["last_updated"] = t_day
                        updated_flag = True
                
                if updated_flag:
                    save_shadowing_data(data)
                    
                return data
        except Exception as e:
            st.error(f"쉐도잉 데이터 로드 중 오류 발생: {e}")
            return initialize_default_shadowing_data()
    else:
        # 파일이 없으면 기본 데이터로 초기화
        data = initialize_default_shadowing_data()
        save_shadowing_data(data)
        return data

def save_shadowing_data(data):
    \"\"\"쉐도잉 데이터를 로컬 JSON에 저장합니다.\"\"\"
    try:
        with open(SHADOWING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"쉐도잉 데이터 저장 실패: {e}")
        return False

def sync_realtime_shadowing_data(scanner):
    \"\"\"실시간 한국 시장(KRX) 데이터를 분석하여 상승률 15% 이상 & 거래대금 500억 이상 터진 주도주를 자동으로 쉐도잉 및 백과사전에 반영합니다. (미달 시 300억으로 자동 완화 적용)\"\"\"
    import datetime
    import pandas as pd
    import FinanceDataReader as fdr
    import time
    
    try:
        # 1. KRX 전체 종목 조회
        df_krx = fdr.StockListing('KRX')
        if df_krx is None or df_krx.empty:
            return False, "KRX 시장 정보를 실시간으로 가져올 수 없습니다."
            
        # 필요한 컬럼 정제 및 존재 확인
        if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
            df_krx['Code'] = df_krx['Symbol']
        
        # 등락률 컬럼명 확인 (대소문자 구분 없이 Ratio, Rate, Chg, 등락 등이 포함된 컬럼 매칭)
        chg_col = None
        for col in df_krx.columns:
            c_low = col.lower()
            if 'ratio' in c_low or 'rate' in c_low or 'chg' in c_low or '등락' in col:
                chg_col = col
                break
                
        # 거래대금 컬럼명 확인 (대소문자 구분 없이 Amount, Value, Amt, 대금 등이 포함된 컬럼 매칭)
        amt_col = None
        for col in df_krx.columns:
            c_low = col.lower()
            if 'amount' in c_low or 'value' in c_low or 'amt' in c_low or '대금' in col:
                amt_col = col
                break
        
        df = df_krx.copy()
        
        # 등락률 및 거래대금 변환
        if chg_col:
            df[chg_col] = pd.to_numeric(df[chg_col], errors='coerce').fillna(0.0)
        else:
            return False, "주가 등락률 데이터를 찾을 수 없습니다."
            
        if amt_col:
            df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce').fillna(0.0)
        else:
            return False, "거래대금 데이터를 찾을 수 없습니다."
            
        # 2. 거래대금 스케일 감지 및 정제 (FinanceDataReader에 따라 원 단위 또는 백만 원 단위일 수 있음)
        max_amt = df[amt_col].max()
        # 한국 시장 기준 500억 = 50,000,000,000 원. 
        # 500억 임계치 설정 (거래대금 최대치 기준으로 단위를 동적 감지)
        if max_amt > 1e9: # 원 단위
            limit_500b = 50000000000
            limit_300b = 30000000000
        elif max_amt > 1e6: # 천 원 단위
            limit_500b = 50000000
            limit_300b = 30000000
        else: # 백만 원 단위
            limit_500b = 50000
            limit_300b = 30000
            
        # 등락률도 퍼센트 단위(15.0)인지 소수점 단위(0.15)인지 감지
        max_chg = df[chg_col].max()
        chg_threshold = 15.0 if max_chg > 1.0 else 0.15
        
        # 3. 1차 필터링 (상승률 15% 이상 & 거래대금 500억 이상)
        df_leaders = df[(df[chg_col] >= chg_threshold) & (df[amt_col] >= limit_500b)]
        
        # 만약 500억 이상 종목이 없으면, 300억 이상으로 완화
        if df_leaders.empty:
            df_leaders = df[(df[chg_col] >= chg_threshold) & (df[amt_col] >= limit_300b)]
            
        if df_leaders.empty:
            return False, "오늘 조건(상승률 15% 이상, 거래대금 300억 이상)을 만족하는 주도주가 없습니다."
            
        # 4. 분석 진행 및 테마 추출
        shadow_data = load_shadowing_data()
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        added_stocks = []
        themes_detected = {} # theme_name -> stocks_list
        
        for _, row in df_leaders.iterrows():
            code = row['Code']
            name = row.get('Name', code)
            
            # StockScanner 분석을 통해 신호 및 테마 융합
            analysis = scanner.analyze_stock(code, 'KR')
            if analysis:
                signals = analysis.get('signals', '')
                score = analysis.get('score', 50)
                
                # 강한 세력 수급 신호가 포착된 종목들만 등록
                if score >= 60 or "세력" in signals or "수급" in signals or "골드" in signals or "밥그릇" in signals:
                    added_stocks.append(name)
                    theme_found = "실시간 급등주"
                    themes_detected.setdefault(theme_found, []).append(name)
        
        if not added_stocks:
            return False, "조건은 만족했으나 세력 신호 기준 점수를 넘는 핵심 주도주가 없습니다."
            
        # 5. 백과사전(dictionary) 테마 자동 등재 및 병합 갱신
        # 기존 모든 테마의 last_updated 날짜를 오늘 날짜로 일괄 동적 갱신
        for entry in shadow_data.get("dictionary", []):
            entry["last_updated"] = today_str
            
        for theme_name, stocks_list in themes_detected.items():
            if theme_name == "실시간 급등주":
                theme_name = f"당일 급등 수급주 ({today_str})"
                
            theme_exists = False
            for entry in shadow_data.get("dictionary", []):
                if entry.get("theme") == theme_name:
                    theme_exists = True
                    # 기존 종목에 추가 (중복 제거)
                    existing_stocks = [s.strip() for s in entry.get("stocks", "").split(",") if s.strip()]
                    for s in stocks_list:
                        if s not in existing_stocks:
                            existing_stocks.append(s)
                    entry["stocks"] = ", ".join(existing_stocks)
                    entry["last_updated"] = today_str
                    entry["reason"] = f"({today_str} 실시간 자동 갱신) " + entry.get("reason", "")
                    break
                    
            if not theme_exists:
                new_id = f"theme_auto_{int(time.time())}_{hash(theme_name)%1000}"
                new_theme_auto = {
                    "id": new_id,
                    "theme": theme_name,
                    "stocks": ", ".join(stocks_list),
                    "reason": f"({today_str} 실시간 자동 등재) 오늘 거래대금 급증 및 강한 세력 수급 신호가 발생한 당일 시장 주도주/테마군입니다.",
                    "last_updated": today_str
                }
                shadow_data["dictionary"].append(new_theme_auto)
                
        # 쉐도잉 일지(records) 추가 (당일 키워드 통합 기록)
        record_exists = False
        for rec in shadow_data.get("records", []):
            if rec.get("date") == today_str:
                record_exists = True
                existing_stocks = [s.strip() for s in rec.get("stocks", "").split(",") if s.strip()]
                for s in added_stocks:
                    if s not in existing_stocks:
                        existing_stocks.append(s)
                rec["stocks"] = ", ".join(existing_stocks)
                rec["reason"] = f"({today_str} 실시간 수급 합산) " + rec.get("reason", "")
                break
                
        if not record_exists:
            new_record = {
                "date": today_str,
                "keyword": "실시간수급주",
                "stocks": ", ".join(added_stocks),
                "reason": f"({today_str} 자동 기록) 한국 시장 당일 거래대금 및 등락률 최상위권의 강력한 주도 세력 유입 종목군"
            }
            shadow_data["records"].insert(0, new_record) # 최신글이 맨 위로
            
        # 6. 로컬 JSON 저장
        if save_shadowing_data(shadow_data):
            return True, f"✅ 실시간 한국 시장 주도주 {len(added_stocks)}개가 백과사전 및 쉐도잉 일지에 안전하게 반영되었습니다! (분석일자: {today_str})"
        else:
            return False, "동기화된 데이터를 로컬 파일에 저장하는 데 실패했습니다."
            
    except Exception as e:
        return False, f"실시간 데이터 반영 에러: {str(e)}"

def render_trading_price_guide(symbol, market_code):
    \"\"\"세력 평단을 활용해 종목 스캔 상세 뷰에 최적의 진입가, 익절가, 손절가 가이드를 실시간 렌더링합니다.\"\"\"
    whale = scanner.calculate_whale_analysis(symbol, market_code)
    if not whale:
        return ""
        
    b_lower, b_upper = whale['buy_zone']
    t1 = whale['target_price_1']
    t2 = whale['target_price_2']
    sl = whale['stop_loss']
    rr = whale['rr_ratio']
    curr = whale['current_price']
    
    price_suffix = "원" if market_code != 'US' else "달러"
    
    if rr >= 2.0:
        rr_badge = '<span style="background-color:#2ecc71; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">매우 유리</span>'
    elif rr >= 1.2:
        rr_badge = '<span style="background-color:#3498db; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">진입 보통</span>'
    else:
        rr_badge = '<span style="background-color:#e74c3c; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">손익비 불리</span>'
        
    ref_price = curr if curr > 0 else b_upper
    p_t1 = ((t1 - ref_price) / ref_price) * 100 if ref_price > 0 else 0
    p_t2 = ((t2 - ref_price) / ref_price) * 100 if ref_price > 0 else 0
    p_sl = ((sl - ref_price) / ref_price) * 100 if ref_price > 0 else 0
    
    html = f\"\"\"
    <div style="
        background: linear-gradient(135deg, rgba(30, 34, 42, 0.95) 0%, rgba(20, 24, 30, 0.98) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">
            <span style="font-size: 1.05em; font-weight: bold; color: #58a6ff;">🎯 실시간 추천 매매 시나리오 타점</span>
            <div>
                <span style="font-size: 0.8em; color: #8b949e; margin-right: 5px;">기대 손익비: <b>{rr:.2f}</b></span>
                {rr_badge}
            </div>
        </div>
        
        <table style="width:100%; border-collapse: collapse; font-size: 0.9em; color: #adbac7;">
            <thead>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left;">
                    <th style="padding: 8px 5px; color: #8b949e; font-weight: 500;">구분</th>
                    <th style="padding: 8px 5px; color: #8b949e; font-weight: 500; text-align: right;">가이드 가격</th>
                    <th style="padding: 8px 5px; color: #8b949e; font-weight: 500; text-align: right;">대비 기대치</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <td style="padding: 10px 5px; font-weight: bold; color: #2ecc71;">🟢 매수 권장 (Buy Zone)</td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #2ecc71;">
                        {b_lower:,.0f} ~ {b_upper:,.0f} {price_suffix}
                    </td>
                    <td style="padding: 10px 5px; text-align: right; color: #8b949e; font-size: 0.85em;">분할 매수 유효</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <td style="padding: 10px 5px; font-weight: bold; color: #f1c40f;">🎯 1차 목표가 (익절선)</td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #f1c40f;">
                        {t1:,.0f} {price_suffix}
                    </td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #f1c40f;">
                        +{p_t1:+.1f}%
                    </td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <td style="padding: 10px 5px; font-weight: bold; color: #e67e22;">🔥 2차 목표가 (최대치)</td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e67e22;">
                        {t2:,.0f} {price_suffix}
                    </td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e67e22;">
                        +{p_t2:+.1f}%
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 5px; font-weight: bold; color: #e74c3c;">🚨 최종 손절가 (Risk Cut)</td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e74c3c;">
                        {sl:,.0f} {price_suffix}
                    </td>
                    <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e74c3c;">
                        {p_sl:+.1f}%
                    </td>
                </tr>
            </tbody>
        </table>
        
        <div style="margin-top: 12px; background: rgba(255,255,255,0.02); border-radius: 6px; padding: 10px; border: 1px dashed rgba(255,255,255,0.05);">
            <p style="margin: 0; font-size: 0.78em; color: #8b949e; line-height: 1.4;">
                💡 <b>가이드 해석 방법:</b> 세력 가중평단(VWAP) 및 장기 저항선 기준 가격입니다. 
                현재가가 매수 권장가 범위 내에 있거나 돌파 직후 안착 시 <b>매수유효 / 적극매수</b> 구간으로 해석할 수 있으며, 
                최종 손절가(Risk Cut) 이탈 시에는 기계적으로 리스크를 관리하는 전략이 손익비 차원에서 매우 유리합니다.
            </p>
        </div>
    </div>
    \"\"\"
    return html

"""

# 1) PORTFOLIO_FILE 밑에 helper_code 주입
target_portfolio_file = 'PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")'
if target_portfolio_file in content:
    content = content.replace(target_portfolio_file, target_portfolio_file + "\n\n" + helper_code.strip())
    print("★ 헬퍼 함수들 및 SHADOWING_FILE 정의 삽입 성공!")
else:
    print("❌ ERROR: PORTFOLIO_FILE 정의부를 찾지 못했습니다!")

# 2) st.tabs 부분 치환 (tab_dict 추가)
# 569라인 부근 st.tabs 찾기
# stock_app.py:569:tab_scan, tab_portfolio = st.tabs(["?? \u001d\u000f\u001d\u000f\u001d\u0003\u001d\u000b", "?? \u001d\u000f\u001d\u000f\u001d\u000b\u001d\t\u001d\u0007"])
# 인코딩 깨짐을 방지하기 위해 'tab_scan, tab_portfolio = st.tabs' 라는 문자열이 있는 라인 전체를 찾아서 교체
lines = content.splitlines()
tabs_replaced = False
for idx, line in enumerate(lines):
    if "tab_scan, tab_portfolio = st.tabs" in line:
        lines[idx] = 'tab_scan, tab_portfolio, tab_dict = st.tabs(["🔍 종목 스캔", "⭐ 포트폴리오", "📚 주도테마백과사전"])'
        tabs_replaced = True
        print(f"★ st.tabs 라인 치환 성공! (라인 {idx+1})")
        break

if tabs_replaced:
    content = "\n".join(lines)
else:
    print("❌ ERROR: tab_scan, tab_portfolio = st.tabs 라인을 찾지 못했습니다!")

# 3) 전문가 의견 하단에 render_trading_price_guide 삽입 (3군데)

# 3-1. 직접 검색 상세 뷰 전문가 의견
target_opinion_direct = """                if s_data['action'] == 'BUY': st.success(f"**{s_data['action_desc']}**")
                else: st.info(f"**{s_data['action_desc']}**")"""

replacement_opinion_direct = """                if s_data['action'] == 'BUY': st.success(f"**{s_data['action_desc']}**")
                else: st.info(f"**{s_data['action_desc']}**")
                
                # [신규] 실시간 추천 거래 가이드라인 카드 연동
                st.markdown(render_trading_price_guide(s_data['symbol'], s_data['market_type']), unsafe_allow_html=True)"""

if target_opinion_direct in content:
    content = content.replace(target_opinion_direct, replacement_opinion_direct)
    print("★ 직접 검색 뷰 전문가 의견 가이드 연동 성공!")
else:
    print("❌ WARNING: 직접 검색 뷰 전문가 의견 위치를 찾지 못했습니다!")

# 3-2. 시장 스캔 테이블 선택 전문가 의견
target_opinion_scan = """                    st.markdown("##### 💡 전문가 의견")
                    if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                    else: st.info(f"**{selected_data['action_desc']}**")"""

replacement_opinion_scan = """                    st.markdown("##### 💡 전문가 의견")
                    if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                    else: st.info(f"**{selected_data['action_desc']}**")
                    
                    # [신규] 실시간 추천 거래 가이드라인 카드 연동
                    st.markdown(render_trading_price_guide(selected_symbol, current_market), unsafe_allow_html=True)"""

if target_opinion_scan in content:
    content = content.replace(target_opinion_scan, replacement_opinion_scan)
    print("★ 시장 스캔 테이블 선택 뷰 전문가 의견 가이드 연동 성공!")
else:
    print("❌ WARNING: 시장 스캔 테이블 선택 뷰 전문가 의견 위치를 찾지 못했습니다!")

# 3-3. 포트폴리오 탭 전문가 의견
target_opinion_portfolio = """                            st.markdown("##### 💡 전문가 의견")
                            if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                            else: st.info(f"**{selected_data['action_desc']}**")"""

replacement_opinion_portfolio = """                            st.markdown("##### 💡 전문가 의견")
                            if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                            else: st.info(f"**{selected_data['action_desc']}**")
                            
                            # [신규] 실시간 추천 거래 가이드라인 카드 연동
                            st.markdown(render_trading_price_guide(selected_symbol, m_key), unsafe_allow_html=True)"""

if target_opinion_portfolio in content:
    content = content.replace(target_opinion_portfolio, replacement_opinion_portfolio)
    print("★ 포트폴리오 탭 전문가 의견 가이드 연동 성공!")
else:
    print("❌ WARNING: 포트폴리오 탭 전문가 의견 위치를 찾지 못했습니다!")

# 4. tab_dict UI 코드 텍스트 준비
dict_tab_code = """
# --- [주도테마백과사전 & 주식 쉐도잉 탭] ---
with tab_dict:
    st.markdown("### 📚 주도주·테마 백과사전 & 주식 쉐도잉")
    st.caption("유튜브 영상(RhMRtXb_95E)에 수록된 '주식 쉐도잉' 및 '나만의 테마/종목 DB 훈련'을 보조하는 디지털 도구입니다.")
    
    # 1. 데이터 불러오기
    shadow_data = load_shadowing_data()
    
    # [신규] 실시간 시장 주도 테마 자동 반영 엔진 UI 배치
    st.markdown("##### ⚡ 실시간 주도 테마 자동 동기화 엔진")
    
    st.markdown(\"\"\"
    <div style="
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.08) 0%, rgba(16, 20, 28, 0.95) 100%) !important;
        border: 1px solid rgba(88, 166, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    ">
        <span style="font-size: 0.9em; font-weight: bold; color: #58a6ff !important;">📢 실시간 자동화 안내</span>
        <p style="margin: 6px 0 0 0; color: #adbac7 !important; font-size: 0.85em; line-height: 1.5;">
            <b>상승률 15% 이상 & 거래대금 500억 이상</b> 터진 한국 시장(KRX)의 당일 핵심 주도주들을 실시간으로 파싱하고 
            StockScanner 엔진으로 기술 점수와 전문가 매매 신호를 종합 분석하여 <b>백과사전 테마와 쉐도잉 일지에 자동으로 누적 병합</b>합니다. (기준 미달 시 300억으로 자동 완화 적용)
        </p>
    </div>
    \"\"\", unsafe_allow_html=True)
    
    col_sync = st.columns([3, 1])
    with col_sync[0]:
        st.caption("※ 장 마감 후 또는 장중에 실행하시면 오늘 실시간으로 터진 뜨거운 주도주가 즉시 캘린더와 차트에 축적됩니다.")
    with col_sync[1]:
        if st.button("🔄 실시간 데이터 자동 반영", type="primary", use_container_width=True):
            with st.spinner("실시간 한국 시장(KRX) 주도주 분석 및 백과사전 동기화 중..."):
                success, msg = sync_realtime_shadowing_data(scanner)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
    # 서브 탭 구성
    sub_dict_tab, sub_shadow_tab = st.tabs(["📖 테마 백과사전", "📝 주식 쉐도잉 일지"])
    
    # 2. 테마 백과사전 탭
    with sub_dict_tab:
        st.markdown("#### 📖 실시간 동기화 테마 리스트")
        st.write("주도주 조건이 만족되어 백과사전에 자동으로 등록 및 업데이트된 테마들입니다.")
        
        for entry in shadow_data.get("dictionary", []):
            st.markdown(f\"\"\"
            <div style="
                background-color: rgba(255,255,255,0.02) !important;
                border: 1px solid rgba(255,255,255,0.05) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                margin-bottom: 12px !important;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:bold; font-size:1.05em; color:#f1c40f;">🏷️ {entry.get('theme')}</span>
                    <span style="font-size:0.78em; color:#8b949e;">최종 업데이트: {entry.get('last_updated')}</span>
                </div>
                <p style="margin:5px 0; font-size:0.88em; color:#adbac7;">📈 <b>주도 종목:</b> <span style="color:#58a6ff; font-weight:bold;">{entry.get('stocks')}</span></p>
                <p style="margin:5px 0 0 0; font-size:0.82em; color:#8b949e; line-height:1.4;">💡 <b>상세 원인:</b> {entry.get('reason')}</p>
            </div>
            \"\"\", unsafe_allow_html=True)
            
    # 3. 주식 쉐도잉 일지 탭
    with sub_shadow_tab:
        st.markdown("#### 📝 당일 핵심 주도 테마 쉐도잉 일지")
        st.write("매일 퇴근 후 장 마감 데이터 중 가장 강했던 주도 섹터와 종목의 유입 이유를 기록하고 훈련하는 일지입니다.")
        
        # 쉐도잉 일지 신규 작성 Form
        with st.expander("✍️ 오늘자 주도주 쉐도잉 일지 수동 작성", expanded=False):
            with st.form("shadow_form", clear_on_submit=True):
                s_date = st.date_input("날짜").strftime('%Y-%m-%d')
                s_keyword = st.text_input("핵심 키워드 (예: 반도체, 초전도체)", placeholder="핵심 테마나 재료 입력")
                s_stocks = st.text_input("주도 종목 (예: 한미반도체, 제주반도체)", placeholder="콤마(,)로 구분하여 입력")
                s_reason = st.text_area("주도 이유 및 장중 흐름", placeholder="상승 이유, 뉴스, 특징 거래대금 흐름 등 기록")
                
                if st.form_submit_button("💾 일지 기록 저장"):
                    if s_keyword and s_stocks:
                        shadow_data["records"].insert(0, {
                            "date": s_date,
                            "keyword": s_keyword,
                            "stocks": s_stocks,
                            "reason": s_reason
                        })
                        if save_shadowing_data(shadow_data):
                            st.success("오늘의 쉐도잉 일지가 성공적으로 기록되었습니다!")
                            st.rerun()
                    else:
                        st.warning("키워드와 주도 종목는 필수 입력 항목입니다.")
                        
        # 기록된 일지 출력
        for record in shadow_data.get("records", []):
            st.markdown(f\"\"\"
            <div style="
                background-color: rgba(30, 34, 42, 0.4) !important;
                border-left: 4px solid #58a6ff !important;
                border: 1px solid rgba(255,255,255,0.05) !important;
                border-radius: 0 8px 8px 0 !important;
                padding: 15px !important;
                margin-bottom: 15px !important;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:bold; font-size:1em; color:#58a6ff;">📅 {record.get('date')} | 핵심 키워드: {record.get('keyword')}</span>
                </div>
                <p style="margin:5px 0; font-size:0.88em; color:#adbac7;">🔥 <b>주요 급등주:</b> {record.get('stocks')}</p>
                <p style="margin:5px 0 0 0; font-size:0.82em; color:#8b949e; line-height:1.4;">📝 <b>상세 흐름 & 뉴스:</b> {record.get('reason')}</p>
            </div>
            \"\"\", unsafe_allow_html=True)
"""

# Footer 바로 직전에 tab_dict 추가
target_footer = """# Footer
st.divider()"""

if target_footer in content:
    content = content.replace(target_footer, dict_tab_code.strip() + "\n\n" + target_footer)
    print("★ tab_dict UI 영역 삽입 성공!")
else:
    print("❌ ERROR: Footer 영역을 찾지 못했습니다!")

# 5. 파일 쓰기
with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
print("★ stock_app.py 패치 완료 및 파일 저장 성공!")
