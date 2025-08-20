from seleniumbase import Driver
from seleniumbase import SB

# with SB(browser=r"C:\Program Files\Google\Chrome\Application\chrome.exe", uc=True, proxy="127.0.0.1:5082") as sb:
#     url = "https://www.cloudflare.com/login"
#     sb.uc_open_with_reconnect(url, 5.5)
#     sb.uc_gui_handle_captcha()  # PyAutoGUI press Tab and Spacebar
#     sb.sleep(2.5)

manager = SB(browser="chrome",
             binary_location=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             uc=True,
             proxy="127.0.0.1:5082")

sb = manager.__enter__()  # 这一步等价于 with ... as sb:
# 2. 正常写脚本
url = "https://nhentai.net"
sb.uc_open_with_reconnect(url, 5.5)
sb.uc_gui_handle_captcha()
sb.sleep(2.5)
# 3. 手动退出上下文（一定要做，否则浏览器不会关闭）
manager.__exit__(None, None, None)
