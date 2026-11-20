# -*- coding: utf-8 -*-
"""
文件下载服务
"""

import os
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional

import httpx

from ..core.api_client import QuarkAPIClient
from ..exceptions import APIError, DownloadError

# 常规桌面浏览器 UA
_DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
)

# 夸克网盘客户端 UA。普通 UA 请求 file/download 时，大文件会返回
# code=23018 (download file size limit)，换用此 UA 重试即可绕过该限制。
_QUARK_CLIENT_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) quark-cloud-drive/2.5.56 Chrome/100.0.4896.160 '
    'Electron/18.3.5.12-a038f7b798 Safari/537.36 Channel/pckk_other_ch'
)

# 获取下载地址所需的固定参数，ve 必须与客户端版本保持一致
_DOWNLOAD_API_PARAMS = {
    'pr': 'ucpro',
    'fr': 'pc',
    'sys': 'win32',
    've': '2.5.56',
    'ut': '',
    'guid': '',
}

_DOWNLOAD_API_BASE = 'https://drive-pc.quark.cn/1/clouddrive'

# 「文件过大」错误码
_FILE_SIZE_LIMIT_CODE = 23018

# 流式下载的块大小，过小会明显拖慢大文件速度
_DEFAULT_CHUNK_SIZE = 1024 * 1024

# aria2c 默认参数，可通过 aria2_options 覆盖
_ARIA2_DEFAULT_OPTIONS: Dict[str, Any] = {
    'connections': 16,
    'split': 16,
    'min_split_size': '1M',
    'extra_args': [],
}


