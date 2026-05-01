---
name: env-backup
description: 环境变量备份与恢复工具。**触发条件**：用户请求修改/切换/添加/删除环境变量（PATH、JAVA_HOME、GOPATH等）时，自动先备份再执行修改。支持 Windows/Linux/Mac。
metadata:
  short-description: 环境变量备份恢复
  triggers:
    - "修改环境变量"
    - "切换 JDK"
    - "更改 PATH"
    - "设置 JAVA_HOME"
    - "添加到 PATH"
    - "删除环境变量"
    - "环境变量备份"
---

# Env Backup

环境变量管理工具，支持备份、恢复、对比查看。

**重要：修改环境变量前自动备份，防止误操作导致环境丢失。**

## Trigger

以下场景**自动触发**此 skill，先备份再执行操作：

| 触发词 | 操作 |
|--------|------|
| "修改环境变量"、"更改环境变量" | 备份 + 执行修改 |
| "切换 JDK"、"切换 Java 版本" | 备份 + 修改 JAVA_HOME/PATH |
| "添加到 PATH"、"删除 PATH" | 备份 + 修改 PATH |
| "设置 JAVA_HOME"、"设置 GOPATH" | 备份 + 设置变量 |
| "环境变量备份"、"备份环境变量" | 仅备份 |

**标准工作流**：
1. 收到修改请求 → 自动执行 `backup`
2. 执行用户请求的环境变量修改
3. 可选：执行 `diff` 展示变更对比

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

## Hooks 配置 (可选自动化)

如需在每次修改环境变量时自动备份，可配置 Claude Code hook：

在 `~/.claude/settings.json` 中添加：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' | grep -qE '(SetEnvironmentVariable|JAVA_HOME|PATH)' && ~/.claude/skills/env-backup/scripts/env-backup.sh backup --note 'auto-backup' 2>/dev/null || true",
            "timeout": 10,
            "statusMessage": "Auto-backing up environment variables..."
          }
        ]
      }
    ]
  }
}
```

**注意**：hook 配置后需要重启 Claude Code 或执行 `/hooks` 重新加载。

## Compatibility

- Claude Code: Yes
- OpenClaw: Yes