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
        self.cookies_plain_file = self.config_dir / "cookies.txt"
        self.logger = get_logger(__name__)

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
            # 同时以纯文本方式导出，方便交给其它工具复用
            self._save_cookies_plain_text(cookies)
        except Exception as e:
            raise ConfigError(f"保存cookies失败: {e}")

    def _save_cookies_plain_text(self, cookies: List[Dict]) -> None:
        """将cookies以纯文本形式导出到本地文件"""
        try:
            cookie_string = self._cookies_to_string(cookies)
            with open(self.cookies_plain_file, 'w', encoding='utf-8') as f:
                f.write(cookie_string)
        except Exception as e:
            self.logger.warning(f"保存纯文本cookies失败: {e}")

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
        # 如果不是强制重新登录，先尝试使用已保存的cookies
        if not force_relogin:
            saved_cookies = self._load_cookies()
            if saved_cookies:
                self.logger.info("使用已保存的登录凭证")
                return self._cookies_to_string(saved_cookies['cookies'])

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

    def get_cookies(self, force_relogin: bool = False) -> str:
        """
        获取有效的cookies字符串

        Args:
            force_relogin: 是否强制重新登录

        Returns:
            Cookie字符串
        """
        # 如果不强制重新登录，先尝试返回已保存的cookies
        if not force_relogin:
            saved_cookies = self._load_cookies()
            if saved_cookies:
                cookies = saved_cookies['cookies']
                cookie_string = self._cookies_to_string(cookies)

                # 简单验证：检查是否有必要的cookie
                required_cookies = ['__pus', '__kps', '__uid']  # 夸克网盘的关键cookie
                has_required = all(required in cookie_string for required in required_cookies)

                if has_required:
                    self.logger.debug("使用已保存的有效Cookie")
                    return cookie_string
                else:
                    self.logger.warning("已保存的Cookie缺少必要字段，需要重新登录")

        # 如果没有有效的cookies或强制重新登录，则执行登录
        return self.login(force_relogin)

    def logout(self) -> None:
        """登出并清除本地cookies"""
        try:
            for file in [self.cookies_file, self.cookies_plain_file]:
                if file.exists():
                    file.unlink()
            self.logger.debug("已清除登录信息")
        except Exception as e:
            self.logger.error(f"清除登录信息时出错: {e}")

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
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
            required_cookies = ['__pus', '__kps', '__uid']  # 夸克网盘的关键cookie

            for required in required_cookies:
                if required not in cookie_string:
                    return False

            return True

        except Exception:
            return False


# 便捷函数
def get_auth_cookies(timeout: int = 300, force_relogin: bool = False) -> str:
    """获取认证cookies的便捷函数"""
    auth = QuarkAuth(timeout=timeout)
    return auth.get_cookies(force_relogin=force_relogin)
