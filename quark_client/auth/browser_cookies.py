# -*- coding: utf-8 -*-
"""
从本机浏览器读取夸克网盘 cookie

夸克 CDN 直链校验浏览器会话（依赖 httpOnly cookie ``__puus``），而通过 API
二维码登录拿不到它，表现为下载一律 412。这里直接从浏览器读取已登录的
cookie，作为获取凭证的默认方式。

目前只支持 Firefox：它的 cookie 明文存放在 ``cookies.sqlite``，用标准库
即可读取，不需要任何额外依赖。Chromium 系的 cookie 需要走系统 keyring
解密，暂不实现。

用法::

    from .browser_cookies import read_firefox_cookies
    cookies = read_firefox_cookies()   # {name: value}
"""

import configparser
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# 夸克网盘相关的 cookie 所在域，越靠后优先级越高（同名 cookie 更具体的覆盖更宽泛的）
QUARK_COOKIE_HOSTS = ('.quark.cn', '.pan.quark.cn', 'pan.quark.cn')

# 下载直链需要的浏览器专属 cookie，缺了它 CDN 会返回 412
DOWNLOAD_REQUIRED_COOKIES = ('__puus',)


def _firefox_root() -> Path:
    """Firefox 配置根目录（Linux 默认路径）"""
    return Path.home() / '.mozilla' / 'firefox'


def _profile_dirs_from_ini(root: Path) -> List[Path]:
    """从 profiles.ini 读取所有 profile 目录"""
    ini = root / 'profiles.ini'
    if not ini.is_file():
        return []

    parser = configparser.RawConfigParser()
    try:
        parser.read(ini, encoding='utf-8')
    except Exception:
        return []

    dirs: List[Path] = []
    for section in parser.sections():
        if not section.startswith('Profile'):
            continue
        raw_path = parser.get(section, 'Path', fallback=None)
        if not raw_path:
            continue
        is_relative = parser.getboolean(section, 'IsRelative', fallback=True)
        path = (root / raw_path) if is_relative else Path(raw_path)
        if path.is_dir():
            dirs.append(path)
    return dirs


def _discover_profile_dirs() -> List[Path]:
    """
    找出所有可能存放 cookie 的 Firefox profile 目录

    优先读 profiles.ini，读不到就扫描子目录里的 cookies.sqlite。
    """
    root = _firefox_root()
    if not root.is_dir():
        return []

    dirs = _profile_dirs_from_ini(root)
    if dirs:
        return dirs

    return sorted({p.parent for p in root.glob('*/cookies.sqlite')})


def _query_profile(db_path: Path) -> List[tuple]:
    """
    读取单个 profile 里未过期的夸克 cookie

    以 immutable=1 只读打开，避免 Firefox 正在运行时锁库。

    Returns:
        [(host, name, value, path, expiry_seconds), ...]
    """
    now_ms = int(time.time() * 1000)
    placeholders = ','.join('?' * len(QUARK_COOKIE_HOSTS))
    sql = (
        'SELECT host, name, value, path, expiry FROM moz_cookies '
        f'WHERE host IN ({placeholders}) '
        'AND (expiry = 0 OR expiry > ?)'
    )

    conn = None
    try:
        # 路径可能含空格/中文，必须用 as_uri() 做百分号编码
        conn = sqlite3.connect(f'{db_path.as_uri()}?immutable=1', uri=True)
        rows = conn.execute(sql, (*QUARK_COOKIE_HOSTS, now_ms)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()

    result = []
    for host, name, value, path, expiry in rows:
        # Firefox 的 expiry 单位是毫秒，这里统一成秒
        expiry_seconds = int(expiry / 1000) if expiry else 0
        result.append((host, name, value or '', path or '/', expiry_seconds))
    return result


def _host_rank(host: str) -> int:
    """域名越具体排序越靠后，便于同名 cookie 覆盖前面的宽泛值"""
    try:
        return QUARK_COOKIE_HOSTS.index(host)
    except ValueError:
        return len(QUARK_COOKIE_HOSTS)


def read_firefox_cookies(profile_dirs: Optional[Iterable[Path]] = None) -> Dict[str, str]:
    """
    从 Firefox 读取已登录的夸克 cookie

    Args:
        profile_dirs: 指定 profile 目录，默认自动发现

    Returns:
        {cookie名: value}，读不到时返回空字典（不抛异常）
    """
    dirs = list(profile_dirs) if profile_dirs is not None else _discover_profile_dirs()

    for profile_dir in dirs:
        db_path = Path(profile_dir) / 'cookies.sqlite'
        if not db_path.is_file():
            continue

        rows = _query_profile(db_path)
        if not rows:
            continue

        # 同名 cookie 取域名更具体的那个
        rows.sort(key=lambda row: _host_rank(row[0]))
        return {name: value for _host, name, value, _path, _exp in rows}

    return {}


def is_usable_for_download(cookies: Dict[str, str]) -> bool:
    """判断这套 cookie 是否带有下载直链需要的浏览器会话字段"""
    return all(cookies.get(name) for name in DOWNLOAD_REQUIRED_COOKIES)


def to_cookie_records(cookies: Dict[str, str]) -> List[Dict]:
    """
    转换为 cookies.json 使用的记录格式

    ``expires`` 为 0 表示会话 cookie。
    """
    return [
        {
            'name': name,
            'value': value,
            'domain': '.quark.cn',
            'path': '/',
            'expires': 0,
        }
        for name, value in cookies.items()
    ]


def get_browser_cookies() -> Dict[str, str]:
    """获取浏览器里已登录的夸克 cookie（当前仅 Firefox）"""
    return read_firefox_cookies()
