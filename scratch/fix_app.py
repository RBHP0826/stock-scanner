# -*- coding: utf-8 -*-
import os

def main():
    file_path = r"C:\Users\zxc02\OneDrive\Desktop\새 폴더\stock_app.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print(f"Total lines: {len(lines)}")
    
    # 2101번째 줄부터 2136번째 줄까지 (0-based 인덱스로는 2100~2135)
    # 안전 점검: 시작과 끝 텍스트 확인
    start_idx = 2100
    end_idx = 2136 # 2136번째 줄까지 포함 (0-based로 2135까지가 index)
    
    target_start = "if not day_themes and not day_records:"
    target_end = '""", unsafe_allow_html=True)'
    
    actual_start = lines[start_idx].strip()
    actual_end = lines[end_idx-1].strip()
    
    print(f"Target Start (Line {start_idx+1}): {actual_start}")
    print(f"Target End (Line {end_idx}): {actual_end}")
    
    if target_start not in actual_start or target_end not in actual_end:
        print("Error: Target text mismatch! Finding by text...")
        # 텍스트로 직접 찾기
        found_start = -1
        for idx, line in enumerate(lines):
            if "if not day_themes and not day_records:" in line and idx > 1800:
                found_start = idx
                break
        
        if found_start == -1:
            print("Error: Could not find target start text")
            return
            
        found_end = -1
        for idx in range(found_start, len(lines)):
            if '""", unsafe_allow_html=True)' in lines[idx]:
                # 두번째 card의 end를 찾기 위해 double check
                # det_col2 안의 쉐도잉 일지 카드 렌더링 끝부분
                if idx > found_start + 10:
                    found_end = idx + 1
                    break
                    
        if found_end == -1:
            print("Error: Could not find target end text")
            return
            
        start_idx = found_start
        end_idx = found_end
        print(f"Found by text search: Line {start_idx+1} to {end_idx}")
        
    # 새로운 코드 정의 (들여쓰기 12칸 반영)
    new_code = """            if not day_themes and not day_records:
                st.info(f"📅 {sel_date}에 자동으로 등록되거나 기록된 상세 데이터가 없습니다.")
            else:
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    st.markdown("##### 📖 당일 동기화 테마 백과사전")
                    if not day_themes:
                        st.write("⚪ 해당일 등록된 테마가 없습니다.")
                    for entry in day_themes:
                        rate_info = f"<span style='color: #ff7b72; font-weight: bold;'>▲ {entry.get('average_rate', 0)}%</span>" if entry.get('average_rate') else ""
                        amt_info = f"<span style='color: #58a6ff; font-weight: bold;'> | {entry.get('cumulative_amount', 0)}억</span>" if entry.get('cumulative_amount') else ""
                        
                        st.markdown(f\"\"\"
                        <div class="detail-card theme-card" style="margin-bottom: 12px; padding: 12px; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; background-color: rgba(255,255,255,0.02);">
                            <div class="detail-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; margin-bottom: 6px;">
                                <span class="detail-title" style="color:#ffffff !important; font-weight: bold; font-size: 1.05em;">🏷️ {entry.get('theme')}</span>
                                <span style="font-size: 0.85em;">{rate_info}{amt_info}</span>
                            </div>
                            <div class="detail-body">
                                <p style="color:#e2e8f0 !important; margin: 4px 0;"><strong>📈 주도 종목:</strong> <span class="highlight" style="color:#58a6ff !important; font-weight: bold;">{entry.get('stocks')}</span></p>
                                <p style="color:#adbac7 !important; margin: 4px 0; font-size: 0.9em; line-height: 1.4;"><strong>💡 상세 원인:</strong> {entry.get('reason')}</p>
                            </div>
                        </div>
                        \"\"\", unsafe_allow_html=True)
                with det_col2:
                    st.markdown("##### 📝 당일 핵심 쉐도잉 일지")
                    if not day_records:
                        st.write("⚪ 해당일 작성된 쉐도잉 일지가 없습니다.")
                    else:
                        rec = day_records[0]
                        details = rec.get("details", [])
                        
                        if details:
                            st.write("**🔥 주요 급등주 시세 및 상승이유**")
                            
                            sub_rows = []
                            for idx, d in enumerate(details):
                                rate_val = d.get('rate', 0.0)
                                rate_str = f"+{rate_val}%" if rate_val > 0 else f"{rate_val}%"
                                sub_rows.append(f\"\"\"
                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <td style="color: #ffffff; font-weight: bold; padding: 4px 2px;">{d.get('name')}</td>
                                    <td style="color: #8b949e; font-size: 0.85em; padding: 4px 2px;">{d.get('industry', '')}</td>
                                    <td style="color: #ff7b72; font-weight: bold; text-align: right; padding: 4px 2px;">{rate_str}</td>
                                    <td style="color: #58a6ff; text-align: right; padding: 4px 2px;">{int(d.get('amount', 0))}억</td>
                                    <td style="color: #adbac7; font-size: 0.88em; padding: 4px 2px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{d.get('reason', '')}">{d.get('reason', '')}</td>
                                </tr>
                                \"\"\".replace("\\n", ""))
                                
                            table_html = f\"\"\"
                            <table style="width: 100%; border-collapse: collapse; font-size: 11px; line-height: 1.3;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; color: #8b949e;">
                                        <th style="padding-bottom: 4px;">종목</th>
                                        <th style="padding-bottom: 4px;">업종</th>
                                        <th style="padding-bottom: 4px; text-align: right;">등락률</th>
                                        <th style="padding-bottom: 4px; text-align: right;">거래대금</th>
                                        <th style="padding-bottom: 4px; padding-left: 6px;">상승이유</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {"".join(sub_rows)}
                                </tbody>
                            </table>
                            \"\"\"
                            st.markdown(table_html.replace("\\n", " "), unsafe_allow_html=True)
                            st.caption("※ 표를 마우스로 올리시면 말줄임 처리된 전체 상승이유를 볼 수 있습니다.")
                            
                            st.write("")
                            st.markdown(f"**💡 장중 흐름 요약:**\\n{rec.get('reason')}")
                        else:
                            for record in day_records:
                                st.markdown(f\"\"\"
                                <div class="detail-card shadow-card" style="margin-bottom: 12px; padding: 12px; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; background-color: rgba(255,255,255,0.02);">
                                    <div class="detail-header" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; margin-bottom: 6px;">
                                        <span class="detail-title" style="color:#ffffff !important; font-weight: bold; font-size: 1.05em;">📅 키워드: {record.get('keyword')}</span>
                                    </div>
                                    <div class="detail-body">
                                        <p style="color:#e2e8f0 !important; margin: 4px 0;"><strong>🔥 주요 급등주:</strong> <span class="highlight" style="color:#58a6ff !important; font-weight: bold;">{record.get('stocks')}</span></p>
                                        <p style="color:#adbac7 !important; margin: 4px 0; font-size: 0.9em; line-height: 1.4;"><strong>📝 상세 흐름 & 뉴스:</strong> {record.get('reason')}</p>
                                    </div>
                                </div>
                                \"\"\", unsafe_allow_html=True)
"""
    
    # 조립
    new_lines = lines[:start_idx] + [new_code] + lines[end_idx:]
    
    # 쓰기
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print("Success: stock_app.py has been patched successfully!")

if __name__ == "__main__":
    main()
