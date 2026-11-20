# 交互式 Shell 升级为 zsh 式体验 — 实施计划

> 状态：**已实施**（2026-11-20），验证结果见第 9 节
> 目标文件：`quark_client/cli/interactive.py`（单文件改动为主）
> 预计体量：约 150 行新增/修改 + 依赖 1 行 + 帮助文案 5 行

---

## 1. 目标与验收标准

把 `quarkpan interactive` 从「只能一次性输入整行」升级为接近 zsh 的交互体验。

验收标准（逐条可验证）：

1. **方向键**：左右移动光标、上下翻阅历史命令，`Ctrl-A/E`（行首/行尾）可用。
2. **Tab 补全**：补全命令名；补全命令参数（当前目录的文件/文件夹名）；候选以多列菜单展示，右侧带描述。
3. **候选滚动**：候选数超过屏幕高度时菜单自动滚动，选中项始终可见；`MULTI_COLUMN` 下横向列数超出时出现 `<` `>` 滚动箭头。
4. **历史持久化**：重启进程后仍能用上方向键翻到上次的历史；`Ctrl-R` 可反向搜索历史。
5. **带空格的文件名**：补全插入后不会被 `shlex.split` 拆碎（必须 `shlex.quote`）。
6. **`Ctrl-C` / `Ctrl-D` 行为不变**：`Ctrl-C` 中断当前输入但不退出、`Ctrl-D` 退出，与现有行为一致。
7. `flake8`（`--max-line-length=120`）与 `py_compile` 通过。

---

## 2. 已定的决策（不要再改动/重提）

| 决策 | 说明 |
|---|---|
| **用 prompt_toolkit** | 不用裸 readline。理由：多列候选菜单、描述、`Ctrl-R`、滚动都是内置能力 |
| **不做「序号操作」** | 用户明确否掉了 QuarkPan-plus 的 `cd 3` / `download 2` 那套，**不要再提议** |
| **不做 fzf 式全屏选择器** | 属于另一个量级（+100~200 行），本次不做 |
| **不做 aria2 续传** | 用户明确「先别做」 |
| **不动业务逻辑** | 只改 `interactive.py` 的输入层，命令实现一律不改 |
| **不引入 Chromium cookie 读取** | 用户只要 Firefox |

---

## 3. 当前代码现状（改动前必须核对）

提交基线：

```
d5cedbe feat: 默认从 Firefox 读取登录 Cookie，失败再回退二维码登录
b385c05 fix: 绕过下载 23018 大文件限制并支持 aria2
ca311f6 (origin/master)
```

`quark_client/cli/interactive.py`（1057 行）关键位置：

| 位置 | 内容 |
|---|---|
| L1-13 | imports：`os / shlex / typing`、`rich.console.Console`、`rich.panel.Panel`、`rich.prompt.Prompt`、`rich.table.Table` |
| L36-72 | `self.commands` 命令字典（命令名 → 绑定方法），补全的数据源之一 |
| L74-145 | `start()`：主循环，**L104 `command_line = Prompt.ask(prompt).strip()`** 是要替换的那一行 |
| L147-195 | `cmd_help()`：帮助表格，需要补一段快捷键说明 |
| L196 / L253 | `cmd_list()` / `cmd_list_detailed()`：列目录，是文件名的补全数据源 |
| L538 | `_get_display_name()`：把目录名裁短用于 prompt 显示 |
| L594 | `_change_to_directory()`：切换目录（`cd` 成功后需要刷新补全缓存） |
| L1050 | `start_interactive()`：入口函数 |

当前的 prompt 字符串带 rich 标记：

```python
prompt = f"[cyan]quark[/cyan]:[blue]{display_name}[/blue]$ "
command_line = Prompt.ask(prompt).strip()
```

**实测确认的现状**（不要再花时间验证）：

- 进程从未 `import readline`，`'readline' in sys.modules` 为 `False`
- 向 `Prompt.ask()` 发送 `abc` + 左箭头 + `X` + 回车，得到 `'abc\x1b[DX'`，转义序列被原样收起 → **方向键现在完全不可用**
- 本机已装 `prompt_toolkit 3.0.43`，但 `pyproject.toml` 尚未声明

---

## 4. 实施方案

### 4.1 依赖

`pyproject.toml` 的 `dependencies` 增加：

```toml
"prompt_toolkit>=3.0.0",
```

### 4.2 新增 import（注意导入位置，容易踩坑）

```python
import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle   # ⚠️ 在 shortcuts，不在 completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
```

### 4.3 新增模块级常量

