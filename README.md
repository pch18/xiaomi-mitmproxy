# xiaomi mitmproxy

用于查看小米云服务加密 API 流量的 mitmproxy addon 和 mitmweb 界面补丁。

它不会修改拦截到的原始请求和响应内容。对于匹配的小米 API 请求，会在
mitmweb 中额外增加两个详情选项卡：

- `Xiaomi Request`
- `Xiaomi Response`

选项卡使用支持折叠和语法高亮的 JSON 阅读器展示解密结果。即使解密失败，
选项卡也会保留，并显示错误信息和原始内容。

## 功能

- 仅处理 `api.io.mi.com` 及其子域名。
- 从 `application/x-www-form-urlencoded` 请求体中提取 `_nonce` 和 `data`。
- 解密小米 RC4 加密的请求和响应内容。
- 保留 mitmweb 原有的 `Request` 和 `Response` 选项卡。
- 增加支持折叠、语法高亮和局部复制的 JSON 文本阅读器。
- 解密失败时仍然显示小米选项卡，并展示原始内容。
- Flow List 默认使用 `mi.com` 作为搜索条件。
- 在顶部选项卡后增加红色 `Clear All` 按钮，点击后直接清空请求，无需二次确认。
- 自动捕获并持久化登录响应中的 `ssecurity`。

## 环境要求

- Python 3.11 或更高版本
- 手机和运行 mitmweb 的电脑位于同一个局域网
- 一个可用的小米云服务登录会话，或已有的小米云服务 `ssecurity`

界面补丁固定适配以下版本：

```text
mitmproxy==12.2.3
```

## 安装

```bash
git clone <你的 GitHub 仓库地址>
cd xiaomi-mitmproxy

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 patch_mitmweb_comment_preview.py
```

补丁脚本会修改本地 `.venv` 中安装的 mitmweb 文件。重新创建虚拟环境或重新
安装 mitmproxy 后，需要再次运行补丁脚本。

## 配置 ssecurity

addon 会从当前项目目录读取小米云服务会话密钥：

```text
ssecurity.txt
```

`ssecurity` 属于会话敏感信息，因此该文件已经被 Git 忽略。如果文件不存在，
addon 会在启动时自动创建空的 `ssecurity.txt`，并将权限限制为仅当前用户可
读写。

addon 会自动监听以下登录接口：

```text
https://account.xiaomi.com/pass/serviceLoginAuth2
```

当该接口的明文响应中包含 `ssecurity` 时，addon 会：

1. 将最新值写入 `ssecurity.txt`。
2. 将文件权限限制为仅当前用户可读写。
3. 立即更新内存中的密钥，无需重启 mitmweb。

也可以在启动 mitmweb 前手工填写：

```bash
printf '%s\n' '你的-ssecurity-值' > ssecurity.txt
chmod 600 ssecurity.txt
```

小米登录会话发生变化时，该密钥可能会失效。

## 启动 mitmweb

```bash
source .venv/bin/activate
mitmweb -s app.py --listen-host 0.0.0.0 --listen-port 8080
```

在电脑上打开 Web 管理界面：

```text
http://127.0.0.1:8081
```

更新界面补丁后，请强制刷新浏览器：

```text
macOS:         Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R
```

## 配置手机代理

1. 将手机和电脑连接到同一个 Wi-Fi。
2. 查询电脑的局域网 IP 地址。macOS 可以执行：

   ```bash
   ipconfig getifaddr en0
   ```

3. 在手机的 Wi-Fi 设置中手动配置 HTTP 代理：

   ```text
   服务器: <电脑局域网 IP>
   端口:   8080
   ```

4. 使用手机浏览器打开：

   ```text
   http://mitm.it
   ```

5. 根据手机平台下载并安装 mitmproxy CA 证书。

### iPhone 和 iPad

安装描述文件后，还需要手工启用证书信任：

```text
设置 > 通用 > 关于本机 > 证书信任设置
```

为 mitmproxy 根证书启用完全信任。

### Android

将下载的证书安装为 CA 证书。Android 7 及更高版本中，应用可能会拒绝用户
安装的 CA 证书，除非应用明确允许使用该证书。

## 使用方式

1. 启动 mitmweb，并配置手机代理。
2. 在手机上使用小米应用。
3. 在 mitmweb 的 Flow List 中选择一个匹配的请求。
4. 打开 `Xiaomi Request` 或 `Xiaomi Response`。
5. 点击 JSON 左侧的展开箭头，折叠或展开对象和数组。
6. 选中任意可见文本，即可局部复制 JSON 内容。

mitmweb 原有的 `Request` 和 `Response` 选项卡仍然会展示加密前的原始流量。

## 解密失败

只要域名匹配，两个小米选项卡都会显示。解密失败时会展示：

```text
<错误信息>

Raw body
<原始请求或响应内容>
```

常见原因：

- `ssecurity.txt` 为空，或其中的密钥已经失效。
- 请求中没有 `_nonce` 和 `data`。
- 接口使用了不同的请求格式。
- 收到响应时，尚未获得可用的请求 nonce。

## 测试

```bash
source .venv/bin/activate
python3 -m unittest -v
```

## 已知限制

- mitmweb 补丁仅适配 `mitmproxy==12.2.3`。使用其他版本时，可能需要调整
  `patch_mitmweb_comment_preview.py`。
- addon 只会尝试解密 `api.io.mi.com` 及其子域名的 RC4 流量。
- 如果应用使用了证书锁定、自定义 TLS 实现，或绕过系统代理，可能无法抓取
  流量。

## 使用声明

请仅检查你有权访问的设备、账号和流量。解密后的 API 内容和小米会话密钥
可能包含敏感信息。测试结束后，请移除手机代理配置和 mitmproxy CA 证书。