class FileDownloadService:
    """文件下载服务"""

    def __init__(self, client: QuarkAPIClient):
        """
        初始化文件下载服务

        Args:
            client: API客户端实例
        """
        self.client = client

    def _request_download_info(self, file_ids: List[str]) -> List[Dict]:
        """
        请求 file/download 接口，返回下载信息列表

        大文件会被服务端以 code=23018 拒绝，此时切换为夸克客户端 UA 重试一次。

        Args:
            file_ids: 文件ID列表

        Returns:
            下载信息列表
        """
        data = {'fids': list(file_ids)}

        try:
            response = self.client.post(
                'file/download',
                json_data=data,
                params=dict(_DOWNLOAD_API_PARAMS),
                base_url=_DOWNLOAD_API_BASE
            )
        except APIError as exc:
            code = (exc.response_data or {}).get('code')
            # 400 响应体的业务码可能是 23018，也可能被包在其他层
            if code != _FILE_SIZE_LIMIT_CODE and 'download file size limit' not in str(exc):
                raise
            # 命中「文件过大」限制：服务端只校验 UA，换成客户端 UA 即可
            response = self.client.post(
                'file/download',
                json_data=data,
                params=dict(_DOWNLOAD_API_PARAMS),
                headers={'user-agent': _QUARK_CLIENT_UA},
                base_url=_DOWNLOAD_API_BASE
            )

        data_list = response.get('data') if isinstance(response, dict) else None
        return [item for item in (data_list or []) if item]

    def get_download_url(self, file_id: str) -> str:
        """
        获取文件下载链接

        Args:
            file_id: 文件ID

        Returns:
            下载链接
        """
        infos = self._request_download_info([file_id])
        if not infos:
            raise APIError("无法获取下载链接")
        download_url = infos[0].get('download_url', '')
        if not download_url:
            raise APIError("无法获取下载链接")
        return download_url

    def get_download_urls(self, file_ids: List[str]) -> Dict[str, str]:
        """
        批量获取文件下载链接

        Args:
            file_ids: 文件ID列表

        Returns:
            文件ID到下载链接的映射字典
        """
        download_urls: Dict[str, str] = {}
        for download_info in self._request_download_info(file_ids):
            fid = download_info.get('fid', '')
            download_url = download_info.get('download_url', '')
            if fid and download_url:
                download_urls[fid] = download_url

        return download_urls

    def _build_download_headers(self) -> Dict[str, str]:
        """构建 CDN 直链下载所需的请求头（直链校验 cookie 与 referer）"""
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://pan.quark.cn/',
            'Origin': 'https://pan.quark.cn',
            'User-Agent': _DESKTOP_UA,
        }
        cookies = getattr(self.client, 'cookies', None)
        if cookies:
            headers['Cookie'] = cookies
        return headers

    @staticmethod
    def _sanitize_cookie(cookie: Optional[str]) -> str:
        """去掉换行与首尾空白，避免污染 aria2 的命令行头部参数"""
        if not cookie:
            return ''
        return cookie.replace('\n', '').replace('\r', '').strip()

    def _download_with_aria2(
        self,
        download_url: str,
        save_path: str,
        aria2_options: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        使用 aria2c 多连接下载

        直链必须带上与获取链接时一致的夸克客户端 UA、Referer 和 Cookie，
        否则 CDN 会返回 403。

        Args:
            download_url: 文件直链
            save_path: 本地保存路径
            aria2_options: 覆盖默认参数（connections/split/min_split_size/extra_args）
        """
        aria2c = shutil.which('aria2c')
        if not aria2c:
            raise DownloadError("未找到 aria2c，请先安装 aria2（如 apt install aria2）")

        options = dict(_ARIA2_DEFAULT_OPTIONS)
        options.update(aria2_options or {})

        command = [
            aria2c,
            '-c',  # 断点续传
            '-x', str(options['connections']),
            '-s', str(options['split']),
            '-k', str(options['min_split_size']),
            '--console-log-level=warn',
            '--dir', os.path.dirname(save_path) or '.',
            '-o', os.path.basename(save_path),
            '-U', _QUARK_CLIENT_UA,
            '--header', 'Referer: https://pan.quark.cn/',
        ]

        cookies = self._sanitize_cookie(getattr(self.client, 'cookies', None))
        if cookies:
            command += ['--header', f'Cookie: {cookies}']

        command += [str(arg) for arg in options.get('extra_args', [])]
        command.append(download_url)

        try:
            completed = subprocess.run(command, check=False)
        except OSError as exc:
            raise DownloadError(f"启动 aria2c 失败: {exc}") from exc

        if completed.returncode != 0:
            raise DownloadError(
                f"aria2c 下载失败（退出码 {completed.returncode}），"
                f"直链可能已过期，请重试"
            )

    def _stream_to_file(
        self,
        url: str,
        save_path: str,
        headers: Dict[str, str],
        chunk_size: int,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """流式下载到本地文件"""
        timeout = httpx.Timeout(60.0, connect=30.0)
        with httpx.stream('GET', url, headers=headers, timeout=timeout,
                          follow_redirects=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0) or 0)
            downloaded_size = 0

            with open(save_path, 'wb') as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded_size, total_size)

    def download_file(
        self,
        file_id: str,
        save_path: Optional[str] = None,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable] = None,
        downloader: str = 'native',
        aria2_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        下载文件

        Args:
            file_id: 文件ID
            save_path: 保存路径，如果为None则使用文件原名
            chunk_size: 下载块大小（仅原生下载生效）
            progress_callback: 进度回调函数 (downloaded_bytes, total_bytes)
            downloader: 'native' 使用内置流式下载，'aria2' 调用外部 aria2c
            aria2_options: aria2c 参数覆盖，见 _ARIA2_DEFAULT_OPTIONS

        Returns:
            实际保存的文件路径
        """

        # 获取下载链接和文件信息
        infos = self._request_download_info([file_id])
        if not infos:
            raise APIError("无法获取下载信息")

        download_info = infos[0]
        download_url = download_info.get('download_url', '')
        file_name = download_info.get('file_name', f'file_{file_id}')

        if not download_url:
            raise APIError("无法获取下载链接")

        # 确定保存路径
        if save_path is None:
            save_path = file_name
        elif os.path.isdir(save_path):
            save_path = os.path.join(save_path, file_name)

        # 此时 save_path 不会是 None
        assert save_path is not None

        # 创建目录
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        # 下载文件：直链校验 cookie 和 referer，必须显式带上
        if downloader == 'aria2':
            self._download_with_aria2(download_url, save_path, aria2_options)
            if progress_callback:
                size = os.path.getsize(save_path) if os.path.exists(save_path) else 0
                progress_callback(size, size)
            return save_path

        download_headers = self._build_download_headers()

        try:
            self._stream_to_file(
                download_url, save_path, download_headers,
                chunk_size, progress_callback
            )
        except Exception as exc:
            # 部分 CDN 节点会对浏览器 UA 返回 403，换客户端 UA 重试一次
            download_headers['User-Agent'] = _QUARK_CLIENT_UA
            try:
                self._stream_to_file(
                    download_url, save_path, download_headers,
                    chunk_size, progress_callback
                )
            except Exception:
                raise APIError(
                    f"下载失败: {exc}",
                    response_data={'download_url': download_url}
                ) from exc

        return save_path

    def download_files(
        self,
        file_ids: List[str],
        save_dir: str = "downloads",
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable] = None,
        downloader: str = 'native',
        aria2_options: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        批量下载文件

        Args:
            file_ids: 文件ID列表
            save_dir: 保存目录
            chunk_size: 下载块大小
            progress_callback: 进度回调函数 (current_file, total_files, file_progress)

        Returns:
            下载的文件路径列表
        """

        os.makedirs(save_dir, exist_ok=True)
        downloaded_files = []

        for i, file_id in enumerate(file_ids, 1):
            try:
                def file_progress(downloaded, total):
                    if progress_callback:
                        progress_callback(i, len(file_ids), downloaded, total)

                file_path = self.download_file(
                    file_id,
                    save_dir,
                    chunk_size,
                    file_progress,
                    downloader=downloader,
                    aria2_options=aria2_options
                )
                downloaded_files.append(file_path)

            except Exception as e:
                print(f"下载文件 {file_id} 失败: {e}")
                continue

        return downloaded_files
