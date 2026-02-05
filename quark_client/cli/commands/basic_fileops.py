"""
基础文件操作命令
"""

from typing import List, Optional

import typer
from rich.prompt import Confirm

from ..utils import (get_client, handle_api_error, print_error, print_info,
                     print_success, print_warning)


def create_folder(folder_name: str, parent_id: str = "0"):
    """创建文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在创建文件夹: {folder_name}")

            result = client.create_folder(folder_name, parent_id)

            if result and result.get('status') == 200:
                print_success(f"文件夹创建成功: {folder_name}")

                # 显示创建的文件夹信息
                if 'data' in result:
                    folder_info = result['data']
                    folder_id = folder_info.get('fid', '')
                    if folder_id:
                        print_info(f"文件夹ID: {folder_id}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"创建文件夹失败: {error_msg}")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "创建文件夹")
        raise typer.Exit(1)


def delete_files(paths: List[str], force: bool = False, use_id: bool = False):
    """删除文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 解析路径或使用ID
            if use_id:
                file_ids = paths
                # 显示要删除的文件信息
                print_warning(f"准备删除 {len(file_ids)} 个文件/文件夹:")

                for i, file_id in enumerate(file_ids, 1):
                    try:
                        file_info = client.get_file_info(file_id)
                        file_name = file_info.get('file_name', file_id)
                        file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                        print_info(f"  {i}. {file_type}: {file_name}")
                    except:
                        print_info(f"  {i}. ID: {file_id}")
            else:
                # 使用路径解析
                print_warning(f"准备删除 {len(paths)} 个文件/文件夹:")

                resolved_items = []
                for i, path in enumerate(paths, 1):
                    try:
                        file_id, file_type = client.resolve_path(path)
                        file_info = client.get_file_info(file_id)
                        file_name = file_info.get('file_name', path)
                        type_name = "文件夹" if file_type == 'folder' else "文件"
                        print_info(f"  {i}. {type_name}: {file_name} (路径: {path})")
                        resolved_items.append(file_id)
                    except Exception as e:
                        print_error(f"  {i}. 无法解析路径 '{path}': {e}")
                        raise typer.Exit(1)

                file_ids = resolved_items

            # 确认删除
            if not force:
                if not Confirm.ask("\n确定要删除这些文件/文件夹吗？"):
                    print_info("取消删除操作")
                    return

            print_info("正在删除文件...")

            if use_id:
                result = client.delete_files(file_ids)
            else:
                result = client.delete_files_by_name(paths)

            if result and result.get('status') == 200:
                print_success(f"成功删除 {len(file_ids)} 个文件/文件夹")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"删除失败: {error_msg}")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "删除文件")
        raise typer.Exit(1)


def rename_file(path: str, new_name: str, use_id: bool = False):
    """重命名文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 解析路径或使用ID
            if use_id:
                file_id = path
                try:
                    file_info = client.get_file_info(file_id)
                    old_name = file_info.get('file_name', file_id)
                    file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                    print_info(f"当前{file_type}名称: {old_name}")
                    print_info(f"新{file_type}名称: {new_name}")
                except:
                    print_info(f"文件ID: {file_id}")
                    print_info(f"新名称: {new_name}")

                result = client.rename_file(file_id, new_name)
            else:
                try:
                    file_id, file_type = client.resolve_path(path)
                    file_info = client.get_file_info(file_id)
                    old_name = file_info.get('file_name', path)
                    type_name = "文件夹" if file_type == 'folder' else "文件"
                    print_info(f"当前{type_name}名称: {old_name} (路径: {path})")
                    print_info(f"新{type_name}名称: {new_name}")
                except Exception as e:
                    print_error(f"无法解析路径 '{path}': {e}")
                    raise typer.Exit(1)

                result = client.rename_file_by_name(path, new_name)

            print_info("正在重命名...")

            if result and result.get('status') == 200:
                print_success(f"重命名成功: {new_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"重命名失败: {error_msg}")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "重命名文件")
        raise typer.Exit(1)


def file_info(file_id: str):
    """获取文件详细信息"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在获取文件信息: {file_id}")

            file_info = client.get_file_info(file_id)

            if file_info:
                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(title=f"文件信息")
                table.add_column("属性", style="cyan")
                table.add_column("值", style="white")

                table.add_row("文件名", file_info.get('file_name', '未知'))
                table.add_row("文件ID", file_info.get('fid', '未知'))
                table.add_row("类型", "文件夹" if file_info.get('file_type') == 0 else "文件")
                table.add_row("大小", _format_size(file_info.get('size', 0)))
                table.add_row("格式", file_info.get('format_type', '未知'))
                table.add_row("创建时间", file_info.get('created_at', '未知'))
                table.add_row("修改时间", file_info.get('updated_at', '未知'))

                console.print(table)
            else:
                print_error("无法获取文件信息")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取文件信息")
        raise typer.Exit(1)