```python
# 命令名 -> 描述，补全菜单右侧显示用；与 self.commands 保持同步
COMMAND_DESCRIPTIONS = {
    'help': '显示帮助', 'exit': '退出', 'ls': '列出当前目录',
    'll': '详细列表', 'cd': '切换目录', 'pwd': '显示当前路径',
    'search': '搜索文件', 'download': '下载文件', 'mkdir': '创建文件夹',
    'rm': '删除', 'rename': '重命名', 'info': '查看文件信息',
    'upload': '上传文件', 'share': '创建分享', 'shares': '我的分享',
    'save': '转存分享', 'move': '移动文件', 'batch-share': '批量分享',
    'list-dirs': '目录结构', 'status': '登录状态', 'version': '版本',
    'clear': '清屏',
}
```

### 4.4 新增 `ShellCompleter(Completer)`

职责：根据光标前文本决定补什么。

```python
class ShellCompleter(Completer):
    def __init__(self, shell):
        self.shell = shell      # 反向引用，用于取当前目录条目与命令表

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        ...
```

行为规范：

1. **第一个 token**（还没输入空格）→ 补全命令名，`display_meta` 用 `COMMAND_DESCRIPTIONS`。
2. **第一个 token 已完整输入 + 空格** → 补全参数：
   - 当前目录的**文件夹**名（`display_meta="文件夹"`）
   - 当前目录的**文件**名（`display_meta="文件"`）
3. **`cd` / `move` 的第二个参数** → 只补文件夹。
4. **`download` / `rm` / `info` / `share` 等** → 文件 + 文件夹都补。
5. 所有补全文本必须经过 **`shlex.quote()`**（见 4.6 坑 1）。
6. 前缀匹配大小写不敏感更友好（`str.lower().startswith`）。

### 4.5 条目缓存（补全的数据源）

**不要抄 QuarkPan-plus 的序号缓存设计**（用户不要序号）。这里只需要一份「当前目录最近一次列表结果」，用途仅限补全：

```python
self._dir_entries: List[dict] = []      # [{'file_name':..., 'file_type': 0/1, 'fid':...}, ...]
```

写入点：

- `cmd_list()` 与 `cmd_list_detailed()` 成功取到 `file_list` 后：`self._dir_entries = list(file_list)`
- `_change_to_directory()` 成功后：**清空** `self._dir_entries`（下次 `ls` 再填）。避免 `cd` 后拿旧目录的名字补全。

`cmd_list` 里的 `file_list` 来自 `self.client.list_files(...).get('data', {}).get('list', [])`。

> 注意：这是「补全缓存」，不是「序号缓存」，不暴露给用户，不支持 `cd 3`。

### 4.6 替换主循环的输入层（`start()` 内 L104 附近）

现在：

```python
while self.running:
    try:
        display_name = self._get_display_name(self.current_folder_name)
        prompt = f"[cyan]quark[/cyan]:[blue]{display_name}[/blue]$ "
        command_line = Prompt.ask(prompt).strip()
```

改为（在 `while` **之前**创建 session）：

```python
history_file = get_config_dir() / "shell_history"
session = PromptSession(
    completer=ShellCompleter(self),
    complete_style=CompleteStyle.MULTI_COLUMN,
    reserve_space_for_menu=10,
    history=FileHistory(str(history_file)),
    complete_while_typing=False,
    enable_history_search=False,
)

while self.running:
    try:
        display_name = self._get_display_name(self.current_folder_name)
        prompt = HTML(f"<ansicyan>quark</ansicyan>:<ansiblue>{display_name}</ansiblue>$ ")
        command_line = session.prompt(prompt).strip()
```

要点：

- `HTML()` 需要转义：目录名里可能有 `&`、`<`、`>`。用 `html.escape(display_name)` 或改成 `FormattedText` 碎片列表。
- `complete_while_typing=False` 保持 zsh 默认手感（按 Tab 才弹）；想要边打边提示再设 `True`。
- `enable_history_search=False`：让上下键是「历史整体翻页」而不是前缀匹配；`Ctrl-R` 才是搜索。

### 4.7 `Ctrl-C` / `Ctrl-D` 处理

`session.prompt()` 的行为与 `input()` 不同，必须显式接：

```python
    except KeyboardInterrupt:      # Ctrl-C
        print_info("\n使用 'exit' 退出程序")
        continue                   # 不退出，与现状一致
    except EOFError:               # Ctrl-D
        break
```

现状代码已有这两个 `except`，确认顺序和缩进正确即可。

### 4.8 帮助文案

`cmd_help()` 末尾追加：

```
快捷键:
  Tab          补全命令 / 文件名（多列候选，方向键选择）
  ↑ / ↓        翻阅历史命令
  ← / →        移动光标
  Ctrl-R       搜索历史
  Ctrl-C       中断当前输入（不退出）
  Ctrl-D       退出
```

