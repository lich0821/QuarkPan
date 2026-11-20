"""
交互式CLI模式
"""

import os
import shlex
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .commands.basic_fileops import upload_file
from .commands.batch_share_commands import batch_share, list_structure
from .commands.move_commands import move_files
from .commands.share_commands import create_share, list_my_shares, save_share
from .utils import get_client, print_error, print_info, print_success, print_warning

console = Console()


class InteractiveShell:
    """交互式Shell"""

    def __init__(self):
        self.client = None
        self.current_folder_id = "0"
        self.current_folder_name = "根目录"
        self.running = True

        # 目录栈：存储 (folder_id, folder_name) 的路径
        self.directory_stack = [("0", "根目录")]

        # 命令映射
        self.commands = {
            'help': self.cmd_help,
            'h': self.cmd_help,
            '?': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'q': self.cmd_exit,
            'ls': self.cmd_list,
            'list': self.cmd_list,
            'll': self.cmd_list_detailed,
            'cd': self.cmd_change_dir,
            'pwd': self.cmd_pwd,
            'search': self.cmd_search,
            'find': self.cmd_search,
            'download': self.cmd_download,
            'dl': self.cmd_download,
            'mkdir': self.cmd_mkdir,
            'rm': self.cmd_remove,
            'del': self.cmd_remove,
            'delete': self.cmd_remove,
            'rename': self.cmd_rename,
            'mv': self.cmd_rename,
            'info': self.cmd_info,
            'clear': self.cmd_clear,
            'cls': self.cmd_clear,
            'upload': self.cmd_upload,
            'up': self.cmd_upload,
            'share': self.cmd_share,
            'shares': self.cmd_shares,
            'move': self.cmd_move,
            'mv': self.cmd_move,
            'batch-share': self.cmd_batch_share,
            'list-dirs': self.cmd_list_dirs,
            'save': self.cmd_save,
            'status': self.cmd_status,
            'version': self.cmd_version,
        }

    def start(self):
        """启动交互式模式"""
        console.print(Panel.fit(
            "[bold cyan]🌟 夸克网盘交互式CLI[/bold cyan]\n"
            "输入 'help' 查看可用命令\n"
            "输入 'exit' 退出程序",
            title="欢迎使用",
            border_style="cyan"
        ))

        # 检查登录状态
        try:
            self.client = get_client().__enter__()
            if not self.client.is_logged_in():
                print_error("未登录，请先使用 'quarkpan auth login' 登录")
                return

            print_success("已登录夸克网盘")
            print_info(f"当前位置: {self.current_folder_name}")

        except Exception as e:
            print_error(f"初始化失败: {e}")
            return

        # 主循环
        while self.running:
            try:
                # 显示提示符 - 使用友好显示名称
                display_name = self._get_display_name(self.current_folder_name)
                prompt = f"[cyan]quark[/cyan]:[blue]{display_name}[/blue]$ "
                command_line = Prompt.ask(prompt).strip()

                if not command_line:
                    continue

                # 解析命令
                try:
                    args = shlex.split(command_line)
                except ValueError as e:
                    print_error(f"命令解析错误: {e}")
                    continue

                if not args:
                    continue

                cmd = args[0].lower()
                cmd_args = args[1:]

                # 执行命令
                if cmd in self.commands:
                    try:
                        self.commands[cmd](cmd_args)
                    except KeyboardInterrupt:
                        print_info("\n命令被中断")
                    except Exception as e:
                        print_error(f"命令执行错误: {e}")
                else:
                    print_error(f"未知命令: {cmd}，输入 'help' 查看可用命令")

            except KeyboardInterrupt:
                print_info("\n使用 'exit' 退出程序")
            except EOFError:
                break

        # 清理
        try:
            if self.client:
                self.client.__exit__(None, None, None)
        except:
            pass

        print_info("再见！")

    def cmd_help(self, args: List[str]):
        """显示帮助信息"""
        table = Table(title="可用命令", show_header=True, header_style="bold magenta")
        table.add_column("命令", style="cyan", width=15)
        table.add_column("别名", style="dim", width=10)
        table.add_column("说明", style="white")

        commands_help = [
            ("help", "h, ?", "显示此帮助信息"),
            ("exit", "quit, q", "退出程序"),
            ("ls", "list", "列出当前目录文件"),
            ("ll", "", "详细列出当前目录文件"),
            ("cd <path>", "", "切换目录"),
            ("cd ..", "", "返回上级目录"),
            ("cd", "", "返回根目录"),
            ("pwd", "", "显示当前目录和路径"),
            ("search <keyword>", "find", "搜索文件"),
            ("download <path>", "dl", "下载文件"),
            ("mkdir <name>", "", "创建文件夹"),
            ("rm <path>...", "del", "删除文件/文件夹"),
            ("rename <old> <new>", "mv", "重命名文件/文件夹"),
            ("info <path>", "", "显示文件信息"),
            ("upload <file>", "up", "上传文件到当前目录"),
            ("share <path>", "", "创建分享链接"),
            ("shares", "", "查看我的分享列表"),
            ("save <url>", "", "转存分享文件"),
            ("move <src> <dst>", "mv", "移动文件到目标文件夹"),
            ("batch-share", "", "批量分享目录"),
            ("list-dirs", "", "查看目录结构"),
            ("status", "", "显示登录状态和存储信息"),
            ("version", "", "显示版本信息"),
            ("clear", "cls", "清屏"),
        ]

        for cmd, alias, desc in commands_help:
            table.add_row(cmd, alias, desc)

        console.print(table)

        console.print("\n[bold yellow]路径说明:[/bold yellow]")
        console.print("• 使用文件名: [cyan]文件.txt[/cyan]")
        console.print("• 使用相对路径: [cyan]文件夹/文件.txt[/cyan]")
        console.print("• 使用绝对路径: [cyan]/文件夹/文件.txt[/cyan]")
        console.print("• 文件夹路径末尾加/: [cyan]文件夹/[/cyan]")

    def cmd_exit(self, args: List[str]):
        """退出程序"""
        self.running = False

    def cmd_list(self, args: List[str]):
        """列出文件"""
        try:
            # 确定要列出的目录
            target_folder_id = self.current_folder_id
            target_folder_name = self.current_folder_name

            # 如果提供了路径参数，解析路径
            if args:
                path = args[0]
                from ..services.batch_share_service import BatchShareService
                batch_service = BatchShareService(self.client.api_client)

                resolved_folder_id = batch_service._resolve_path_to_folder_id(path)
                if not resolved_folder_id:
                    print_error(f"路径不存在: {path}")
                    return

                target_folder_id = resolved_folder_id
                # 获取目标目录名称
                if path == "/" or path == "":
                    target_folder_name = "根目录"
                else:
                    # 从路径中提取目录名
                    path_clean = path.strip('/')
                    if path_clean:
                        target_folder_name = path_clean.split('/')[-1]
                    else:
                        target_folder_name = "根目录"

            # 列出目标目录的文件
            files = self.client.list_files(target_folder_id, size=50)  # type: ignore[attr-defined]
            file_list = files.get('data', {}).get('list', [])

            if not file_list:
                print_info("目录为空")
                return

            # 显示目录信息 - 使用友好显示名称
            display_name = self._get_display_name(target_folder_name, max_length=50)
            print_info(f"目录: {display_name}")
            print_info(f"共 {len(file_list)} 个项目\n")

            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)

                if file_type == 0:  # 文件夹
                    console.print(f"  {i:2d}. 📁 {name}/")
                else:  # 文件
                    size = file_info.get('size', 0)
                    size_str = self._format_size(size)
                    console.print(f"  {i:2d}. 📄 {name} [dim]({size_str})[/dim]")

        except Exception as e:
            print_error(f"列出文件失败: {e}")

    def cmd_list_detailed(self, args: List[str]):
        """详细列出文件"""
        try:
            files = self.client.list_files(self.current_folder_id, size=50)  # type: ignore[attr-defined]
            file_list = files.get('data', {}).get('list', [])

            if not file_list:
                print_info("目录为空")
                return

            # 使用友好显示名称作为表格标题
            display_name = self._get_display_name(self.current_folder_name, max_length=30)
            table = Table(title=f"目录内容: {display_name}")
            table.add_column("序号", style="dim", width=4)
            table.add_column("类型", style="cyan", width=4)
            table.add_column("名称", style="white")
            table.add_column("大小", style="green", width=10)

            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)
                size = file_info.get('size', 0)

                if file_type == 0:
                    table.add_row(str(i), "📁", f"{name}/", "-")
                else:
                    size_str = self._format_size(size)
                    table.add_row(str(i), "📄", name, size_str)

            console.print(table)

        except Exception as e:
            print_error(f"列出文件失败: {e}")

    def cmd_change_dir(self, args: List[str]):
        """切换目录"""
        if not args:
            # 回到根目录
            self._change_to_root()
            return

        path = args[0]

        try:
            if path == "..":
                # 返回上级目录
                self._change_to_parent()
                return

            file_id, file_type = self.client.resolve_path(path, self.current_folder_id)  # type: ignore[attr-defined]

            if file_type != 'folder':
                print_error(f"'{path}' 不是文件夹")
                return

            # 获取文件夹的真实名称（优先使用列表缓存中的名称）
            real_name = self.client.get_real_file_name(file_id)  # type: ignore[attr-defined]
            if real_name:
                folder_name = real_name
            else:
                # 如果缓存中没有，则使用API获取的名称
                folder_info = self.client.get_file_info(file_id)  # type: ignore[attr-defined]
                folder_name = folder_info.get('file_name', path)

            # 切换到新目录
            self._change_to_directory(file_id, folder_name)

        except Exception as e:
            print_error(f"切换目录失败: {e}")

    def cmd_pwd(self, args: List[str]):
        """显示当前目录"""
        display_name = self._get_display_name(self.current_folder_name, max_length=50)
        current_path = self._get_current_path()

        print_info(f"当前目录: {display_name}")
        print_info(f"完整路径: {current_path}")
        if len(self.current_folder_name) > 50:
            print_info(f"完整名称: {self.current_folder_name}")
        print_info(f"目录ID: {self.current_folder_id}")
        print_info(f"目录层级: {len(self.directory_stack) - 1}")

    def cmd_search(self, args: List[str]):
        """搜索文件"""
        if not args:
            print_error("请提供搜索关键词")
            return

        keyword = " ".join(args)
        print_info(f"搜索: {keyword}")

        try:
            # 简化的搜索实现
            results = self.client.search_files(keyword, size=20)  # type: ignore[attr-defined]
            file_list = results.get('data', {}).get('list', [])
            total = results.get('metadata', {}).get('_total', len(file_list))

            if not file_list:
                print_warning("没有找到匹配的文件")
                return

            print_success(f"找到 {total} 个结果（显示前20个）:")

            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)
                size = file_info.get('size', 0)

                if file_type == 0:
                    console.print(f"  {i:2d}. 📁 {name}/")
                else:
                    size_str = self._format_size(size)
                    console.print(f"  {i:2d}. 📄 {name} [dim]({size_str})[/dim]")

        except Exception as e:
            print_error(f"搜索失败: {e}")

    def cmd_download(self, args: List[str]):
        """下载文件"""
        if not args:
            print_error("请提供要下载的文件路径")
            return

        # 支持 download <path> [--aria2] [-x N]
        use_aria2 = False
        connections = 16
        paths: List[str] = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ('--aria2', '-a'):
                use_aria2 = True
            elif arg in ('-x', '--connections') and i + 1 < len(args):
                try:
                    connections = int(args[i + 1])
                except ValueError:
                    print_error(f"无效的连接数: {args[i + 1]}")
                    return
                i += 1
            else:
                paths.append(arg)
            i += 1

        if not paths:
            print_error("请提供要下载的文件路径")
            return

        path = paths[0]

        try:
            print_info(f"准备下载: {path}")
            if use_aria2:
                print_info(f"⚡ 使用 aria2c 下载（{connections} 连接）")

            def progress_callback(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    print(f"\r下载进度: {percent:.1f}%", end="", flush=True)

            downloaded_path = self.client.download_file_by_name(  # type: ignore[attr-defined]
                path,
                current_folder_id=self.current_folder_id,
                progress_callback=progress_callback,
                downloader='aria2' if use_aria2 else 'native',
                aria2_options={'connections': connections, 'split': connections}
            )

            print()  # 换行
            print_success(f"下载完成: {downloaded_path}")

        except Exception as e:
            print()  # 换行
            print_error(f"下载失败: {e}")

    def cmd_mkdir(self, args: List[str]):
        """创建文件夹"""
        if not args:
            print_error("请提供文件夹名称")
            return

        folder_name = args[0]

        try:
            result = self.client.create_folder(folder_name, self.current_folder_id)  # type: ignore[attr-defined]

            if result and result.get('status') == 200:
                print_success(f"文件夹创建成功: {folder_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"创建文件夹失败: {error_msg}")

        except Exception as e:
            print_error(f"创建文件夹失败: {e}")

    def cmd_remove(self, args: List[str]):
        """删除文件"""
        if not args:
            print_error("请提供要删除的文件路径")
            return

        try:
            print_warning(f"准备删除 {len(args)} 个文件/文件夹:")

            for i, path in enumerate(args, 1):
                print_info(f"  {i}. {path}")

            from rich.prompt import Confirm
            if not Confirm.ask("\n确定要删除这些文件/文件夹吗？"):
                print_info("取消删除操作")
                return

            result = self.client.delete_files_by_name(args, self.current_folder_id)  # type: ignore[attr-defined]

            if result and result.get('status') == 200:
                print_success(f"成功删除 {len(args)} 个文件/文件夹")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"删除失败: {error_msg}")

        except Exception as e:
            print_error(f"删除失败: {e}")

    def cmd_rename(self, args: List[str]):
        """重命名文件"""
        if len(args) < 2:
            print_error("请提供原文件名和新文件名")
            return

        old_path = args[0]
        new_name = args[1]

        try:
            result = self.client.rename_file_by_name(  # type: ignore[attr-defined]
                old_path, new_name, self.current_folder_id)

            if result and result.get('status') == 200:
                print_success(f"重命名成功: {old_path} -> {new_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"重命名失败: {error_msg}")

        except Exception as e:
            print_error(f"重命名失败: {e}")

    def cmd_info(self, args: List[str]):
        """显示文件信息"""
        if not args:
            print_error("请提供文件路径")
            return

        path = args[0]

        try:
            file_info = self.client.get_file_info_by_name(path, self.current_folder_id)  # type: ignore[attr-defined]

            table = Table(title=f"文件信息: {path}")
            table.add_column("属性", style="cyan")
            table.add_column("值", style="white")

            table.add_row("文件名", file_info.get('file_name', '未知'))
            table.add_row("文件ID", file_info.get('fid', '未知'))
            table.add_row("类型", "文件夹" if file_info.get('file_type') == 0 else "文件")
            table.add_row("大小", self._format_size(file_info.get('size', 0)))
            table.add_row("格式", file_info.get('format_type', '未知'))

            console.print(table)

        except Exception as e:
            print_error(f"获取文件信息失败: {e}")

    def cmd_clear(self, args: List[str]):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _get_display_name(self, folder_name: str, max_length: int = 20) -> str:
        """
        获取友好显示的文件夹名称

        Args:
            folder_name: 原始文件夹名称
            max_length: 最大显示长度

        Returns:
            友好显示的名称
        """
        if not folder_name or folder_name == "根目录":
            return "根目录"

        # 如果名称不太长，直接返回
        if len(folder_name) <= max_length:
            return folder_name

        # 对于长名称，进行智能截断
        # 优先保留开头和结尾的重要信息
        if len(folder_name) > max_length:
            # 计算截断位置
            start_len = max_length // 2 - 1
            end_len = max_length - start_len - 3  # 3个字符用于"..."

            if start_len > 0 and end_len > 0:
                return f"{folder_name[:start_len]}...{folder_name[-end_len:]}"
            else:
                # 如果太短，直接截断
                return f"{folder_name[:max_length-3]}..."

        return folder_name

    def _change_to_root(self):
        """切换到根目录"""
        self.current_folder_id = "0"
        self.current_folder_name = "根目录"
        self.directory_stack = [("0", "根目录")]
        print_info("已切换到根目录")

    def _change_to_parent(self):
        """返回上级目录"""
        if len(self.directory_stack) <= 1:
            print_warning("已经在根目录，无法返回上级目录")
            return

        # 弹出当前目录，返回上级
        self.directory_stack.pop()
        parent_id, parent_name = self.directory_stack[-1]

        self.current_folder_id = parent_id
        self.current_folder_name = parent_name

        display_name = self._get_display_name(parent_name)
        print_success(f"已返回上级目录: {display_name}")

    def _change_to_directory(self, folder_id: str, folder_name: str):
        """切换到指定目录"""
        # 添加到目录栈
        self.directory_stack.append((folder_id, folder_name))

        # 更新当前目录
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name

        # 显示切换成功信息
        display_name = self._get_display_name(folder_name)
        print_success(f"已切换到: {display_name}")

    def _get_current_path(self) -> str:
        """获取当前路径字符串"""
        if len(self.directory_stack) <= 1:
            return "/"

        path_parts = []
        for _, name in self.directory_stack[1:]:  # 跳过根目录
            path_parts.append(name)

        return "/" + "/".join(path_parts)

    def cmd_upload(self, args: List[str]):
        """上传文件"""
        if not args:
            print_error("用法: upload <本地文件路径>")
            print_info("示例: upload /path/to/file.txt")
            return

        local_file_path = args[0]

        # 检查文件是否存在
        if not os.path.exists(local_file_path):
            print_error(f"文件不存在: {local_file_path}")
            return

        if not os.path.isfile(local_file_path):
            print_error(f"路径不是文件: {local_file_path}")
            return

        try:
            print_info(f"上传文件到当前目录: {self.current_folder_name}")

            # 调用上传函数，上传到当前目录
            upload_file(
                file_path=local_file_path,
                parent_folder_id=self.current_folder_id,
                folder_path=None,
                create_dirs=False
            )

        except Exception as e:
            print_error(f"上传失败: {e}")

    def cmd_share(self, args: List[str]):
        """创建分享链接"""
        if not args:
            print_error("用法: share <文件/文件夹路径> [选项]")
            print_info("示例: share 文件.txt")
            print_info("示例: share 文件夹/")
            print_info("选项:")
            print_info("  --title <标题>     设置分享标题")
            print_info("  --password <密码>  设置提取码")
            print_info("  --expire <天数>    设置过期天数(0=永久)")
            return

        file_path = args[0]

        # 解析选项
        title = ""
        password = None
        expire_days = 0

        i = 1
        while i < len(args):
            if args[i] == "--title" and i + 1 < len(args):
                title = args[i + 1]
                i += 2
            elif args[i] == "--password" and i + 1 < len(args):
                password = args[i + 1]
                i += 2
            elif args[i] == "--expire" and i + 1 < len(args):
                try:
                    expire_days = int(args[i + 1])
                except ValueError:
                    print_error("过期天数必须是数字")
                    return
                i += 2
            else:
                i += 1

        try:
            # 解析文件路径到文件ID
            file_id = self._resolve_path_to_id(file_path)
            if not file_id:
                print_error(f"无法找到文件: {file_path}")
                return

            print_info("创建分享链接...")

            # 调用分享函数
            create_share(
                file_paths=[file_id],
                title=title,
                expire_days=expire_days,
                password=password,
                use_id=True
            )

        except Exception as e:
            print_error(f"创建分享失败: {e}")

    def cmd_shares(self, args: List[str]):
        """查看我的分享列表"""
        # 解析参数
        page = 1
        size = 20

        i = 0
        while i < len(args):
            if args[i] == "--page" and i + 1 < len(args):
                try:
                    page = int(args[i + 1])
                except ValueError:
                    print_error("页码必须是数字")
                    return
                i += 2
            elif args[i] == "--size" and i + 1 < len(args):
                try:
                    size = int(args[i + 1])
                except ValueError:
                    print_error("每页数量必须是数字")
                    return
                i += 2
            else:
                i += 1

        try:
            print_info("获取分享列表...")

            # 调用分享列表函数
            list_my_shares(page=page, size=size)

        except Exception as e:
            print_error(f"获取分享列表失败: {e}")

    def cmd_move(self, args: List[str]):
        """移动文件"""
        if len(args) < 2:
            print_error("用法: move <源文件路径> <目标文件夹路径>")
            print_info("示例: move file.txt Documents/")
            print_info("示例: mv folder1/ folder2/")
            return

        source_path = args[0]
        target_path = args[1]

        try:
            # 解析源文件路径到文件ID
            source_file_id = self._resolve_path_to_id(source_path)
            if not source_file_id:
                print_error(f"无法找到源文件: {source_path}")
                return

            # 解析目标文件夹路径到文件夹ID
            target_folder_id = self._resolve_path_to_id(target_path)
            if not target_folder_id:
                print_error(f"无法找到目标文件夹: {target_path}")
                return

            # 检查目标是否为文件夹
            try:
                from ..services.name_resolver import NameResolver
                resolver = NameResolver(self.client.files)  # type: ignore[attr-defined]

                # 获取目标文件信息
                if target_path.startswith('/'):
                    _, target_info = resolver.resolve_path(target_path)
                else:
                    # 相对路径，从当前目录开始解析
                    if self.current_folder_id == "0":
                        full_path = f"/{target_path}"
                    else:
                        current_path = self._get_current_path()
                        full_path = f"{current_path}/{target_path}".replace("//", "/")
                    _, target_info = resolver.resolve_path(full_path)

                if not target_info.get('dir', False):  # type: ignore[attr-defined]
                    print_error(f"目标不是文件夹: {target_path}")
                    return

            except Exception as e:
                print_error(f"无法验证目标文件夹: {e}")
                return

            print_info(f"移动 '{source_path}' 到 '{target_path}'...")

            # 调用移动函数
            move_files(
                source_paths=[source_file_id],
                target_path=target_folder_id,
                use_id=True
            )

        except Exception as e:
            print_error(f"移动文件失败: {e}")

    def _resolve_path_to_id(self, path: str) -> Optional[str]:
        """解析路径到文件ID"""
        try:
            from ..services.name_resolver import NameResolver
            resolver = NameResolver(self.client.files)  # type: ignore[attr-defined]

            # 如果是绝对路径，从根目录开始解析
            if path.startswith('/'):
                file_id, _ = resolver.resolve_path(path)
            else:
                # 相对路径，从当前目录开始解析
                if self.current_folder_id == "0":
                    # 在根目录
                    file_id, _ = resolver.resolve_path(f"/{path}")
                else:
                    # 在子目录，需要构造完整路径
                    current_path = self._get_current_path()
                    full_path = f"{current_path}/{path}".replace("//", "/")
                    file_id, _ = resolver.resolve_path(full_path)

            return file_id
        except Exception:
            return None

    def cmd_batch_share(self, args: List[str]):
        """批量分享目录/文件功能"""
        print_info("批量分享功能")

        # 解析参数
        output = None
        exclude = ["来自：分享"]
        dry_run = False
        target_dir = None
        depth = 3
        share_level = "folders"

        i = 0
        while i < len(args):
            if args[i] == "--output" or args[i] == "-o":
                if i + 1 < len(args):
                    output = args[i + 1]
                    i += 2
                else:
                    print_error("--output 需要一个参数")
                    return
            elif args[i] == "--exclude" or args[i] == "-e":
                if i + 1 < len(args):
                    exclude = [args[i + 1]]
                    i += 2
                else:
                    print_error("--exclude 需要一个参数")
                    return
            elif args[i] == "--dry-run":
                dry_run = True
                i += 1
            elif args[i] == "--target-dir" or args[i] == "-t":
                if i + 1 < len(args):
                    target_dir = args[i + 1]
                    i += 2
                else:
                    print_error("--target-dir 需要一个参数")
                    return
            elif args[i] == "--depth" or args[i] == "-d":
                if i + 1 < len(args):
                    try:
                        depth = int(args[i + 1])
                    except ValueError:
                        print_error("--depth 必须是数字")
                        return
                    i += 2
                else:
                    print_error("--depth 需要一个参数")
                    return
            elif args[i] == "--share-level" or args[i] == "-l":
                if i + 1 < len(args):
                    if args[i + 1] in ["folders", "files", "both"]:
                        share_level = args[i + 1]
                    else:
                        print_error("--share-level 必须是 folders, files 或 both")
                        return
                    i += 2
                else:
                    print_error("--share-level 需要一个参数")
                    return
            elif args[i] == "--help" or args[i] == "-h":
                print_info("批量分享命令帮助：")
                print_info("用法: batch-share [选项]")
                print_info("选项:")
                print_info("  --output, -o <文件名>     CSV输出文件名")
                print_info("  --exclude, -e <模式>      排除的目录名称模式")
                print_info("  --dry-run                 只扫描，不创建分享")
                print_info("  --target-dir, -t <路径>   指定起始目录路径")
                print_info("  --depth, -d <数字>        扫描深度层级（默认3）")
                print_info("  --share-level, -l <类型>  分享类型: folders/files/both")
                print_info("")
                print_info("示例:")
                print_info("  batch-share                                    # 默认模式")
                print_info("  batch-share --target-dir \"/我的资料\"          # 指定目录")
                print_info("  batch-share --depth 2 --share-level both     # 2级深度，文件+文件夹")
                return
            else:
                i += 1

        try:
            # 调用批量分享函数
            batch_share(output=output, exclude=exclude, dry_run=dry_run,
                        target_dir=target_dir, depth=depth, share_level=share_level)
        except Exception as e:
            print_error(f"批量分享失败: {e}")

    def cmd_list_dirs(self, args: List[str]):
        """查看网盘目录结构"""
        print_info("查看目录结构")

        # 解析参数
        level = 3
        exclude = ["来自：分享"]

        i = 0
        while i < len(args):
            if args[i] == "--level" or args[i] == "-l":
                if i + 1 < len(args):
                    try:
                        level = int(args[i + 1])
                    except ValueError:
                        print_error("level必须是数字")
                        return
                    i += 2
                else:
                    print_error("--level 需要一个参数")
                    return
            elif args[i] == "--exclude" or args[i] == "-e":
                if i + 1 < len(args):
                    exclude = [args[i + 1]]
                    i += 2
                else:
                    print_error("--exclude 需要一个参数")
                    return
            else:
                i += 1

        try:
            # 调用目录结构查看函数
            list_structure(level=level, exclude=exclude)
        except Exception as e:
            print_error(f"查看目录结构失败: {e}")

    def cmd_save(self, args: List[str]):
        """转存分享文件"""
        if not args:
            print_error("用法: save <分享链接> [选项]")
            print_info("示例: save https://pan.quark.cn/s/abc123")
            print_info("选项:")
            print_info("  --folder <路径>    目标文件夹路径 (默认: /)")
            print_info("  --no-create-folder 不自动创建目标文件夹")
            return

        share_url = args[0]
        target_folder = "/来自：分享/"
        create_folder = True

        # 解析选项
        i = 1
        while i < len(args):
            if args[i] == "--folder" and i + 1 < len(args):
                target_folder = args[i + 1]
                i += 2
            elif args[i] == "--no-create-folder":
                create_folder = False
                i += 1
            else:
                i += 1

        try:
            print_info(f"转存分享文件到: {target_folder}")

            # 调用转存分享函数
            save_share(
                share_url=share_url,
                target_folder=target_folder,
                create_folder=create_folder
            )

        except Exception as e:
            print_error(f"转存分享失败: {e}")

    def cmd_status(self, args: List[str]):
        """显示登录状态和存储信息"""
        try:
            # 检查登录状态
            if not self.client.is_logged_in():  # type: ignore[attr-defined]
                print_error("❌ 未登录")
                print_info("请使用 'quarkpan auth login' 登录")
                return

            print_success("已登录")

            # 获取存储信息
            try:
                storage = self.client.get_storage_info()  # type: ignore[attr-defined]
                if storage and 'data' in storage:
                    data = storage['data']
                    total = data.get('total', 0)
                    used = data.get('used', 0)
                    free = total - used

                    # 创建存储信息表格
                    from rich.table import Table
                    table = Table(title="💾 存储空间信息")
                    table.add_column("项目", style="cyan")
                    table.add_column("大小", style="green")
                    table.add_column("百分比", style="yellow")

                    usage_percent = (used / total * 100) if total > 0 else 0

                    table.add_row("总容量", self._format_size(total), "100%")
                    table.add_row("已使用", self._format_size(used), f"{usage_percent:.1f}%")
                    table.add_row("剩余", self._format_size(free), f"{100-usage_percent:.1f}%")

                    console.print(table)
                else:
                    print_warning("⚠️ 无法获取存储信息")
            except Exception as e:
                print_warning(f"⚠️ 获取存储信息失败: {e}")

            # 获取当前目录文件数量
            try:
                files = self.client.list_files(self.current_folder_id, size=1)  # type: ignore[attr-defined]
                if files and 'data' in files:
                    total_files = files['data'].get('total', 0)
                    display_name = self._get_display_name(self.current_folder_name)
                    print_info(f"📂 当前目录 ({display_name}) 文件数量: {total_files}")
                else:
                    print_warning("⚠️ 无法获取文件信息")
            except Exception as e:
                print_warning(f"⚠️ 获取文件信息失败: {e}")

        except Exception as e:
            print_error(f"❌ 错误: {e}")

    def cmd_version(self, args: List[str]):
        """显示版本信息"""
        from rich import print as rprint
        rprint("[bold blue]QuarkPan CLI[/bold blue] [green]v1.0.0[/green]")
        rprint("夸克网盘命令行工具 - 交互模式")


def start_interactive():
    """启动交互式模式"""
    shell = InteractiveShell()
    shell.start()


if __name__ == "__main__":
    start_interactive()
