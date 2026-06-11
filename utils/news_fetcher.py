import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import html
import sys
import os

# 현재 디렉토리 기준 utils 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

def fetch_latest_news_reason(stock_name):
    """
    구글 뉴스 RSS를 검색하여 특정 종목의 가장 최신 '특징주' 기사 헤드라인을 가져옵니다.
    """
    # '특징주' 키워드를 포함하여 검색
    query = f"{stock_name} 특징주 OR 급등"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        if items:
            for item in items[:3]: # 상위 3개 검색
                title = item.find('title').text
                if title:
                    title = html.unescape(title)
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    # 구글 뉴스의 경우 종목명이 포함된 기사를 선호
                    if stock_name in title:
                        return f"[뉴스] {title}"
            
            # 종목명이 명시되지 않았더라도 첫번째 기사 반환
            first_title = html.unescape(items[0].find('title').text)
            if " - " in first_title:
                first_title = first_title.rsplit(" - ", 1)[0]
            return f"[뉴스] {first_title}"
            
    except Exception as e:
        logger.warning(f"Failed to fetch news for {stock_name}: {e}")
        
    return "당일 시세 및 거래대금 급등 (뉴스 미확인)"

if __name__ == "__main__":
    print(fetch_latest_news_reason("삼성전자"))
