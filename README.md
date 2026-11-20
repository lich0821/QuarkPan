# QuarkPan - 夸克网盘 Python 客户端

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyPi](https://img.shields.io/pypi/v/quarkpan.svg)](https://pypi.python.org/pypi/quarkpan)

一个功能完整的夸克网盘 Python API 客户端和命令行工具，支持文件管理、上传下载、分享转存等核心功能。提供简洁的 Python API 接口和强大的命令行工具，满足自动化脚本和日常使用需求。

发送 `WCF` 进入社区交流，获取更多资源：
<center>

![公众号搜索【漩智】加入社区](QrCode.jpg)
</center>

## ✨ 主要功能

### 🔐 登录认证
- **API 二维码登录**: 通过官方 API 获取二维码，手机扫码安全登录
- **手动 Cookie 登录**: 支持手动输入 Cookie 的备用登录方式  
- **自动登录状态检查**: 智能检测登录状态，避免重复认证
- **安全 Cookie 管理**: 加密存储登录凭证，支持自动刷新

### 📁 文件管理
- **文件夹浏览**: 递归浏览文件夹，支持分页和路径导航
- **文件搜索**: 全盘关键词搜索，支持文件名和内容匹配
- **文件操作**: 创建、删除、重命名、移动文件和文件夹
- **批量操作**: 支持批量选择和处理多个文件
- **存储信息**: 实时查看网盘容量使用情况

### 📤 上传下载  
- **文件上传**: 支持单文件和文件夹上传，自动处理大文件分片
- **下载链接**: 获取文件直接下载地址，支持外部下载工具
- **进度显示**: 实时显示上传下载进度和速度
- **断点续传**: 支持大文件的断点续传功能

### 🔗 分享功能
- **创建分享**: 为文件 / 文件夹创建分享链接，支持密码和有效期设置
- **分享管理**: 查看、编辑、删除自己的分享记录
- **分享转存**: 将他人分享的资源一键转存到自己网盘
- **链接解析**: 智能识别和解析各种格式的分享链接
- **批量转存**: 支持批量转存多个分享链接到指定目录
- **自动化转存**: 基于请求序列分析的高效转存实现

### 🖥️ 命令行工具
- **交互式界面**: 提供类似文件管理器的交互式命令行界面  
- **丰富命令集**: 涵盖所有网盘操作的完整命令集合
- **美观输出**: 使用 Rich 库提供彩色和格式化的终端输出
- **批量脚本**: 支持批量操作脚本和自动化任务

## 🚀 快速开始

### 安装
#### 方法一：直接安装
```sh
pip install quarkpan
```

#### 方法二：从源码安装
```bash
# 克隆项目
git clone https://github.com/lich0821/QuarkPan.git
cd QuarkPan

# 安装依赖
pip install -r requirements.txt

# 开发模式安装（可选）
pip install -e .
```

#### 方法三：直接使用
```bash
# 克隆后直接运行
git clone https://github.com/lich0821/QuarkPan.git
cd QuarkPan
pip install -r requirements.txt

# 三种运行方式任选其一：
# 1. 使用 Python 模块方式
python -m quark_client.cli --help

# 2. 直接运行 CLI 脚本
python cli.py --help

# 3. 安装后使用命令行工具（需要先运行 pip install -e .）
# quarkpan --help
```

### 快速体验

#### 🌟 推荐：交互模式（一键启动）
```bash
# 🎯 最简单：直接运行自动进入交互模式
quarkpan

# 等效命令（明确指定交互模式）
quarkpan interactive

# 使用Python模块方式
python -m quark_client.cli.main
```

#### 1. 首次登录
```bash
# 🎯 最简单：直接运行（自动进入交互模式，引导完成登录）
quarkpan

# 或者直接使用登录命令
quarkpan auth login

# Python模块方式
python -m quark_client.cli.main
```

#### 2. Python API 快速上手
```python
from quark_client import QuarkClient

# 创建客户端（首次使用会自动引导登录）
with QuarkClient() as client:
    # 检查登录状态
    if not client.is_logged_in():
        client.login()  # 自动打开二维码登录

    # 获取根目录文件列表
    files = client.list_files()
    print(f"找到 {len(files['data']['list'])} 个文件")

    # 搜索文件
    results = client.search_files("重要文档")

    # 获取存储信息
    storage = client.get_storage_info()
    print(f"已使用: {storage['data']['used'] / (1024**3):.2f} GB")
```

## 📖 详细使用说明

### Python API 使用

#### 基础文件操作
```python
from quark_client import QuarkClient

with QuarkClient() as client:
    # 文件列表获取
    files = client.list_files(folder_id="0", page=1, size=50)

    # 创建文件夹
    result = client.files.create_folder("新文件夹", parent_id="0")

    # 删除文件（支持批量）
    result = client.files.delete_files(["file_id_1", "file_id_2"])

    # 重命名文件
    result = client.files.rename_file("file_id", "新名称")

    # 移动文件（支持批量）
    result = client.files.move_files(["file_id"], "target_folder_id")

    # 搜索文件
    results = client.search_files("关键词", size=20)
```

#### 上传下载操作
```python
# 上传文件
result = client.upload.upload_file("本地文件.txt", parent_folder_id="0")

# 获取下载链接  
download_info = client.download.get_download_url("file_id")
download_url = download_info['download_url']

# 获取存储信息
storage = client.get_storage_info()
total_gb = storage['data']['total'] / (1024**3)
used_gb = storage['data']['used'] / (1024**3)
```

#### 分享管理
```python
# 创建分享链接
share = client.shares.create_share(
    file_ids=["file_id_1", "file_id_2"],
    title="我的分享",
    expire_days=7,
    password="1234"
)

# 获取我的分享列表
my_shares = client.shares.get_my_shares(page=1, size=20)

# 转存他人分享的文件
result = client.shares.save_shared_files(
    share_url="https://pan.quark.cn/s/abc123",
    password="1234",
    target_folder_id="0"
)

# 解析分享链接
share_id, password = client.shares.parse_share_url(
    "https://pan.quark.cn/s/abc123 密码: 1234"
)
```

### 命令行使用

> **说明**: 以下所有命令都提供两种运行方式：
> - `python -m quark_client.cli <command>` （模块方式）
> - `python cli.py <command>` （脚本方式）  
> - `quarkpan <command>` （安装后，需要先运行 `pip install -e .`）

#### 交互式模式（推荐新用户）
```bash  
# 🎯 最简单：直接启动（默认进入交互模式）
quarkpan

# 传统方式（等效）
python -m quark_client.cli interactive
# 或
python cli.py interactive

# 交互式界面提供类似文件管理器的体验：
# - 使用方向键浏览文件和文件夹
# - 按 Enter 进入文件夹或执行操作
# - 按 Tab 查看可用操作
# - 按 q 退出当前界面
```

#### 认证管理
```bash
# 🎯 最简单：直接运行（自动引导登录）
quarkpan

# API 二维码登录（直接命令）
quarkpan auth login

# 手动 Cookie 登录
quarkpan auth login --method simple

# 查看登录状态
quarkpan auth status

# 登出账户
quarkpan auth logout
```

#### 基础文件操作  
```bash
# 🎯 推荐：直接运行进入交互模式进行操作
quarkpan

# 或使用直接命令：
# 查看当前目录文件列表
quarkpan ls

# 查看指定文件夹（使用文件夹 ID）
quarkpan ls --folder-id FOLDER_ID

# 进入文件夹（切换当前工作目录）
quarkpan cd 文件夹名称

# 返回上级目录
quarkpan cd ..

# 创建文件夹
quarkpan mkdir "新文件夹"

# 重命名文件/文件夹  
quarkpan rename FILE_ID "新名称"

# 删除文件/文件夹
quarkpan rm FILE_ID

# 移动文件到指定文件夹
quarkpan mv FILE_ID FOLDER_ID

# 查看文件详细信息
quarkpan info FILE_ID
```

#### 搜索功能
```bash
# 🎯 推荐：在交互模式中使用搜索功能
quarkpan

# 或使用直接命令：
# 全盘搜索文件
quarkpan search "关键词"

# 限制搜索结果数量
quarkpan search "关键词" --limit 10

# 搜索特定文件类型
quarkpan search "报告" --file-type pdf
```

#### 上传下载
```bash
# 🎯 推荐：在交互模式中进行上传下载
quarkpan

# 或使用直接命令：
# 上传文件到当前文件夹
quarkpan upload "本地文件.txt"

# 上传到指定文件夹
quarkpan upload "本地文件.txt" --folder-id FOLDER_ID

# 获取文件下载链接
quarkpan download get FILE_ID

# 下载文件到本地
quarkpan download FILE_ID --output "本地路径.txt"
```

#### 分享管理
```bash
# 🎯 推荐：在交互模式中管理分享
quarkpan

# 或使用直接命令：
# 创建文件分享
quarkpan share create FILE_ID --title "分享标题" --password 1234

# 查看我的分享列表
quarkpan share list

# 转存他人分享
quarkpan save "https://pan.quark.cn/s/abc123" --folder "/目标文件夹" --save-all --wait

# 批量转存分享链接
quarkpan batch-save "https://pan.quark.cn/s/abc123" "https://pan.quark.cn/s/def456" --folder "/目标文件夹"

# 批量分享功能
quarkpan batch-share --help                               # 查看完整帮助
quarkpan batch-share                                      # 默认模式（四级目录）
quarkpan batch-share --target-dir "/我的资料"            # 指定目录模式
quarkpan batch-share --depth 2 --share-level both        # 灵活深度模式
quarkpan batch-share --dry-run                           # 预览模式（不创建分享）
```

### 🚀 批量分享功能详解

批量分享功能支持三种使用模式，适应不同的分享需求：

```bash
# 1️⃣ 默认模式（完全向后兼容）
quarkpan batch-share
# 分享根目录下三级目录的所有子文件夹，排除"来自：分享"目录

# 2️⃣ 指定目录模式
quarkpan batch-share --target-dir "/课程资料"
# 分享指定目录的子文件夹

quarkpan batch-share --target-dir "/文档" --depth 2
# 分享指定目录下2级深度的文件夹

# 3️⃣ 灵活深度模式
quarkpan batch-share --depth 1
# 分享根目录下1级深度的所有文件夹

quarkpan batch-share --depth 2 --share-level files
# 分享根目录下2级深度的所有文件

quarkpan batch-share --depth 2 --share-level both
# 分享根目录下2级深度的文件夹和文件

# 🔍 预览和排除
quarkpan batch-share --dry-run                           # 仅扫描预览，不创建分享
quarkpan batch-share --exclude "临时" --exclude "备份"   # 排除特定目录
quarkpan batch-share --output "my_shares.csv"           # 自定义CSV输出文件名
```

**参数说明：**
- `--target-dir, -t`: 指定起始目录路径（默认根目录）
- `--depth, -d`: 扫描深度层级（默认 3）
- `--share-level, -l`: 分享类型 - `folders` (文件夹) / `files` (文件) / `both` (两者)
- `--exclude, -e`: 排除的目录名称模式
- `--output, -o`: CSV 输出文件名
- `--dry-run`: 只扫描预览，不创建分享
```

## 🔐 登录认证详解

### API 二维码登录（推荐）

```bash
# 🎯 最简单：直接运行（自动引导登录）
quarkpan

# 或直接使用登录命令
quarkpan auth login

# 传统方式
python -m quark_client.cli auth login
```

**工作流程：**
1. 程序调用夸克官方 API 获取登录 token
2. 生成二维码并保存到 `config/qr_code.png`  
3. 在终端显示 ASCII 二维码
4. 使用夸克 APP 扫码确认登录
5. 自动获取并保存登录 Cookie
6. 验证登录状态并保存用户信息

**优点：**
- 安全可靠，使用官方 API
- 无需手动操作浏览器
- 自动化程度高

### 手动 Cookie 登录

```bash
# 🎯 最简单
quarkpan auth login --method simple

# 传统方式
python -m quark_client.cli auth login --method simple
```

**使用场景：**
- API 登录失败时的备用方案
- 已有有效 Cookie 需要快速导入
- 批量部署或脚本化场景

**操作步骤：**
1. 程序提供详细的 Cookie 获取指引
2. 用户手动从浏览器复制 Cookie
3. 粘贴到程序提示界面
4. 程序验证并保存 Cookie

### 登录状态管理

```bash
# 🎯 推荐：在交互模式中管理登录状态
quarkpan

# 或使用直接命令：
# 检查当前登录状态
quarkpan auth status

# 查看用户信息
quarkpan auth info  

# 刷新登录状态
quarkpan auth refresh

# 退出登录
quarkpan auth logout
```

**Cookie 安全说明：**
- Cookie 文件存储在 `config/cookies.json`
- 支持基础加密存储（可选）
- 自动检测 Cookie 过期并提醒重新登录
- 支持多账户 Cookie 管理（计划功能）

## 📚 API 使用说明

### 文件管理

```python
# 获取文件列表
files = client.list_files(folder_id="0", page=1, size=50)

# 创建文件夹
result = client.create_folder("新文件夹", parent_id="0")

# 删除文件
result = client.delete_files(["file_id_1", "file_id_2"])

# 重命名文件
result = client.rename_file("file_id", "新名称")

# 搜索文件
results = client.search_files("关键词")

# 上传文件
result = client.upload_file("本地文件.txt", parent_folder_id="0")

# 获取下载链接
download_url = client.get_download_url("file_id")
```

### 分享管理

```python
# 创建分享链接
share = client.create_share(
    file_ids=["file_id_1", "file_id_2"],
    title="我的分享",
    expire_days=7,
    password="1234"
)

# 解析分享链接
share_id, password = client.parse_share_url(
    "https://pan.quark.cn/s/abc123 密码: 1234"
)

# 转存分享文件
result = client.save_shared_files(
    share_url="https://pan.quark.cn/s/abc123",
    target_folder_id="0",
    save_all=True,                    # 保存全部文件
    wait_for_completion=True          # 等待转存完成
)

# 批量转存分享链接
share_urls = [
    "https://pan.quark.cn/s/abc123",
    "https://pan.quark.cn/s/def456"
]

def progress_callback(current, total, url, result):
    print(f"[{current}/{total}] 转存: {url}")

results = client.batch_save_shares(
    share_urls=share_urls,
    target_folder_id="0",
    progress_callback=progress_callback
)

# 获取我的分享列表
shares = client.get_my_shares()
```

## 📁 项目结构

```
QuarkPan/
├── quark_client/             # 主要代码包
│   ├── __init__.py           # 包入口和导出定义
│   ├── client.py             # 主客户端类
│   ├── config.py             # 配置管理
│   ├── exceptions.py         # 异常定义
│   ├── auth/                 # 认证模块
│   │   ├── __init__.py  
│   │   ├── login.py         # 统一登录管理
│   │   ├── api_login.py     # API 二维码登录
│   │   └── simple_login.py  # 手动 Cookie 登录
│   ├── core/                # 核心 API 客户端
│   │   ├── __init__.py  
│   │   └── api_client.py    # HTTP 客户端和 API 封装
│   ├── services/            # 业务服务层
│   │   ├── __init__.py  
│   │   ├── file_service.py        # 文件管理服务
│   │   ├── file_upload_service.py # 文件上传服务
│   │   ├── file_download_service.py # 文件下载服务
│   │   ├── share_service.py       # 分享管理服务
│   │   └── name_resolver.py       # 文件名解析器
│   ├── cli/                 # 命令行界面
│   │   ├── __init__.py  
│   │   ├── __main__.py      # 模块入口 (python -m quark_client.cli)
│   │   ├── main.py          # CLI 主程序
│   │   ├── interactive.py   # 交互式界面
│   │   ├── utils.py         # CLI 工具函数
│   │   └── commands/        # 命令模块
│   │       ├── __init__.py
│   │       ├── auth.py            # 认证命令
│   │       ├── basic_fileops.py   # 基础文件操作
│   │       ├── download.py        # 下载命令
│   │       ├── move_commands.py   # 移动操作命令
│   │       ├── search.py          # 搜索命令
│   │       └── share_commands.py  # 分享命令
│   └── utils/               # 工具模块
│       ├── __init__.py  
│       ├── logger.py        # 日志工具
│       └── qr_code.py       # 二维码工具
├── examples/                # 使用示例
│   ├── basic_usage.py       # 基础功能演示
│   ├── file_operations_demo.py # 文件操作演示
│   ├── file_browser_demo.py # 文件浏览器演示
│   ├── share_save_demo.py   # 分享转存演示
│   └── enhanced_share_save_demo.py # 转存功能演示
├── config/                  # 配置文件目录
│   ├── cookies.json         # 登录 Cookie 存储
│   ├── login_result.json    # 登录结果缓存
│   ├── qr_code.png          # 二维码图片
│   └── user_info.json       # 用户信息缓存
├── cli.py                   # CLI 直接入口脚本
├── setup.py                 # 安装配置
├── requirements.txt         # 依赖列表
├── LICENSE                  # 开源协议
└── README.md                # 项目说明
```

## 🧪 运行示例

项目提供了多个示例文件，帮助你快速了解各种功能的使用方法：

### 基础使用示例
```bash  
# 演示基本功能：登录、获取文件列表、搜索、存储信息
python examples/basic_usage.py
```

**功能演示：**
- ✅ 自动登录认证
- 📁 获取根目录文件列表（显示前 5 个）
- 💾 查看存储容量信息  
- 🔍 全盘文件搜索演示
- 🔗 获取个人分享列表

### 文件操作演示  
```bash
# 完整的文件管理操作流程演示
python examples/file_operations_demo.py
```

**功能演示：**
- 📂 浏览和列出文件夹内容
- ➕ 创建测试文件夹和子文件夹
- ✏️ 重命名文件和文件夹
- 📦 移动文件到不同文件夹
- 🗑️ 删除文件和清理测试数据
- 🔍 多关键词搜索演示

### 文件浏览器演示
```bash
# 交互式文件浏览器体验
python examples/file_browser_demo.py  
```

**功能演示：**
- 🖥️ 类似系统文件管理器的界面
- ⬆️⬇️ 方向键导航文件列表
- 📁 双击进入文件夹
- 📋 查看文件详细信息
- 🔄 实时刷新文件列表

### 分享转存演示
```bash
# 分享链接创建和转存功能
python examples/share_save_demo.py

# 转存功能演示
python examples/enhanced_share_save_demo.py
```

**功能演示：**
- 🔗 创建文件分享链接（带密码和有效期）
- 📋 管理个人分享列表
- 💾 转存他人分享的资源
- 🔍 分享链接格式解析
- 📊 分享文件详情查看
- 🚀 批量转存多个分享链接
- ⏳ 转存任务状态监控
- 🎯 文件过滤和高级选项

### 组合使用示例

你也可以组合使用多个示例来体验完整工作流：

```bash
# 完整体验流程
python examples/basic_usage.py          # 1. 首先体验基础功能
python examples/file_operations_demo.py # 2. 然后体验文件操作
python examples/share_save_demo.py      # 3. 最后体验分享功能
```

**注意事项：**
- 🔑 首次运行需要完成登录认证
- ⚠️ 某些操作会创建测试数据，程序会自动清理
- 📱 需要手机安装夸克 APP 用于扫码登录
- 🌐 需要稳定的网络连接

## 📦 依赖说明

### 核心依赖
- **httpx** (>=0.24.0): 现代化 HTTP 客户端，支持异步请求
- **pydantic** (>=2.0.0): 数据验证和类型注解
- **typer** (>=0.9.0): 现代化命令行界面框架
- **rich** (>=13.0.0): 美化终端输出和交互

### 二维码支持  
- **qrcode** (>=7.4.0): 二维码生成和终端 ASCII 显示

### 用户体验
- **tqdm** (>=4.65.0): 进度条显示

### 开发和测试
- **pytest** (>=7.0.0): 测试框架
- **pytest-asyncio** (>=0.21.0): 异步测试支持

### 依赖安装
```bash
# 安装所有依赖
pip install -r requirements.txt

# 仅安装核心依赖（最小化安装）  
pip install httpx typer rich pydantic

# 开发环境安装（包含测试工具）
pip install -r requirements.txt pytest pytest-asyncio
```

### 系统要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows/macOS/Linux
- **内存**: 建议 512MB 以上可用内存
- **网络**: 需要稳定的互联网连接
- **终端**: 支持 UTF-8 编码的终端（推荐）

## ⚠️ 注意事项与免责声明

### 使用须知
1. **首次使用**: 需要通过扫码或手动方式完成登录认证
2. **配置文件**: 登录信息保存在 `config/cookies.json`，请妥善保管
3. **网络环境**: 建议在稳定的网络环境下使用，避免上传 / 下载中断
4. **账号安全**: 请使用官方夸克 APP 进行扫码登录，确保账号安全
5. **功能限制**: 部分功能受夸克网盘官方 API 限制，可能会有调用频率限制

### 技术限制
- **大文件处理**: 超大文件的上传下载可能需要较长时间
- **并发限制**: 为避免触发反爬限制，默认限制并发请求数量
- **API 变更**: 夸克网盘官方 API 可能随时变更，导致部分功能暂时不可用
- **登录有效期**: Cookie 有效期有限，过期后需要重新登录

### 免责声明
1. **仅供学习**: 本项目仅用于学习和个人使用，不得用于商业用途
2. **使用风险**: 用户使用本工具所产生的任何风险和责任由用户自行承担
3. **服务条款**: 使用时请遵守夸克网盘的官方服务条款和用户协议
4. **数据安全**: 请勿使用本工具处理敏感或重要数据，作者不承担数据损失责任
5. **法律合规**: 用户应确保使用行为符合当地法律法规要求

### 故障排除
- **登录失败**: 尝试清除 `config/cookies.json` 后重新登录
- **API 错误**: 检查网络连接，或等待片刻后重试
- **二维码不显示**: 检查终端是否支持图片显示，或查看 `config/qr_code.png`
- **上传 / 下载中断**: 检查文件路径和网络连接状态
- **命令行乱码**: 确保终端支持 UTF-8 编码

### 获取帮助
- **GitHub Issues**: [提交问题报告](https://github.com/lich0821/QuarkPan/issues)
- **示例代码**: 参考 `examples/` 目录下的示例文件
- **微信群**: 发送 `WCF` 进群交流
<center>

![公众号搜索【漩智】加入社区](QrCode.jpg)
</center>

### 贡献指南
欢迎提交 Issue 和 Pull Request！在贡献代码前，请：
1. 阅读项目的代码风格规范
2. 确保新功能有对应的测试用例
3. 更新相关文档和示例代码
4. 遵循 MIT 开源协议

## 📄 许可协议

本项目采用 [MIT License](LICENSE) 开源协议。

部分下载相关实现参考了第三方项目，其署名与许可（Apache License 2.0）见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---
⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
