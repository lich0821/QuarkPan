"""
分享服务
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config import Config
from ..core.api_client import QuarkAPIClient
from ..exceptions import APIError, ShareLinkError


class ShareService:
    """分享服务"""

    def __init__(self, client: QuarkAPIClient):
        """
        初始化分享服务

        Args:
            client: API客户端实例
        """
        self.client = client

    def check_existing_shares(self, file_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        检查文件是否已经分享过

        Args:
            file_ids: 要检查的文件ID列表

        Returns:
            字典，key为文件ID，value为分享信息（如果已分享）
        """
        if not file_ids:
            return {}

        existing_shares = {}

        try:
            # 获取所有分享列表
            shares_response = self.get_my_shares(page=1, size=100)  # 获取更多分享

            if shares_response.get('status') != 200:
                # 如果获取分享列表失败，返回空字典，不影响正常分享流程
                return {}

            shares_data = shares_response.get('data', {})
            shares_list = shares_data.get('list', [])

            # 构建文件ID到分享信息的映射
            for share in shares_list:
                # 只考虑有效的分享（未过期、状态正常）
                if share.get('status') != 1:  # 1表示正常状态
                    continue

                # 获取分享中的文件ID
                share_fid = share.get('first_fid')
                if share_fid and share_fid in file_ids:
                    existing_shares[share_fid] = {
                        'share_id': share.get('share_id'),
                        'share_url': share.get('share_url'),
                        'title': share.get('title', ''),
                        'created_at': share.get('created_at'),
                        'expired_at': share.get('expired_at'),
                        'file_num': share.get('file_num', 1)
                    }

        except Exception:
            # 如果检查过程出错，返回空字典，不影响正常分享流程
            pass

        return existing_shares

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
        import time

        # 第一步：创建分享任务
        data = {
            'fid_list': file_ids,
            'title': title,
            'url_type': 2 if password else 1,  # 1=公开链接, 2=私密链接
            'expired_type': 1 if expire_days == 0 else 2  # 1=永久，2=有期限
        }

        # 如果设置了过期时间，添加过期时间字段
        if expire_days > 0:
            import time
            expired_at = int((time.time() + expire_days * 24 * 3600) * 1000)  # 毫秒时间戳
            data['expired_at'] = expired_at

        # 如果设置了密码，添加密码字段
        if password:
            data['passcode'] = password

        response = self.client.post('share', json_data=data)

        if not response.get('status') == 200:
            raise APIError(f"创建分享失败: {response.get('message', '未知错误')}")

        # 获取任务ID
        task_id = response.get('data', {}).get('task_id')
        if not task_id:
            raise APIError("无法获取分享任务ID")

        # 第二步：轮询任务状态，等待分享创建完成
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            task_response = self.client.get(
                'task',
                params={
                    'task_id': task_id,
                    'retry_index': retry_count
                }
            )

            if task_response.get('status') == 200:
                task_data = task_response.get('data', {})

                # 检查任务状态
                if task_data.get('status') == 2:  # 任务完成
                    share_id = task_data.get('share_id')
                    if share_id:
                        # 第三步：获取完整的分享信息
                        return self._get_share_details(share_id)
                elif task_data.get('status') == 3:  # 任务失败
                    raise APIError(f"分享创建失败: {task_data.get('message', '任务失败')}")

            retry_count += 1
            time.sleep(1)  # 等待1秒后重试

        raise APIError("分享创建超时")

    def _get_share_details(self, share_id: str) -> Dict[str, Any]:
        """
        获取分享详细信息，包括分享链接

        Args:
            share_id: 分享ID

        Returns:
            完整的分享信息
        """
        data = {'share_id': share_id}

        response = self.client.post('share/password', json_data=data)

        if not response.get('status') == 200:
            raise APIError(f"获取分享详情失败: {response.get('message', '未知错误')}")

        return response.get('data', {})

    def get_my_shares(self, page: int = 1, size: int = 50) -> Dict[str, Any]:
        """
        获取我的分享列表

        Args:
            page: 页码
            size: 每页数量

        Returns:
            分享列表
        """
        params = {
            '_page': page,
            '_size': size,
            '_order_field': 'created_at',
            '_order_type': 'desc',  # 降序
            '_fetch_total': 1,
            '_fetch_notify_follow': 1
        }

        response = self.client.get('share/mypage/detail', params=params)
        return response

    def parse_share_url(self, share_url: str) -> Tuple[str, Optional[str]]:
        """
        解析分享链接，提取分享ID和密码

        Args:
            share_url: 分享链接

        Returns:
            (share_id, password) 元组

        Raises:
            ShareLinkError: 链接格式错误
        """
        # 支持多种分享链接格式
        patterns = [
            # 夸克网盘标准格式
            r'https://pan\.quark\.cn/s/([a-zA-Z0-9]+)',
            # 带密码的格式
            r'https://pan\.quark\.cn/s/([a-zA-Z0-9]+).*?密码[：:]?\s*([a-zA-Z0-9]+)',
            # 其他可能的格式
            r'quark://share/([a-zA-Z0-9]+)',
        ]

        share_id = None
        password = None

        for pattern in patterns:
            match = re.search(pattern, share_url, re.IGNORECASE)
            if match:
                share_id = match.group(1)
                if len(match.groups()) > 1:
                    password = match.group(2)
                break

        if not share_id:
            raise ShareLinkError(f"无法解析分享链接: {share_url}")

        # 尝试从文本中提取密码
        if not password:
            password_patterns = [
                r'密码[：:]?\s*([a-zA-Z0-9]+)',
                r'提取码[：:]?\s*([a-zA-Z0-9]+)',
                r'code[：:]?\s*([a-zA-Z0-9]+)',
            ]

            for pattern in password_patterns:
                match = re.search(pattern, share_url, re.IGNORECASE)
                if match:
                    password = match.group(1)
                    break

        return share_id, password

    def get_share_token(self, share_id: str, password: Optional[str] = None) -> str:
        """
        获取分享访问令牌

        Args:
            share_id: 分享ID
            password: 提取码

        Returns:
            访问令牌
        """
        data = {
            'pwd_id': share_id,
            'passcode': password or '',
            'support_visit_limit_private_share': True
        }

        # 使用分享专用的API基础URL
        response = self.client.post(
            'share/sharepage/token',
            json_data=data,
            base_url=Config.SHARE_BASE_URL
        )

        # 提取token
        if isinstance(response, dict) and 'data' in response:
            token_info = response['data']
            return token_info.get('stoken', '')

        raise ShareLinkError("无法获取分享访问令牌")

    def get_share_info(self, share_id: str, token: str, pdir_fid: str = "0") -> Dict[str, Any]:
        """
        获取分享详细信息

        Args:
            share_id: 分享ID
            token: 访问令牌
            pdir_fid: 父目录ID，根目录为 "0"

        Returns:
            分享信息
        """
        params = {
            'pwd_id': share_id,
            'stoken': token,
            'pdir_fid': pdir_fid,
            'force': '0',
            '_page': 1,
            '_size': 50,
            '_fetch_banner': '1',
            '_fetch_share': '1',
            '_fetch_total': '1',
            '_sort': 'file_type:asc,file_name:asc'
        }

        response = self.client.get(
            'share/sharepage/detail',
            params=params,
            base_url=Config.SHARE_BASE_URL
        )

        return response

    def save_shared_files(
        self,
        share_id: str,
        token: str,
        file_ids: List[str],
        target_folder_id: str = "0",
        target_folder_name: Optional[str] = None,
        pdir_fid: str = "0",
        save_all: bool = False,
        wait_for_completion: bool = True,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        转存分享的文件

        Args:
            share_id: 分享ID
            token: 访问令牌
            file_ids: 要转存的文件ID列表
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称（如果需要创建新文件夹）
            pdir_fid: 源目录ID，根目录为 "0"
            save_all: 是否保存全部文件
            wait_for_completion: 是否等待转存任务完成

        Returns:
            转存结果
        """
        data = {
            'fid_list': file_ids,
            'fid_token_list': [],
            'to_pdir_fid': target_folder_id,
            'pwd_id': share_id,
            'stoken': token,
            'pdir_fid': pdir_fid,
            'pdir_save_all': save_all,
            'exclude_fids': [],
            'scene': 'link'
        }

        # 如果指定了目标文件夹名称，添加到请求中
        if target_folder_name:
            data['to_pdir_name'] = target_folder_name

        response = self.client.post(
            'share/sharepage/save',
            json_data=data,
            base_url=Config.SHARE_BASE_URL
        )

        if not response.get('status') == 200:
            error_msg = f"转存失败: {response.get('message', '未知错误')}"
            raise APIError(error_msg)

        # 如果需要等待任务完成
        if wait_for_completion:
            task_id = response.get('data', {}).get('task_id')
            if task_id:
                # 等待转存任务完成
                task_result = self._wait_for_save_task_completion(task_id, timeout)
                response['task_result'] = task_result

        return response

    def _wait_for_save_task_completion(self, task_id: str, timeout: int = 60) -> Dict[str, Any]:
        """
        等待转存任务完成

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            任务完成结果
        """
        import time

        start_time = time.time()
        retry_index = 0
        max_retries = timeout // 1  # 每1秒检查一次

        while retry_index < max_retries and time.time() - start_time < timeout:
            try:
                task_response = self.client.get(
                    'task',
                    params={
                        'task_id': task_id,
                        'retry_index': retry_index
                    }
                )

                if task_response.get('status') == 200:
                    task_data = task_response.get('data', {})
                    status = task_data.get('status')
                    message = task_data.get('message', '')

                    # 使用数字状态值，与 FileService 保持一致
                    if status == 2:  # 任务完成
                        return task_response
                    elif status == 3:  # 任务失败
                        error_msg = f"转存任务失败: {message or '任务失败'}"
                        raise APIError(error_msg)
                    elif status in [0, 1]:  # 0=PENDING, 1=RUNNING
                        # 任务进行中，继续等待
                        pass
                    # 其他状态也继续等待

                retry_index += 1
                if retry_index < max_retries:
                    time.sleep(1)

            except Exception as e:
                elapsed = time.time() - start_time
                error_str = str(e)

                # 检查是否是容量不足错误，如果是则立即停止重试
                if "capacity limit" in error_str:
                    raise APIError("转存失败: 网盘容量不足，请清理空间后重试")

                # 检查其他不需要重试的错误
                non_retry_errors = [
                    "permission denied",
                    "access denied",
                    "forbidden",
                    "unauthorized",
                    "file not found",
                    "share expired",
                    "share not found"
                ]

                if any(err in error_str.lower() for err in non_retry_errors):
                    raise APIError(f"转存失败: {error_str}")

                if elapsed >= timeout - 5:  # 接近超时时抛出异常
                    raise APIError(f"转存任务监控失败: {e}")

                retry_index += 1
                if retry_index < max_retries:
                    time.sleep(1)

        raise APIError(f"转存任务超时 (超过 {timeout} 秒)")

    def parse_and_save(
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
        解析分享链接并转存文件（一站式服务）

        Args:
            share_url: 分享链接
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称
            file_filter: 文件过滤函数，接收文件信息字典，返回True表示转存
            save_all: 是否保存全部文件
            wait_for_completion: 是否等待转存任务完成

        Returns:
            转存结果
        """
        # 1. 解析分享链接
        share_id, password = self.parse_share_url(share_url)

        # 2. 获取访问令牌
        token = self.get_share_token(share_id, password)

        # 3. 获取分享信息
        share_info = self.get_share_info(share_id, token)

        # 4. 提取文件列表
        if not isinstance(share_info, dict) or 'data' not in share_info:
            raise ShareLinkError("无法获取分享文件列表")

        files = share_info['data'].get('list', [])
        if not files:
            raise ShareLinkError("分享中没有文件")

        # 5. 应用文件过滤器
        if file_filter:
            files = [f for f in files if file_filter(f)]
            save_all = False  # 如果有过滤器，不能使用 save_all

        # 6. 提取文件ID（如果不是保存全部）
        file_ids = [] if save_all else [f['fid'] for f in files]

        # 7. 转存文件
        result = self.save_shared_files(
            share_id=share_id,
            token=token,
            file_ids=file_ids,
            target_folder_id=target_folder_id,
            target_folder_name=target_folder_name,
            save_all=save_all,
            wait_for_completion=wait_for_completion,
            timeout=timeout
        )

        # 8. 添加额外信息到结果中
        result['share_info'] = {
            'share_id': share_id,
            'file_count': len(files),
            'files': files
        }

        return result

    def batch_save_shares(
        self,
        share_urls: List[str],
        target_folder_id: str = "0",
        target_folder_name: Optional[str] = None,
        save_all: bool = True,
        wait_for_completion: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        批量转存分享链接

        Args:
            share_urls: 分享链接列表
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称
            save_all: 是否保存全部文件
            wait_for_completion: 是否等待转存任务完成
            progress_callback: 进度回调函数，接收 (current, total, url, result)

        Returns:
            转存结果列表
        """
        results = []
        total = len(share_urls)

        for i, share_url in enumerate(share_urls, 1):
            try:
                result = self.parse_and_save(
                    share_url=share_url,
                    target_folder_id=target_folder_id,
                    target_folder_name=target_folder_name,
                    save_all=save_all,
                    wait_for_completion=wait_for_completion
                )

                result['success'] = True
                result['url'] = share_url
                results.append(result)

                if progress_callback:
                    progress_callback(i, total, share_url, result)

            except Exception as e:
                error_result = {
                    'success': False,
                    'url': share_url,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                results.append(error_result)

                if progress_callback:
                    progress_callback(i, total, share_url, error_result)

        return results

    def save_share_url(
        self,
        share_url: str,
        target_folder_id: str = "0",
        wait_for_completion: bool = True,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        简化的分享链接转存方法

        Args:
            share_url: 分享链接
            target_folder_id: 目标文件夹ID
            wait_for_completion: 是否等待转存任务完成

        Returns:
            转存结果
        """
        return self.parse_and_save(
            share_url=share_url,
            target_folder_id=target_folder_id,
            save_all=True,
            wait_for_completion=wait_for_completion
        )

    def delete_share(self, share_id: str) -> Dict[str, Any]:
        """
        删除分享

        Args:
            share_id: 分享ID

        Returns:
            删除结果
        """
        data = {'share_id': share_id}

        response = self.client.post('share/delete', json_data=data)
        return response

    def smart_batch_create_shares(
        self,
        file_ids: List[str],
        title: str = "",
        expire_days: int = 0,
        password: Optional[str] = None,
        check_duplicates: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        智能批量创建分享链接（自动检查重复）

        Args:
            file_ids: 文件ID列表
            title: 分享标题
            expire_days: 过期天数，0表示永久
            password: 分享密码
            check_duplicates: 是否检查重复分享
            progress_callback: 进度回调函数

        Returns:
            批量分享结果
        """
        if not file_ids:
            return {
                'status': 400,
                'message': '文件列表不能为空',
                'data': {
                    'total': 0,
                    'new_created': 0,
                    'reused': 0,
                    'failed': 0,
                    'results': []
                }
            }

        results = []
        new_created = 0
        reused = 0
        failed = 0

        # 检查已有分享
        existing_shares = {}
        if check_duplicates:
            existing_shares = self.check_existing_shares(file_ids)

        total = len(file_ids)

        for i, file_id in enumerate(file_ids):
            try:
                # 检查是否已经分享过
                if file_id in existing_shares:
                    # 复用现有分享
                    share_info = existing_shares[file_id]
                    result = {
                        'file_id': file_id,
                        'status': 'reused',
                        'share_url': share_info['share_url'],
                        'share_id': share_info['share_id'],
                        'title': share_info['title'],
                        'message': '复用现有分享'
                    }
                    reused += 1
                else:
                    # 创建新分享
                    share_response = self.create_share(
                        file_ids=[file_id],
                        title=title,
                        expire_days=expire_days,
                        password=password
                    )

                    # 检查是否有分享链接，表示分享成功
                    if share_response.get('share_url'):
                        result = {
                            'file_id': file_id,
                            'status': 'created',
                            'share_url': share_response.get('share_url'),
                            'share_id': share_response.get('pwd_id'),  # 分享ID字段名
                            'title': share_response.get('title', title),
                            'message': '创建新分享成功'
                        }
                        new_created += 1
                    else:
                        result = {
                            'file_id': file_id,
                            'status': 'failed',
                            'message': '创建分享失败: 未获取到分享链接'
                        }
                        failed += 1

                results.append(result)

                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, total, file_id, result)

            except Exception as e:
                result = {
                    'file_id': file_id,
                    'status': 'failed',
                    'message': f'处理失败: {str(e)}'
                }
                results.append(result)
                failed += 1

                if progress_callback:
                    progress_callback(i + 1, total, file_id, result)

        return {
            'status': 200,
            'message': f'批量分享完成: 新建 {new_created}, 复用 {reused}, 失败 {failed}',
            'data': {
                'total': total,
                'new_created': new_created,
                'reused': reused,
                'failed': failed,
                'results': results
            }
        }
