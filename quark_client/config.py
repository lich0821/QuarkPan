"""
配置管理模块
"""

import os
from pathlib import Path
from typing import Any, Dict


def get_config_dir() -> Path:
    """获取配置目录路径"""
    # 优先使用环境变量
    config_dir = os.getenv('QUARK_CONFIG_DIR')
    if config_dir:
        return Path(config_dir)

    # 默认使用用户主目录下的 .quarkpan 文件夹（不受 cd 影响）
    return Path.home() / '.quarkpan'


def get_default_headers() -> Dict[str, str]:
    """获取默认的HTTP请求头"""
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400',
        'origin': 'https://pan.quark.cn',
        'referer': 'https://pan.quark.cn/',
        'accept-language': 'zh-CN,zh;q=0.9',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
    }


class Config:
    """配置类"""

    # API相关配置
    BASE_URL = 'https://drive-pc.quark.cn/1/clouddrive'
    SHARE_BASE_URL = 'https://drive.quark.cn/1/clouddrive'
    ACCOUNT_URL = 'https://pan.quark.cn/account'

    # 默认参数
    DEFAULT_PARAMS = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
    }

    # 请求超时设置
    REQUEST_TIMEOUT = 60.0

    # 重试设置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    # 分页设置
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100

    # 文件下载设置
    DOWNLOAD_CHUNK_SIZE = 8192
    DOWNLOAD_DIR = 'downloads'