def browse_folder(folder_id: str = "0"):
    """交互式文件夹浏览"""
    # TODO: 实现交互式浏览功能
    _ = folder_id  # 参数将在未来实现中使用
    print_warning("交互式浏览功能正在开发中...")
    print_info("请使用 'quarkpan interactive' 启动完整的交互式模式")


def goto_folder(target: str, current_folder: str = "0"):
    """智能进入文件夹"""
    # TODO: 实现智能导航功能
    _ = target, current_folder  # 参数将在未来实现中使用
    print_warning("智能导航功能正在开发中...")
    print_info("请使用 'quarkpan interactive' 启动完整的交互式模式")


def get_download_link(file_id: str):
    """获取文件下载链接"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在获取下载链接: {file_id}")

            download_url = client.get_download_url(file_id)

            if download_url:
                print_success("下载链接获取成功:")
                print_info(download_url)
            else:
                print_error("无法获取下载链接")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取下载链接")
        raise typer.Exit(1)


def _format_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _resolve_folder_path(client, folder_path: str, create_dirs: bool = False) -> str:
    """
    解析文件夹路径到文件夹ID

    Args:
        client: QuarkClient实例
        folder_path: 文件夹路径，如 '/Documents/Photos'
        create_dirs: 是否自动创建不存在的文件夹

    Returns:
        文件夹ID
    """
    from ...services.name_resolver import NameResolver

    resolver = NameResolver(client.files)

    try:
        # 尝试解析路径
        folder_id, file_type = resolver.resolve_path(folder_path)

        if file_type != 'folder':
            raise ValueError(f"路径 '{folder_path}' 不是文件夹")

        return folder_id

    except Exception:
        if not create_dirs:
            raise ValueError(f"文件夹路径不存在: {folder_path}。使用 --create-dirs 自动创建")

        # 自动创建文件夹路径
        return _create_folder_path(client, folder_path)


def _create_folder_path(client, folder_path: str) -> str:
    """
    递归创建文件夹路径

    Args:
        client: QuarkClient实例
        folder_path: 文件夹路径

    Returns:
        最终文件夹ID
    """
    # 处理绝对路径
    if folder_path.startswith('/'):
        current_folder_id = "0"  # 根目录
        folder_path = folder_path[1:]  # 移除开头的/
    else:
        current_folder_id = "0"  # 默认从根目录开始

    # 如果路径为空，返回根目录
    if not folder_path:
        return current_folder_id

    # 分割路径
    parts = [p for p in folder_path.split('/') if p]

    from ...services.name_resolver import NameResolver
    resolver = NameResolver(client.files)

    # 逐级创建文件夹
    for part in parts:
        try:
            # 尝试查找现有文件夹
            current_folder_id = resolver._find_in_folder(part, current_folder_id, 'folder')
        except:
            # 文件夹不存在，创建它
            print_info(f"创建文件夹: {part}")
            result = client.create_folder(part, current_folder_id)

            if result and result.get('status') == 200:
                folder_info = result.get('data', {})
                current_folder_id = folder_info.get('fid', '')
                if not current_folder_id:
                    raise ValueError(f"创建文件夹失败: {part}")
            else:
                error_msg = result.get('message', '未知错误')
                raise ValueError(f"创建文件夹失败: {part} - {error_msg}")

    return current_folder_id


def upload_file(file_path: str, parent_folder_id: str = "0", folder_path: Optional[str] = None, create_dirs: bool = False):
    """上传文件到夸克网盘"""
    from pathlib import Path

    from rich.console import Console
    from rich.progress import (BarColumn, Progress, SpinnerColumn,
                               TaskProgressColumn, TextColumn,
                               TimeRemainingColumn)

    console = Console()

    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            print_error(f"文件不存在: {file_path}")
            raise typer.Exit(1)

        if not file_path_obj.is_file():
            print_error(f"路径不是文件: {file_path}")
            raise typer.Exit(1)

        file_size = file_path_obj.stat().st_size
        print_info(f"上传 {file_path_obj.name} ({_format_size(file_size)})")

        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 处理文件夹路径参数
            if folder_path:
                try:
                    parent_folder_id = _resolve_folder_path(client, folder_path, create_dirs)
                    print_info(f"目标文件夹: {folder_path}")
                except Exception as e:
                    print_error(f"解析文件夹路径失败: {e}")
                    raise typer.Exit(1)

            # 创建进度条
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:

                task = progress.add_task("上传中...", total=100)

                def progress_callback(percent: int, message: str):
                    progress.update(task, completed=percent, description=message)

                # 开始上传（使用绝对路径）
                result = client.upload_file(
                    file_path=str(file_path_obj.resolve()),
                    parent_folder_id=parent_folder_id,
                    progress_callback=progress_callback
                )

            # 上传完成后，在进度条外显示结果
            if result.get('status') == 'success':
                md5_info = f" MD5: {result.get('md5', 'N/A')}" if console.is_terminal else ""
                print_success(f"上传成功{md5_info}")
            else:
                print_error("上传失败")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "上传文件")
        raise typer.Exit(1)