---

## 5. 坑（按踩中概率排序）

1. **带空格的文件名会被拆碎**
   补全插入 `落幕曲 1.5.4.zip`，`shlex.split()` 得到两个 token，命令报「文件不存在」。
   → 补全的 `text` 一律 `shlex.quote(name)`，即插入 `'落幕曲 1.5.4.zip'`。

2. **`CompleteStyle` 导入位置**
   在 `prompt_toolkit.shortcuts`，不在 `prompt_toolkit.completion`。
   实测报错：`ImportError: cannot import name 'CompleteStyle' from 'prompt_toolkit.completion'`。

3. **rich 与 prompt_toolkit 抢终端**
   普通 `console.print()` 在 prompt 阻塞期间没问题。
   但 `rich.Live` / 进度条 与 prompt_toolkit 渲染冲突，本次不引入这类东西；`upload` 的 tqdm 进度条只在命令执行期间跑，prompt 不在渲染，安全。

4. **`HTML()` 注入**
   目录名含 `&`/`<`/`>` 会让 prompt 渲染异常甚至抛异常，必须 `html.escape()`。

5. **历史文件路径**
   `QuarkClient` **没有** `config_dir` 属性（只有 `QuarkAuth` 有，见 `auth/login.py:34`），
   所以必须自行 `from ..config import get_config_dir` 后调用：
   `history_file = get_config_dir() / "shell_history"`。
   注意 `get_config_dir()` 默认是 `Path.cwd()/config`（见 `quark_client/config.py`），
   会随用户的 `cd` 变化；如需固定位置，可支持 `QUARK_CONFIG_DIR` 环境变量（该函数已支持）。

6. **`PromptSession` 创建时机**
   必须在 `while` 循环**外**创建一次。每次循环新建会丢掉补全状态、且反复读历史文件。

7. **Python 3.8 兼容**
   `pyproject.toml` 声明 `requires-python = ">=3.8"`。
   **不要用** `str | None`、`list[dict]` 这类 3.10+ 语法，用 `Optional[str]`、`List[Dict]`。

---

## 6. 实施顺序

1. `pyproject.toml` 加 `prompt_toolkit>=3.0.0`
2. `interactive.py` 加 imports、`COMMAND_DESCRIPTIONS`、`ShellCompleter`
3. `__init__` 加 `self._dir_entries: List[dict] = []`
4. `cmd_list` / `cmd_list_detailed` 写入 `_dir_entries`
5. `_change_to_directory` 清空 `_dir_entries`
6. `start()` 创建 `PromptSession`，替换 `Prompt.ask`，核对 `Ctrl-C`/`Ctrl-D`
7. `cmd_help` 补快捷键段
8. 自测 + flake8

---

## 7. 验证方式

无法自动化的部分用 pty 脚本验证（前面已用过这种方式）：

```python
# 伪代码
pid, fd = pty.fork()
if pid == 0: os.execvp("python", ["python", "quarkpan interactive"])
# 发 b"abc\x1b[DX\r" -> 若方向键生效，最终命令应是 abXc
```

逐条对第 1 节验收标准打勾。至少验证：

- [x] `abc` + `←` + `X` → 命令为 `abXc`（方向键生效）
- [x] `do` + `Tab` → 补全为 `download`（命令名补全生效）
- [x] `cd ` + `Tab` → 弹出多列目录候选
- [x] 候选超过 10 个 → 菜单滚动，选中项可见
- [x] 文件名带空格 → 补全后能正常执行
- [x] `Ctrl-R` 能搜到上一条历史
- [x] `Ctrl-C` 不退出；`Ctrl-D` 退出
- [x] `flake8 --max-line-length=120 quark_client/cli/interactive.py` 只剩既有的 3 条告警（`F601` ×2 的 `mv` 重复键、`E722` bare except），**不新增**

---

## 8. 提交

```
feat: 交互模式支持方向键、Tab 补全与可滚动候选

- 用 prompt_toolkit 的 PromptSession 替换 rich Prompt.ask，支持行编辑、
  上下键历史与 Ctrl-R 搜索，历史持久化到 config 目录
- 新增 ShellCompleter：补全命令名（带描述）与当前目录文件名/文件夹名，
  多列候选菜单可自动滚动；补全结果经 shlex.quote 转义，兼容带空格的文件名
- ls/ll 缓存当前目录条目供补全使用，cd 后清空避免补全旧目录内容
- cmd_help 补充快捷键说明
```
---

## 9. 实施结果（2026-11-20）

改动文件：

