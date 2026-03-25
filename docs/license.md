# License 功能说明（已实现）

## 1. 机器码
- 生成位置：`manager-go`。
- 规则顺序：
  - Linux：读取 `/etc/machine-id`
  - macOS：读取 `ioreg -rd1 -c IOPlatformExpertDevice` 的 `IOPlatformUUID`
  - 兜底：首个可用网卡 MAC
- 对原始值做 `SHA-256`，输出十六进制字符串作为 `machine_code`。

## 2. License 结构
- 采用 `签名 + 加密`：
  - 加密：`AES-256-GCM`
  - 签名：`HMAC-SHA256`
- claims 字段：
  - `machine_code`
  - `expire_time`（本地时间语义）
  - `max_monitors`
  - `issued_at`
- envelope 字段：
  - `alg`
  - `nonce`（base64）
  - `ciphertext`（base64）
  - `signature`（hex）
  - `issued_at`

## 3. 后端行为
- Python Web 全局拦截：
  - 如果已过期，返回 `402`。
  - 放行接口：
    - `/api/v1/health`
    - `/api/v1/auth/login`
    - `/api/v1/auth/captcha`
    - `/api/v1/license/status`
    - `/api/v1/license/upload`
- manager-go 限额校验：
  - 创建启用监控、或把监控从禁用改为启用时校验 License。
  - 统计口径：`enabled=1` 的监控数。
  - 超限返回 `402`。

## 4. 防回拨与停采集
- 每 4 小时更新一次 `last_running_time` 到 `system_configs`。
- 如果发现 `当前本地时间 < last_running_time`：
  - 标记 halted。
  - 停止采集/分发流程（API 仍可访问，便于上传新 License）。
- License 过期同样会停止采集/分发。

## 5. 前端行为
- 新增授权页：`/  `（无需登录、无需权限）。
- 全局请求拦截到 `402` 时，强制跳转 `/license`。
- 授权页支持：
  - 展示机器码和状态
  - 上传 `.lic`

## 6. License 签发工具
- 路径：`manager-go/tools/license-gen/main.go`
- 作用：离线生成可直接上传的 `.lic` 文件（与 manager-go 校验逻辑一致）。

## 6.1 交互式小工具（推荐）
- 路径：`tools/generate-license.sh`
- 用法：
```bash
cd /Users/peter/Documents/arco
./tools/generate-license.sh
```
- 运行后按提示输入：
  - 机器码
  - 到期时间
  - 数量（最大启用监控数）
- 脚本会直接打印生成后的 license 文件路径。

### 使用示例
```bash
cd manager-go
go run ./tools/license-gen \
  --machine-code "<目标机器码>" \
  --expire-time "2026-12-31 23:59:59" \
  --max-monitors 200 \
  --out /tmp/arco.lic
```

### 可选参数
- `--issued-at`：签发时间，默认当前本地时间（RFC3339）。
- `--enc-key`：加密密钥种子（默认读取 `LICENSE_ENC_KEY`，否则使用内置默认值）。
- `--sign-key`：签名密钥种子（默认读取 `LICENSE_SIGN_KEY`，否则使用内置默认值）。
- `--base64`：输出 base64 包裹后的 license 文本（默认输出 JSON envelope）。

## 7. 关键接口
- `GET /api/v1/license/status`
- `POST /api/v1/license/upload`
