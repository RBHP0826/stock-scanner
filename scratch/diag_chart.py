import sys
import os
import numpy as np

# Mock json dump to avoid serializing mock objects
import json
json.dump = lambda *args, **kwargs: None
json.dumps = lambda *args, **kwargs: "{}"

# Create mock modules
from unittest.mock import MagicMock

mock_st = MagicMock()
mock_st.session_state = {
    'selected_market': '한국 (KRX)',
    'market_choice': '한국 (KRX)',
    'realtime_sync': False,
    'scan_results': None,
    'portfolio': {'KR': [], 'US': [], 'COIN': []}
}

class MockSessionState(dict):
    def __getattr__(self, name):
        return self.get(name)
    def __setattr__(self, name, value):
        self[name] = value

session_state_obj = MockSessionState(mock_st.session_state)
mock_st.session_state = session_state_obj

# Mock decorators
def dummy_decorator(*args, **kwargs):
    return lambda f: f

mock_st.cache_resource = dummy_decorator
mock_st.cache_data = dummy_decorator

# Mock UI calls with ascii cleaning
clean_print = lambda label, msg: print(label, str(msg).encode('ascii', errors='ignore').decode('ascii'))
mock_st.error = lambda msg: clean_print("ERROR:", msg)
mock_st.warning = lambda msg: clean_print("WARNING:", msg)
mock_st.info = lambda msg: clean_print("INFO:", msg)
mock_st.success = lambda msg: clean_print("SUCCESS:", msg)

# Mock columns to return false for button clicks to avoid running actions on import
def make_mock_column():
    col = MagicMock()
    col.button = lambda *args, **kwargs: False
    return col

mock_st.columns = lambda spec: [make_mock_column() for _ in range(spec if isinstance(spec, int) else len(spec))]
mock_st.tabs = lambda tab_list: [MagicMock() for _ in range(len(tab_list))]

# Mock widgets to return standard values instead of MagicMock
mock_st.text_input = lambda *args, **kwargs: ""
mock_st.selectbox = lambda *args, **kwargs: ""
mock_st.multiselect = lambda *args, **kwargs: []
mock_st.checkbox = lambda *args, **kwargs: False
mock_st.button = lambda *args, **kwargs: False
mock_st.number_input = lambda *args, **kwargs: 0
mock_st.radio = lambda *args, **kwargs: ""

def mock_plotly_chart(fig, use_container_width=True, theme=None):
    print("--- TRACES ---")
    for i, t in enumerate(fig.data):
        name_clean = str(t.name).encode('ascii', errors='ignore').decode('ascii')
        if t.type == 'candlestick':
            print(f"Trace {i}: name={name_clean}, type={t.type}, close_min={min(t.close)}, close_max={max(t.close)}")
        else:
            y_val = t.y
            if y_val is not None:
                # Filter out NaNs for min/max
                import numpy as np
                y_clean = [y for y in y_val if y is not None and not (isinstance(y, float) and np.isnan(y))]
                y_min = min(y_clean) if y_clean else 'All NaN'
                y_max = max(y_clean) if y_clean else 'All NaN'
            else:
                y_min = 'None'
                y_max = 'None'
            print(f"Trace {i}: name={name_clean}, type={t.type}, y_min={y_min}, y_max={y_max}")
    print("--- Y-AXES ---")
    print("yaxis:", fig.layout.yaxis)
    print("yaxis2:", fig.layout.yaxis2)
    print("---")

mock_st.plotly_chart = mock_plotly_chart

# Inject mocks
sys.modules['streamlit'] = mock_st
sys.modules['streamlit.runtime'] = MagicMock()

# Add workspace directory to path
sys.path.insert(0, os.getcwd())

from stock_app import display_detailed_chart
display_detailed_chart('005930', 'KR')
