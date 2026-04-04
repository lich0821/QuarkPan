# -*- coding: utf-8 -*-
"""
夸克网盘客户端主类
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from .auth import QuarkAuth
from .core.api_client import QuarkAPIClient
from .services.batch_share_service import BatchShareService
from .services.file_download_service import FileDownloadService
from .services.file_service import FileService
from .services.file_upload_service import FileUploadService
from .services.name_resolver import NameResolver
from .services.share_service import ShareService


class QuarkClient:
    """夸克网盘客户端主类"""

    def __init__(self, cookies: Optional[str] = None, auto_login: bool = True):
        """
        初始化夸克网盘客户端

        Args:
            cookies: Cookie字符串，如果为None则自动获取
            auto_login: 是否自动登录
        """
        # 初始化API客户端
        self.api_client = QuarkAPIClient(cookies=cookies, auto_login=auto_login)

        # 初始化服务
        self.files = FileService(self.api_client)
        self.upload = FileUploadService(self.api_client)
        self.download = FileDownloadService(self.api_client)
        self.shares = ShareService(self.api_client)
        self.batch_shares = BatchShareService(self.api_client)
        self.name_resolver = NameResolver(self.files)

        # 保存认证信息
        self._auth = None

    @property
    def auth(self) -> QuarkAuth:
        """获取认证管理器"""
        if not self._auth:
            self._auth = QuarkAuth()
        return self._auth

    def login(self, force_relogin: bool = False, use_qr: bool = True, method: str = "auto") -> str:
        """
        执行多层级登录

        Args:
            force_relogin: 是否强制重新登录
            use_qr: 是否使用二维码登录（兼容性参数）
            method: 登录方式 ("auto", "api", "simple")

        Returns:
            Cookie字符串
        """
        cookies = self.auth.login(force_relogin, use_qr, method)
        self.api_client.cookies = cookies
        return cookies

    def logout(self):
        """登出"""
        self.auth.logout()
        self.api_client.cookies = None

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.auth.is_logged_in()

    # 文件管理快捷方法
    def list_files(self, folder_id: str = "0", **kwargs) -> Dict[str, Any]:
        """获取文件列表"""
        return self.files.list_files(folder_id, **kwargs)

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """获取文件信息"""
        return self.files.get_file_info(file_id)

    def search_files(self, keyword: str, **kwargs) -> Dict[str, Any]:
        """搜索文件"""
        return self.files.search_files(keyword, **kwargs)

    def get_download_url(self, file_id: str) -> str:
        """获取下载链接"""
        return self.download.get_download_url(file_id)

    def get_download_urls(self, file_ids: List[str]) -> Dict[str, str]:
        """批量获取下载链接"""
        return self.download.get_download_urls(file_ids)

    def download_file(self, file_id: str, save_path: Optional[str] = None, **kwargs) -> str:
        """下载文件"""
        return self.download.download_file(file_id, save_path, **kwargs)

    def download_files(self, file_ids: List[str], save_dir: str = "downloads", **kwargs) -> List[str]:
        """批量下载文件"""
        return self.download.download_files(file_ids, save_dir, **kwargs)

    # 基于名称的操作方法
    def resolve_path(self, path: str, current_folder_id: str = "0") -> tuple:
        """解析文件路径到ID"""
        return self.name_resolver.resolve_path(path, current_folder_id)

    def delete_files_by_name(self, paths: List[str], current_folder_id: str = "0") -> Dict[str, Any]:
        """根据文件名删除文件"""
        resolved = self.name_resolver.resolve_multiple_paths(paths, current_folder_id)
        file_ids = [item[0] for item in resolved]
        return self.delete_files(file_ids)

    def rename_file_by_name(self, old_path: str, new_name: str, current_folder_id: str = "0") -> Dict[str, Any]:
        """根据文件名重命名文件"""
        file_id, _ = self.name_resolver.resolve_path(old_path, current_folder_id)
        return self.rename_file(file_id, new_name)

    def move_files_by_name(self, paths: List[str], target_path: str, current_folder_id: str = "0") -> Dict[str, Any]:
        """根据文件名移动文件"""
        # 解析源文件
        resolved = self.name_resolver.resolve_multiple_paths(paths, current_folder_id)
        file_ids = [item[0] for item in resolved]

        # 解析目标文件夹
        target_id, target_type = self.name_resolver.resolve_path(target_path, current_folder_id)
        if target_type != 'folder':
            raise ValueError(f"目标路径必须是文件夹: {target_path}")

        return self.move_files(file_ids, target_id)

    def download_file_by_name(
            self, path: str, save_path: Optional[str] = None, current_folder_id: str = "0", **kwargs) -> str:
        """根据文件名下载文件"""
        file_id, file_type = self.name_resolver.resolve_path(path, current_folder_id)
        if file_type != 'file':
            raise ValueError(f"只能下载文件，不能下载文件夹: {path}")
        return self.download_file(file_id, save_path, **kwargs)

    def get_file_info_by_name(self, path: str, current_folder_id: str = "0") -> Dict[str, Any]:
        """根据文件名获取文件信息"""
        file_id, _ = self.name_resolver.resolve_path(path, current_folder_id)
        return self.get_file_info(file_id)

    def get_real_file_name(self, file_id: str) -> Optional[str]:
        """获取文件的真实名称（从列表缓存中获取）"""
        return self.name_resolver.get_real_name(file_id)

    def list_files_with_details(self, **kwargs) -> Dict[str, Any]:
        """获取文件列表（增强版）"""
        return self.files.list_files_with_details(**kwargs)

    def search_files_advanced(self, keyword: str, **kwargs) -> Dict[str, Any]:
        """高级文件搜索"""
        return self.files.search_files_advanced(keyword, **kwargs)

    def create_folder(self, folder_name: str, parent_id: str = "0") -> Dict[str, Any]:
        """创建文件夹"""
        return self.files.create_folder(folder_name, parent_id)

    def delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """删除文件"""
        return self.files.delete_files(file_ids)

    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """重命名文件"""
        return self.files.rename_file(file_id, new_name)

    def batch_save_shares(
        self,
        share_urls: List[str],
        target_folder_id: str = "0",
        create_subfolder: bool = False,
        save_all: bool = True,
        wait_for_completion: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        批量转存分享链接

        Args:
            share_urls: 分享链接列表
            target_folder_id: 目标文件夹ID
            create_subfolder: 是否为每个分享创建子文件夹
            save_all: 是否保存全部文件
            wait_for_completion: 是否等待转存任务完成
            progress_callback: 进度回调函数

        Returns:
            转存结果列表
        """
        if create_subfolder:
            # 使用原有逻辑，为每个分享创建子文件夹
            results = []
            for i, share_url in enumerate(share_urls):
                try:
                    folder_name = f"分享_{i+1}"
                    result = self.save_shared_files(
                        share_url,
                        target_folder_id,
                        target_folder_name=folder_name,
                        save_all=save_all,
                        wait_for_completion=wait_for_completion
                    )

                    results.append({
                        'success': True,
                        'share_url': share_url,
                        'result': result
                    })

                    if progress_callback:
                        progress_callback(i+1, len(share_urls), share_url, result)

                except Exception as e:
                    error_result = {
                        'success': False,
                        'share_url': share_url,
                        'error': str(e)
                    }
                    results.append(error_result)

                    if progress_callback:
                        progress_callback(i+1, len(share_urls), share_url, error_result)

            return results
        else:
            # 使用新的批量转存功能
            return self.shares.batch_save_shares(
                share_urls=share_urls,
                target_folder_id=target_folder_id,
                save_all=save_all,
                wait_for_completion=wait_for_completion,
                progress_callback=progress_callback
            )

    def sync_folder(
        self,
        local_path: str,
        remote_folder_id: str = "0",
        upload_new: bool = True,
        delete_remote: bool = False
    ) -> Dict[str, Any]:
        """
        同步本地文件夹到云端（占位符，需要实现上传功能）

        Args:
            local_path: 本地文件夹路径
            remote_folder_id: 远程文件夹ID
            upload_new: 是否上传新文件
            delete_remote: 是否删除远程多余文件

        Returns:
            同步结果
        """
        # TODO: 实现文件上传和同步逻辑
        _ = local_path, remote_folder_id, upload_new, delete_remote  # 参数将在未来实现中使用
        raise NotImplementedError("文件同步功能待实现")

    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储空间信息

        Returns:
            存储信息
        """
        try:
            response = self.api_client.get('member')      #26-4-4 由capacity变更为member
            return response
        except Exception as e:
            return {'error': str(e)}

    def upload_file(
        self,
        file_path: str,
        parent_folder_id: str = "0",
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        上传文件到夸克网盘

        Args:
            file_path: 本地文件路径
            parent_folder_id: 父文件夹ID，默认为根目录
            progress_callback: 进度回调函数

        Returns:
            上传结果字典
        """
        return self.upload.upload_file(file_path, parent_folder_id, progress_callback)

    # 分享相关方法
    def create_share(
        self,
        file_ids: List[str],
        title: str = "",
        expire_days: int = 0,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建分享链接

        Args:
            file_ids: 文件ID列表
            title: 分享标题
            expire_days: 过期天数，0表示永久
            password: 提取码，None表示无密码

        Returns:
            分享信息，包含分享链接
        """
        return self.shares.create_share(file_ids, title, expire_days, password)

    def parse_share_url(self, share_url: str) -> Tuple[str, Optional[str]]:
        """
        解析分享链接

        Args:
            share_url: 分享链接

        Returns:
            (share_id, password) 元组
        """
        return self.shares.parse_share_url(share_url)

    def save_shared_files(
        self,
        share_url: str,
        target_folder_id: str = "0",
        target_folder_name: Optional[str] = None,
        file_filter: Optional[Callable] = None,
        save_all: bool = True,
        wait_for_completion: bool = True,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        转存分享的文件

        Args:
            share_url: 分享链接
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称
            file_filter: 文件过滤函数
            save_all: 是否保存全部文件
            wait_for_completion: 是否等待转存任务完成

        Returns:
            转存结果
        """
        return self.shares.parse_and_save(
            share_url, target_folder_id, target_folder_name,
            file_filter, save_all, wait_for_completion, timeout
        )

    def get_my_shares(self, page: int = 1, size: int = 50) -> Dict[str, Any]:
        """
        获取我的分享列表

        Args:
            page: 页码
            size: 每页数量

        Returns:
            分享列表
        """
        return self.shares.get_my_shares(page, size)

    # 文件操作方法
    def move_files(
        self,
        file_ids: List[str],
        target_folder_id: str,
        exclude_fids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        移动文件到指定文件夹

        Args:
            file_ids: 要移动的文件ID列表
            target_folder_id: 目标文件夹ID
            exclude_fids: 排除的文件ID列表

        Returns:
            移动结果
        """
        return self.files.move_files(file_ids, target_folder_id, exclude_fids)

    def close(self):
        """关闭客户端"""
        self.api_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = exc_type, exc_val, exc_tb  # 参数未使用
        self.close()


# 便捷函数
def create_client(cookies: Optional[str] = None, auto_login: bool = True) -> QuarkClient:
    """创建夸克网盘客户端的便捷函数"""
    return QuarkClient(cookies=cookies, auto_login=auto_login)
