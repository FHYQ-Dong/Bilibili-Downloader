import os, sys
import requests
import json
import loguru
import qrcode
import time
from blconfig import BLConfig
    

class BLAuth(requests.Session, BLConfig):
    def __init__(self, data_path=None):
        super().__init__()
        self.headers.update(self.ADDI_HEADERS)
        self.data_path = data_path if data_path else r'data'
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(f'{self.data_path}/log', exist_ok=True)
        os.makedirs(f'{self.data_path}/cookie', exist_ok=True)
        self.logger = loguru.logger
        self.logger.remove()
        self.logger.add(
            sys.stderr,
            format='<level>[{level}] {message}</level>',
            colorize=True,
            level='INFO'
        )
        self.logger.add(f'{self.data_path}/log/log.log', rotation=f'5 MB', encoding='utf-8')
        
    def login(self, timeout=60):
        self._load_cookie()
        if self._check_login():
            self.logger.info('Already logged in.')
            return True
        
        qrcode_key, qrcode_url = self._get_qr_code()
        if not qrcode_key or not qrcode_url:
            self.logger.error('Failed to get QR code.')
            return False
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qrcode_url)
        qr.make(fit=True)
        qr.print_ascii()
        
        for i in range(timeout // 3):
            time.sleep(3)
            if self._refrese_cookie(qrcode_key):
                self.logger.info('Login successful.')
                return True
            else:
                self.logger.info(f'Waiting for login... {i + 1}/{timeout // 3}')
        self.logger.error('Login timed out.')
        return False
        
    def _export_cookie(self):
        with open(f'{self.data_path}/cookie/cookie.json', 'w', encoding='utf-8') as f:
            json.dump(self.cookies.get_dict(), f, ensure_ascii=False, indent=4)
            
    def _load_cookie(self):
        if os.path.exists(f'{self.data_path}/cookie/cookie.json'):
            with open(f'{self.data_path}/cookie/cookie.json', 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                for k, v in cookies.items():
                    self.cookies.set(k, v)
    
    def _check_login(self):
        try:
            resp = self.get(self.CHECK_AUTH_URL)
            data = resp.json()
            return data['code'] == 0
        except Exception as e:
            self.logger.error(f'Error checking login status: {e}')
            return False
        
    def _get_qr_code(self):
        try:
            resp = self.get(self.LOGIN_QR_URL)
            data = resp.json()
            qrcode_key = data['data']['qrcode_key']
            qrcode_url = data['data']['url']
            return qrcode_key, qrcode_url
        except Exception as e:
            self.logger.error(f'Error getting QR code: {e}')
            return None, None
        
    def _refrese_cookie(self, qrcode_key):
        try:
            resp = self.get(self.SET_COOKIE_URL.format(qrcode_key))
            data = resp.json()
            if data['data']['code'] == 0:
                self._export_cookie()
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f'Error setting cookie: {e}')
            return False


if __name__ == '__main__':
    auth = BLAuth()
    if auth.login(timeout=60):
        print('Login successful.')
    else:
        print('Login failed.')