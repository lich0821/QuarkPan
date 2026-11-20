"""
夸克网盘API客户端核心模块
"""

import json
import time
from typing import Any, Dict, Optional

import httpx

from ..auth import QuarkAuth
from ..config import Config, get_default_headers
from ..exceptions import APIError, AuthenticationError, NetworkError


class QuarkAPIClient:
    """夸克网盘API客户端"""

    def __init__(self, cookies: Optional[str] = None, auto_login: bool = True):
        """
        初始化API客户端

        Args:
            cookies: Cookie字符串，如果为None则自动获取
            auto_login: 是否自动登录
        """
        self.cookies = cookies
        self.auto_login = auto_login
        self._client = None
        self._auth = None

        # 初始化HTTP客户端
        self._init_client()

        # 如果没有提供cookies且允许自动登录，则获取cookies
        if not self.cookies and auto_login:
            self._ensure_authenticated()

    def _init_client(self):
        """初始化HTTP客户端"""
        self._client = httpx.Client(
            timeout=Config.REQUEST_TIMEOUT,
            headers=get_default_headers(),
            follow_redirects=True
        )

    def _ensure_authenticated(self):
        """确保已认证"""
        if not self.cookies:
            if not self._auth:
                self._auth = QuarkAuth()
            self.cookies = self._auth.get_cookies()

    def _get_timestamp(self) -> int:
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    def _build_params(self, **kwargs) -> Dict[str, Any]:
        """构建请求参数"""
        params: Dict[str, Any] = Config.DEFAULT_PARAMS.copy()
        params.update({
            '__t': self._get_timestamp(),
            '__dt': 1000,  # 固定值
        })
        params.update(kwargs)
        return params

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """构建请求头"""
        headers = get_default_headers().copy()

        if self.cookies:
            headers['cookie'] = self.cookies

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            params: URL参数
            data: 表单数据
            json_data: JSON数据
            headers: 额外的请求头
            base_url: 基础URL，默认使用Config.BASE_URL

        Returns:
            响应的JSON数据

        Raises:
            APIError: API调用失败
            NetworkError: 网络错误
            AuthenticationError: 认证失败
        """
        if base_url is None:
            base_url = Config.BASE_URL

        full_url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"

        # 构建请求参数和头部
        request_params = self._build_params(**(params or {}))
        request_headers = self._build_headers(headers)

        try:
            # 发送请求
            if method.upper() == 'GET':
                response = self._client.get(  # type: ignore[attr-defined]
                    full_url,
                    params=request_params,
                    headers=request_headers
                )
            elif method.upper() == 'POST':
                if json_data:
                    response = self._client.post(  # type: ignore[attr-defined]
                        full_url,
                        params=request_params,
                        json=json_data,
                        headers=request_headers
                    )
                else:
                    response = self._client.post(  # type: ignore[attr-defined]
                        full_url,
                        params=request_params,
                        data=data,
                        headers=request_headers
                    )
            else:
                raise APIError(f"不支持的HTTP方法: {method}")

            # 检查HTTP状态码
            if response.status_code == 401:
                raise AuthenticationError("认证失败，请重新登录")
            elif response.status_code == 403:
                raise AuthenticationError("访问被拒绝，可能是Cookie过期")
            elif response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                    error_msg = f"HTTP错误: {response.status_code}, 响应: {error_data}"
                except Exception:
                    error_msg = f"HTTP错误: {response.status_code}, 响应: {response.text}"
                # 带上解析后的响应体，调用方可据此判断业务错误码（如 23018）
                raise APIError(error_msg, status_code=response.status_code, response_data=error_data)

            # 解析JSON响应
            try:
                result = response.json()
            except json.JSONDecodeError:
                raise APIError(f"响应不是有效的JSON格式: {response.text[:200]}")

            # 检查API响应状态
            if isinstance(result, dict):
                status = result.get('status')
                code = result.get('code')
                message = result.get('message', '未知错误')

                # 检查不同的错误状态
                if status == 'error' or (code and code != 0):
                    if 'login' in message.lower() or 'auth' in message.lower():
                        raise AuthenticationError(f"认证错误: {message}")
                    else:
                        raise APIError(f"API错误: {message}", response_data=result)

            return result

        except httpx.TimeoutException:
            raise NetworkError("请求超时")
        except httpx.RequestError as e:
            raise NetworkError(f"网络请求失败: {e}")

    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        return self._make_request('GET', url, params=params, **kwargs)

    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        return self._make_request('POST', url, data=data, json_data=json_data, **kwargs)

    def close(self):
        """关闭HTTP客户端"""
        if self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = exc_type, exc_val, exc_tb  # 参数未使用
        self.close()


# 便捷函数
def create_client(cookies: Optional[str] = None, auto_login: bool = True) -> QuarkAPIClient:
    """创建API客户端的便捷函数"""
    return QuarkAPIClient(cookies=cookies, auto_login=auto_login)
