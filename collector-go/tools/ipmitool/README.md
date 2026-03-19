# collector-go IPMI 工具打包说明

该目录用于存放 `collector-go` 自带的 `ipmitool` 二进制，满足商用部署默认不依赖系统安装。

## 目录结构

```text
tools/ipmitool/
├── bin/                # 二进制目录（运行时读取）
├── checksums.sha256    # 可选，二进制校验文件
└── scripts/
    ├── detect_ipmitool.sh
    ├── install.sh
    └── verify.sh
```

## 推荐文件命名

- `ipmitool-linux-amd64`
- `ipmitool-linux-arm64`
- `ipmitool-darwin-amd64`
- `ipmitool-darwin-arm64`
- `ipmitool.exe`（通用 Windows）
- `ipmitool-windows-amd64.exe`
- `ipmitool-windows-arm64.exe`
- `ipmitool`（默认兜底）

## 交付流程

1. 安装二进制到 bundle：

```bash
cd collector-go
./tools/ipmitool/scripts/install.sh --source /path/to/ipmitool-artifacts
```

2. 发布前校验：

```bash
cd collector-go
./tools/ipmitool/scripts/verify.sh --require-current
```

3. 启动 collector：

- `start.sh` 和 `manage-services.sh` 会自动优先设置 `COLLECTOR_IPMITOOL_BIN` 指向 bundle。
- 只有显式设置 `COLLECTOR_ALLOW_SYSTEM_IPMITOOL=true` 时，才允许回退系统 PATH。

