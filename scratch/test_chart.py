import sys
import os
import pandas as pd
import numpy as np

# Insert current working directory
sys.path.insert(0, os.getcwd())

from stock_scanner import StockScanner
scanner = StockScanner()

symbol = '005930'
market = 'KR'

# 데이터 가져오기 (최근 120일)
df = scanner.get_historical_data(symbol, market, days=120)
if df is None or df.empty:
    print("Error: DataFrame is empty")
    sys.exit(1)

# 기술 지표 계산 (이동평균선)
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()
df['MA120'] = df['Close'].rolling(window=120).mean()

# RSI 계산
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# Plotly 차트 생성
import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, subplot_titles=(f'📈 {symbol} 캔들스틱', '📊 RSI 지표'),
                    row_heights=[0.7, 0.3])

# 1. 캔들스틱 추가
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)

# 2. 이동평균선 및 Future On 지표 추가
fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='rgba(255,255,255,0.4)', width=1), name='MA20'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='rgba(255,165,0,0.4)', width=1), name='MA60'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='rgba(255,0,0,0.4)', width=1), name='MA120'), row=1, col=1)

# 🏆 퓨처온 핵심 지표
if 'GoldLine' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df['GoldLine'], line=dict(color='#f1c40f', width=2), name='🏆 골드라인 (EMA 33)'), row=1, col=1)

if 'WhaleLine' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df['WhaleLine'], line=dict(color='#9b59b6', width=2, dash='dash'), name='🐳 세력선 (EMA 448)'), row=1, col=1)

# 볼린저 밴드 (NS밴드)
if 'BB_High' in df.columns and 'BB_Low' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(173, 216, 230, 0.1)'), showlegend=False, name='BB High'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(173, 216, 230, 0.1)'), fill='tonexty', showlegend=False, name='BB Low'), row=1, col=1)

# 4. RSI 추가
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=1.5), name='RSI'), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.update_layout(height=700, template="plotly_dark", showlegend=True, 
                  xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=40, b=10),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

fig.write_html("scratch/chart.html")
print("Chart generated successfully at scratch/chart.html!")
print("Y-axis properties:")
print("yaxis domain:", fig.layout.yaxis.domain)
print("yaxis2 domain:", fig.layout.yaxis2.domain)
