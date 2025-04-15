class BLConfig:
    CHECK_AUTH_URL = 'https://api.bilibili.com/x/web-interface/nav'
    LOGIN_QR_URL = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-fe-header'
    SET_COOKIE_URL = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={}&source=main-fe-header'
    
    CID_URL = 'https://api.bilibili.com/x/player/pagelist?bvid={}'
    VIDEO_URL = 'https://www.bilibili.com/video/{}?p={}'
    ADDI_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        # 'Referer': 'https://www.baidu.com'
    }