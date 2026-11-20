"""
夸克网盘登录模块
支持多种登录方式：API登录、简化登录、Playwright登录
"""

import json
import time
from typing import Dict, List, Optional

from ..config import get_config_dir
from ..exceptions import AuthenticationError, ConfigError
from ..utils.logger import get_logger
from .browser_cookies import (
    get_browser_cookies,
    is_usable_for_download,
    to_cookie_records,
)

# 夸克网盘 API 层面的必要 cookie
REQUIRED_COOKIES = ('__pus', '__kps', '__uid')


class QuarkAuth:
    """夸克网盘认证管理器"""

    def __init__(self, timeout: int = 300):
        """
        初始化认证管理器

        Args:
            timeout: 登录超时时间(秒)，默认5分钟
        """
        self.timeout = timeout
        self.config_dir = get_config_dir()
        self.cookies_file = self.config_dir / "cookies.json"
        self.logger = get_logger(__name__)

        # 最近一次凭证来源: 'browser' | 'saved' | 'login'
        self.cookie_source: Optional[str] = None

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _save_cookies(self, cookies: List[Dict]) -> None:
        """保存cookies到本地文件"""
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cookies': cookies,
                    'timestamp': int(time.time()),
                    'expires_at': self._get_cookies_expire_time(cookies)
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ConfigError(f"保存cookies失败: {e}")

    def _load_cookies(self) -> Optional[Dict]:
        """从本地文件加载cookies"""
        try:
            if not self.cookies_file.exists():
                return None

            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查cookies是否过期
            if self._is_cookies_expired(data):
                return None

            return data
        except Exception:
            return None

    def _get_cookies_expire_time(self, cookies: List[Dict]) -> Optional[int]:
        """获取cookies的过期时间"""
        min_expire = None
        for cookie in cookies:
            # 检查所有cookie，不只是quark域名的
            if 'expires' in cookie and cookie['expires'] > 0:
                expire_time = cookie['expires']
                if min_expire is None or expire_time < min_expire:
                    min_expire = expire_time

        # 如果没有找到有效的过期时间，返回一个合理的默认值（7天后）
        if min_expire is None:
            import time
            min_expire = int(time.time()) + (7 * 24 * 3600)

        return min_expire

    def _is_cookies_expired(self, cookie_data: Dict) -> bool:
        """检查cookies是否过期"""
        import time
        current_time = int(time.time())

        # 如果过期时间无效（None、-1等），使用时间戳检查
        expires_at = cookie_data.get('expires_at')
        if expires_at is None or expires_at <= 0:
            # 如果没有过期时间信息，检查是否超过7天
            timestamp = cookie_data.get('timestamp', 0)
            age_seconds = current_time - timestamp
            return age_seconds > (7 * 24 * 3600)

        return current_time > expires_at

    def _cookies_to_dict(self, cookies: List[Dict]) -> Dict[str, str]:
        """将cookies列表转换为字典格式"""
        result = {}
        for cookie in cookies:
            # 包含所有cookie，不只是quark域名的
            result[cookie['name']] = cookie['value']
        return result

    def _cookies_to_string(self, cookies: List[Dict]) -> str:
        """将cookies列表转换为字符串格式"""
        cookie_dict = self._cookies_to_dict(cookies)
        return '; '.join([f"{key}={value}" for key, value in cookie_dict.items()])

    def login(self, force_relogin: bool = False, use_qr: bool = True, method: str = "auto") -> str:
        """
        执行多层级登录流程

        Args:
            force_relogin: 是否强制重新登录
            use_qr: 是否使用二维码登录（兼容性参数）
            method: 登录方式 ("auto", "api", "simple")

        Returns:
            Cookie字符串

        Raises:
            AuthenticationError: 登录失败
        """
        # 如果不是强制重新登录，优先用浏览器里的登录态，其次才是已保存的
        if not force_relogin:
            browser_cookies = self._load_browser_cookies()
            if browser_cookies:
                return browser_cookies

            saved_cookies = self._load_cookies()
            if saved_cookies:
                self.cookie_source = 'saved'
                self.logger.info("使用已保存的登录凭证")
                return self._cookies_to_string(saved_cookies['cookies'])

        self._warn_fallback()
        self.cookie_source = 'login'

        # 根据指定方法进行登录
        if method == "auto":
            return self._auto_login()
        elif method == "api":
            return self._api_login()
        elif method == "simple":
            return self._simple_login()
        else:
            raise AuthenticationError(f"不支持的登录方式: {method}")

    def _auto_login(self) -> str:
        """
        自动选择最佳登录方式
        优先级: API登录 → 简化登录 → Playwright登录
        """
        self.logger.debug("开始自动登录流程")

        # 1. 尝试API登录
        try:
            self.logger.debug("尝试API登录...")
            return self._api_login()
        except Exception as e:
            self.logger.debug(f"API登录失败: {e}")

        # 2. 尝试简化登录
        try:
            self.logger.debug("尝试简化登录...")
            return self._simple_login()
        except Exception as e:
            self.logger.debug(f"简化登录失败: {e}")

        # 如果所有方式都失败了
        raise AuthenticationError("所有登录方式都失败了")

    def _api_login(self) -> str:
        """API登录方式"""
        try:
            from .api_login import APILogin

            api_login = APILogin(timeout=self.timeout)
            cookies = api_login.login()

            if cookies:
                # 解析cookies字符串为列表格式
                cookie_list = self._parse_cookie_string(cookies)

                # 保存cookies
                self._save_cookies(cookie_list)
                self.logger.debug("API登录成功")
                return cookies
            else:
                raise AuthenticationError("API登录返回空Cookie")

        except ImportError:
            raise AuthenticationError("API登录模块不可用")
        except Exception as e:
            raise AuthenticationError(f"API登录失败: {e}")

    def _simple_login(self) -> str:
        """简化登录方式"""
        try:
            from .simple_login import SimpleLogin

            simple_login = SimpleLogin()
            cookies = simple_login.login()

            if cookies:
                # 解析cookies字符串为列表格式
                cookie_list = self._parse_cookie_string(cookies)

                # 保存cookies
                self._save_cookies(cookie_list)
                self.logger.debug("简化登录成功")
                return cookies
            else:
                raise AuthenticationError("简化登录返回空Cookie")

        except ImportError:
            raise AuthenticationError("简化登录模块不可用")
        except Exception as e:
            raise AuthenticationError(f"简化登录失败: {e}")

    def _parse_cookie_string(self, cookie_string: str) -> List[Dict]:
        """将cookie字符串解析为列表格式"""
        cookies = []
        for pair in cookie_string.split('; '):
            if '=' in pair:
                name, value = pair.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.quark.cn',
                    'path': '/'
                })
        return cookies

    def _validate_cookies(self, cookies: List[Dict]) -> bool:
        """验证cookies是否有效"""
        # 检查是否包含夸克相关的cookies
        quark_cookies = [c for c in cookies if 'quark' in c.get('domain', '')]
        return len(quark_cookies) > 0

    def _load_browser_cookies(self) -> Optional[str]:
        """
        从本机浏览器（当前仅 Firefox）读取已登录的夸克 cookie

        夸克 CDN 直链需要浏览器专属的 __puus，API 登录拿不到，所以浏览器
        cookie 是默认来源。

        Returns:
            Cookie 字符串；浏览器未登录或读不到时返回 None
        """
        try:
            cookies = get_browser_cookies()
        except Exception as e:
            self.logger.debug(f"读取浏览器 Cookie 失败: {e}")
            return None

        if not cookies:
            return None

        # 必须能在 API 层面用，才认为这份 cookie 有效
        if not all(cookies.get(name) for name in REQUIRED_COOKIES):
            self.logger.debug("浏览器 Cookie 缺少 API 必要字段，忽略")
            return None

        if not is_usable_for_download(cookies):
            self.logger.warning(
                "浏览器 Cookie 缺少浏览器会话字段（__puus），"
                "下载大文件可能失败"
            )

        # 写入本地，供 is_logged_in / 离线场景使用
        try:
            self._save_cookies(to_cookie_records(cookies))
        except Exception as e:
            self.logger.debug(f"保存浏览器 Cookie 失败: {e}")

        self.cookie_source = 'browser'
        self.logger.debug("使用浏览器中的夸克 Cookie")
        return '; '.join(f"{name}={value}" for name, value in cookies.items())

    def _warn_fallback(self) -> None:
        """浏览器 cookie 不可用时提示回退后果"""
        self.logger.warning(
            "未从浏览器读取到夸克 Cookie（Firefox 未登录或未安装），"
            "将改用二维码登录；缺少浏览器会话 Cookie，大文件下载可能失败"
        )

    def get_cookies(self, force_relogin: bool = False) -> str:
        """
        获取有效的cookies字符串

        优先级：浏览器 Cookie（默认） → 本地已保存 → 二维码登录

        Args:
            force_relogin: 是否强制重新登录

        Returns:
            Cookie字符串
        """
        if not force_relogin:
            # 默认从浏览器取，能同时满足 API 与 CDN 下载
            browser_cookies = self._load_browser_cookies()
            if browser_cookies:
                return browser_cookies

            saved_cookies = self._load_cookies()
            if saved_cookies:
                cookies = saved_cookies['cookies']
                cookie_string = self._cookies_to_string(cookies)

                # 简单验证：检查是否有必要的cookie
                has_required = all(required in cookie_string for required in REQUIRED_COOKIES)

                if has_required:
                    self.cookie_source = 'saved'
                    self.logger.debug("使用已保存的有效Cookie")
                    return cookie_string
                else:
                    self.logger.warning("已保存的Cookie缺少必要字段，需要重新登录")

        # 如果没有有效的cookies或强制重新登录，则执行登录
        self._warn_fallback()
        self.cookie_source = 'login'
        return self.login(force_relogin)

    def logout(self) -> None:
        """登出并清除本地cookies"""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            self.logger.debug("已清除登录信息")
        except Exception as e:
            self.logger.error(f"清除登录信息时出错: {e}")

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        # 浏览器中的登录态优先（同时决定下载是否可用）
        try:
            browser_cookies = get_browser_cookies()
            if browser_cookies and all(browser_cookies.get(name) for name in REQUIRED_COOKIES):
                self.cookie_source = 'browser'
                return True
        except Exception:
            pass

        saved_cookies = self._load_cookies()
        if saved_cookies is None:
            return False

        # 验证cookie是否有效
        try:
            cookies = saved_cookies['cookies']
            if not cookies:
                return False

            # 简单验证：检查是否有必要的cookie字段
            cookie_string = self._cookies_to_string(cookies)
            for required in REQUIRED_COOKIES:
                if required not in cookie_string:
                    return False

            self.cookie_source = 'saved'
            return True

        except Exception:
            return False


# 便捷函数
def get_auth_cookies(timeout: int = 300, force_relogin: bool = False) -> str:
    """获取认证cookies的便捷函数"""
    auth = QuarkAuth(timeout=timeout)
    return auth.get_cookies(force_relogin=force_relogin)