```
pyproject.toml                  |   1 +
quark_client/cli/interactive.py | 180 +++++++++++++++++++--
```

### 落地内容

| 项 | 位置 |
|---|---|
| `COMMAND_DESCRIPTIONS`（命令名 → 描述） | 模块级，与 `InteractiveShell.commands` 对应，含全部别名 |
| `ShellCompleter` | 模块级类，行首补命令、其后补当前目录条目，插入文本经 `shlex.quote` |
| `self._dir_entries` | `__init__` 新增；`cmd_list`（仅当前目录）与 `cmd_list_detailed` 写入；`_change_to_directory` 清空 |
| `PromptSession` | `start()` 循环外创建；`MULTI_COLUMN` + `reserve_space_for_menu=10` + `FileHistory(config/shell_history)` |
| prompt | `HTML()` + `html.escape()` 防注入 |
| `cmd_help` | 新增「快捷键」段 |

### 参数补全的取舍

- `cd` / `ls` / `list` → 只补文件夹（另有 `..`）
- `move` 第一个参数补文件+文件夹，第二个参数只补文件夹
- `rename` 只补第一个参数（第二个是新名字）
- `search` / `find` / `mkdir` / `upload` / `save` / 无参命令 → 不补路径

### 验证记录（pty 驱动真实 PromptSession）

| 用例 | 结果 |
|---|---|
| `abc` + `←` + `X` + Enter | `'abXc'`（方向键生效） |
| `do` + Tab | `'download'` |
| `cd ` + Tab | 屏幕出现 `..`、`文件夹01`、`文件夹02`、`文件夹03` 多列菜单 |
| `cd ` + Tab + Tab + Enter | `'cd ..'`（菜单选择生效） |
| `download 落` + Tab | `"download '落幕曲 1.5.4.zip'"`（空格已转义） |
| 200 个候选 + 连续 ↓×25 | 菜单滚动，渲染窗口随选中项移动 |
| 新进程按 ↑ | 取到上一条历史（`first-cmd`） |
| `Ctrl-R` 后输入 `first` | 命中 `first-cmd` |
| `Ctrl-C` | 打印 INTERRUPT，进程不退出 |
| `Ctrl-D` | 打印 EOF-EXIT，正常退出 |

`flake8 --max-line-length=120` 输出仍是既有的 3 条（`F601` ×2、`E722`），无新增；`py_compile` 通过。

### 已知遗留

- 菜单首行 `..` 与文件夹并列时公共前缀为空，首次 Tab 只弹菜单不插入文本（与 zsh 行为一致），再按一次 Tab 才选中。
- `upload` 的超参是本机路径，未接 `PathCompleter`（本次范围外）。

---

## 10. 补充：首次 Tab 的目录预加载（2026-11-20）

问题：首次进入时未执行过 `ls`，`_dir_entries` 为空，`cd <Tab>` 只能补出 `..`。

改动：

| 新增 | 说明 |
|---|---|
| `prefetch_entries(wait=0.0)` | 后台线程拉取当前目录列表；`wait` 用于首次按 Tab 时短暂等待 |
| `_prefetch_worker(folder_id)` | 线程体，成功/失败都记录 `_entries_for = folder_id`，避免空目录或失败后反复重试 |
| `entries_ready()` / `get_dir_entries()` | 判断缓存是否属于当前目录，别的目录的缓存不会被拿来补全 |
| `_reset_entries()` | `cd`、`cd ..`、`cd` 回根目录后作废缓存并立即重新预加载 |
| `_bottom_toolbar()` | 底部状态栏：未加载时显示「⏳ 正在加载目录…」，否则显示路径 + 条目数 + 快捷键提示 |
| `_invalidate_prompt()` | 后台线程加载完成后调用 `get_app_or_none().invalidate()` 刷新状态栏（线程安全） |

时序：

1. 登录成功 → `prefetch_entries()` 立刻在后台开始拉当前目录
2. 提示「正在后台加载当前目录，完成后 Tab 可补全文件名…」（仅未就绪时）
3. 用户按 Tab 时若仍未就绪 → `prefetch_entries(wait=2.0)` 最多等 2 秒
4. 加载期间切换目录 → worker 结束检查 `current_folder_id`，自动为新目录重新加载

验证：`prefetch_entries()` 后 0.6 秒，`entries_ready()` 为真，`cd <Tab>` 出现 `来自：分享`，`download 落<Tab>` 得到 `'落幕曲 1.5.4.zip'`；切目录后 `entries_ready()` 立即变假并重新加载。

注：底部状态栏在 pty 测试环境下无法验证（终端不响应 CPR，prompt_toolkit 退化为不渲染辅助行），需在真实终端确认。
