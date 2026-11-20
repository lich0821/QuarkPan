# 第三方组件与许可声明

本项目主体以 MIT 许可发布（见 [LICENSE](../LICENSE)）。以下部分参考或改编自以
Apache License 2.0 发布的第三方项目。

---

## QuarkPanTool

- 来源：https://github.com/ihmily/QuarkPanTool
- 作者：ihmily
- 许可：Apache License 2.0（许可证全文见 [docs/licenses/Apache-2.0.txt](licenses/Apache-2.0.txt)）

### 使用范围

`quark_client/services/file_download_service.py` 中，用于绕过
`file/download` 接口对大文件返回 `code=23018 (download file size limit)`
的夸克网盘客户端 User-Agent 字符串，以及「普通 UA 被拒后换客户端 UA 重试」
这一处理思路，参考自该项目的 `quark.py`：

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
(KHTML, like Gecko) quark-cloud-drive/2.5.56 Chrome/100.0.4896.160
Electron/18.3.5.12-a038f7b798 Safari/537.36 Channel/pckk_other_ch
```

### 修改说明

依据 Apache License 2.0 第 4(c) 条，此处说明本项目对该部分所作的修改：

- 原项目使用 asyncio + aiohttp 实现，本项目为同步 httpx 客户端，相关逻辑按本项目
  的 `QuarkAPIClient` 结构重写，未复制其异步代码；
- 重试逻辑整合进 `_request_download_info()`，同时处理 HTTP 层 4xx 与响应体内的业务码；
- 增加了 `ve` 参数与客户端 UA 版本保持一致的约束，以及 aria2 下载路径复用同一 UA；
- Cookie / Referer 头的处理为本项目自行调试所得，不来自该项目。

### 义务

分发本项目（或其衍生作品）时，需保留本声明与 `docs/licenses/Apache-2.0.txt`
中的许可证全文，并保留上述署名信息。
