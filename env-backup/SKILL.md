---
name: env-backup
description: 环境变量安全备份、恢复、差异对比和变更记录工具，支持 Windows/Linux/macOS。Use this skill whenever Codex may read, add, remove, rename, persist, repair, or modify environment variables or PATH-like configuration, including PATH/Path, JAVA_HOME, JDK/JRE switching, GOPATH/GOROOT, PYTHONPATH, NODE_HOME, NPM/Yarn/pnpm paths, CUDA_PATH, ANDROID_HOME, SDK/toolchain paths, proxy variables, API key variables, shell profile edits (.bashrc/.zshrc/.profile/.bash_profile), PowerShell profile edits, Windows user/system environment variables, registry environment changes, setx, [Environment]::SetEnvironmentVariable, export VAR=..., $env:VAR=..., installer PATH fixes, or any request that could affect command discovery. Before any env-changing command or file edit, create a backup; after every env-related change, append a change log entry describing what changed, the command/file touched, result, and backup id.
---

# Env Backup

环境变量管理工具，支持备份、恢复、对比查看。

**硬性规则：任何环境变量或 PATH 相关修改前先备份，修改后写变更记录。**

## Mandatory Workflow

When handling environment-variable work:

1. Run `backup` before the first change. Keep the printed backup ID.
2. Make the requested environment change.
3. Run `log` immediately after the change, even if the change failed or was skipped.
4. Run `diff <backup-id>` when useful, especially after PATH edits or toolchain switches.
5. Tell the user the backup ID and where the change log is stored.

Prefer a specific note on backup, for example:

```bash
./scripts/env-backup.sh backup --note "before setting JAVA_HOME for JDK 21"
```

## 功能

- **backup**: 备份当前环境变量到 JSON 文件
- **restore**: 从备份恢复环境变量
- **diff**: 对比当前与备份的环境变量差异
- **list**: 列出所有备份记录
- **show**: 显示指定备份内容
- **log**: 记录一次环境变量修改
- **changelog**: 查看环境变量修改记录

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

# 记录一次修改
./scripts/env-backup.sh log --backup-id <backup-id> --summary "设置 JAVA_HOME" --changed "JAVA_HOME=D:\Java\jdk-21" --command "[Environment]::SetEnvironmentVariable(...)" --result "success"

# 查看修改记录
./scripts/env-backup.sh changelog
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

变更记录文件：`~/.env-backup/change-log.tsv`

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
./scripts/env-backup.sh diff env_20260501_213045
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
./scripts/env-backup.sh restore env_20260501_213045 --user
```

### 记录修改

```bash
./scripts/env-backup.sh log \
  --backup-id env_20260501_213045 \
  --scope user \
  --summary "切换 JDK 到 21" \
  --changed "JAVA_HOME=D:\Program Files\Java\jdk-21" \
  --changed "PATH added D:\Program Files\Java\jdk-21\bin" \
  --command "PowerShell SetEnvironmentVariable" \
  --result "success"
```

## Tags

`environment`, `backup`, `restore`, `path`, `windows`, `linux`, `macos`, `JAVA_HOME`, `setx`, `PowerShell`, `shell-profile`

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
            "command": "jq -r '.tool_input.command' | grep -qiE '(SetEnvironmentVariable|setx|JAVA_HOME|GOPATH|GOROOT|PYTHONPATH|NODE_HOME|CUDA_PATH|ANDROID_HOME|PATH|\\.bashrc|\\.zshrc|PowerShell.*profile|export [A-Za-z_][A-Za-z0-9_]*=|\\$env:)' && ~/.claude/skills/env-backup/scripts/env-backup.sh backup --note 'auto-backup before environment-related command' 2>/dev/null || true",
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
