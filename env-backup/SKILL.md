---
name: env-backup
description: 环境变量备份与恢复工具，支持 Windows/Linux/Mac。记录环境变量变更历史，快速恢复、对比差异。
metadata:
  short-description: 环境变量备份恢复
---

# Env Backup

环境变量管理工具，支持备份、恢复、对比查看。

## 功能

- **backup**: 备份当前环境变量到 JSON 文件
- **restore**: 从备份恢复环境变量
- **diff**: 对比当前与备份的环境变量差异
- **list**: 列出所有备份记录
- **show**: 显示指定备份内容

## 平台支持

| 平台 | 用户变量 | 系统变量 |
|------|---------|---------|
| Windows | 支持 | 支持 |
| Linux | 支持 (`~/.bashrc`, `~/.zshrc`) | 需要 root |
| macOS | 支持 (`~/.zshrc`) | 需要 root |

## 安装

无需额外安装，使用脚本直接运行。

## 使用方法

```bash
# 备份当前环境变量
./scripts/env-backup.sh backup [--note "描述"]

# 列出所有备份
./scripts/env-backup.sh list

# 显示指定备份内容
./scripts/env-backup.sh show <backup-id>

# 对比差异
./scripts/env-backup.sh diff <backup-id>

# 恢复环境变量
./scripts/env-backup.sh restore <backup-id> [--user|--system]
```

## Windows 特殊说明

Windows 分离用户变量和系统变量：
- `--user`: 操作用户环境变量 (默认)
- `--system`: 操作系统环境变量 (需要管理员权限)

## 备份存储位置

| 平台 | 存储路径 |
|------|---------|
| Windows | `~/.env-backup/` |
| Linux | `~/.env-backup/` |
| macOS | `~/.env-backup/` |

## 示例

### 备份环境变量

```bash
# Windows (PowerShell)
./scripts/env-backup.sh backup --note "安装 Python 后备份"

# Linux/Mac
./scripts/env-backup.sh backup --note "配置开发环境"
```

### 查看差异

```bash
./scripts/env-backup.sh diff 2026-05-01_20-30
```

输出示例：
```
=== PATH 变化 ===
新增:
  + D:\program\Python\python313-32
  + D:\program\Python\uv

删除:
  - D:\program\windows10\msys64\mingw64\bin

修改:
  JAVA_HOME: D:\Program Files\jdk\jdk-17 -> D:\Program Files\jdk\jdk-21
```

### 恢复环境变量

```bash
# 恢复用户 PATH
./scripts/env-backup.sh restore 2026-05-01_20-30 --user
```

## Tags

`environment`, `backup`, `restore`, `path`, `windows`, `linux`, `macos`

## Compatibility

- Claude Code: Yes
- OpenClaw: Yes