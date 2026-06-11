import logging
import os

def setup_logger():
    logger = logging.getLogger("StockDashboard")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # 파일 핸들러 (error.log)
        fh = logging.FileHandler("error.log", encoding='utf-8')
        fh.setLevel(logging.ERROR)
        
        # 콘솔 핸들러
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger()
