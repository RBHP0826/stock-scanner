import os
import sys
import subprocess
import time
import webbrowser
import threading
import socket
import json
import urllib.request
import urllib.parse

def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf8')
    except:
        return "알수없음"

def send_telegram_msg(msg):
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            token = config.get("telegram_token")
            chat_id = config.get("telegram_chat_id")
            if token and chat_id:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}).encode('utf-8')
                req = urllib.request.Request(url, data=data)
                urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def start_localtunnel():
    print("🌍 3. 전세계 어디서든 접속 가능한 외부망(Tunnel)을 뚫는 중입니다...")
    try:
        # localtunnel 대신 번거로운 확인 창이 없는 localhost.run을 사용합니다.
        # Windows 10/11에 기본 내장된 ssh 클라이언트를 사용하여 터널링합니다.
        process = subprocess.Popen(
            "ssh -o StrictHostKeyChecking=no -R 80:localhost:8501 nokey@localhost.run",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        for line in iter(process.stdout.readline, ''):
            if "https://" in line and ".lhr.life" in line:
                lt_url = "https://" + line.split("https://")[1].strip()
                msg = f"🌐 **[대시보드 원클릭 자동 접속 완료]**\n\n"
                msg += f"기존처럼 복잡한 입력 없이, 이 링크를 누르면 바로 대시보드가 열립니다:\n"
                msg += f"👉 🔗 접속 주소: {lt_url}\n"
                print(f"\n========================================================")
                print(f"✅ 외부 접속 주소 발급 완료: {lt_url}")
                print(f"========================================================\n")
                send_telegram_msg(msg)
                break
    except Exception as e:
        print(f"❌ 외부망 연결 실패: {e}")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def open_browser():
    """Streamlit 서버가 뜰 때까지 잠시 대기 후 브라우저를 엽니다."""
    time.sleep(5)
    print("🌐 [주식 종목 선정] 브라우저 접속을 시도합니다: http://localhost:8501")
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    print("\n========================================================")
    print("      🚀 주식 종목 선정 대시보드 원클릭 실행기")
    print("========================================================\n")
    
    # 작업 디렉토리를 현재 파일 위치로 변경
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    print(f"⏳ 1. 경로 확인 완료: {current_dir}")

    # 브라우저 자동 오픈 스레드 시작
    threading.Thread(target=open_browser, daemon=True).start()

    # Streamlit 실행 (현재 파이썬 인터프리터 사용)
    print("⚙️ 2. 대시보드 서버를 구동합니다...")
    
    local_ip = get_local_ip()
    print("\n========================================================")
    print("📱 [모바일 접속 안내]")
    print(f"   PC와 같은 Wi-Fi를 쓰는 폰에서 접속 주소: http://{local_ip}:8501")
    print("   또는 대시보드 왼쪽 사이드바 맨 밑의 'QR 코드'를 스캔하세요!")
    print("========================================================\n")
    
    # 외부 터널링 스레드 시작
    threading.Thread(target=start_localtunnel, daemon=True).start()
    
    try:
        # 포트를 8501로 고정하고, 외부망(터널) 접속 시 화면이 안 뜨거나 무한 로딩되는 현상을 방지하기 위해 CORS와 XSRF 제한을 끕니다.
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "stock_app.py", 
            "--server.headless=true", 
            "--server.port=8501",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false"
        ], check=True)
    except Exception as e:
        print(f"\n❌ 실행 중 오류가 발생했습니다: {e}")
        input("창을 닫으려면 엔터를 누르세요...")
