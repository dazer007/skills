#!/bin/bash
# Env Backup - 环境变量备份与恢复工具
# 支持 Windows/Linux/Mac

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${HOME}/.env-backup"
CHANGE_LOG="${BACKUP_DIR}/change-log.tsv"
OS_TYPE=""

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        OS_TYPE="windows"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
    elif [[ "$OSTYPE" == "linux"* ]]; then
        OS_TYPE="linux"
    else
        OS_TYPE="unknown"
    fi
}

# 初始化备份目录
init_backup_dir() {
    mkdir -p "$BACKUP_DIR"
}

# 获取 ISO 时间戳
get_iso_timestamp() {
    date +"%Y-%m-%dT%H:%M:%S%z"
}

# 获取当前时间戳 (格式: env_yyyyMMdd_HHmmss)
get_timestamp() {
    date +"env_%Y%m%d_%H%M%S"
}

# TSV 字段转义，避免换行和 tab 破坏日志格式
tsv_escape() {
    local value="${1:-}"
    value="${value//$'\t'/ }"
    value="${value//$'\r'/ }"
    value="${value//$'\n'/ }"
    printf "%s" "$value"
}

# 初始化变更日志
init_change_log() {
    init_backup_dir
    if [[ ! -f "$CHANGE_LOG" ]]; then
        printf "timestamp\tos\tscope\tbackup_id\tsummary\tchanged\tcommand\tresult\n" > "$CHANGE_LOG"
    fi
}

# 写入一条变更记录
append_change_log() {
    local backup_id="${1:-}"
    local scope="${2:-user}"
    local summary="${3:-}"
    local changed="${4:-}"
    local command_text="${5:-}"
    local result="${6:-}"

    init_change_log

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$(get_iso_timestamp)" \
        "$(tsv_escape "$OS_TYPE")" \
        "$(tsv_escape "$scope")" \
        "$(tsv_escape "$backup_id")" \
        "$(tsv_escape "$summary")" \
        "$(tsv_escape "$changed")" \
        "$(tsv_escape "$command_text")" \
        "$(tsv_escape "$result")" >> "$CHANGE_LOG"
}

# Windows: 获取用户环境变量
win_get_user_env() {
    powershell -Command "
    \$vars = @{}
    \$vars['PATH'] = [Environment]::GetEnvironmentVariable('PATH', 'User')
    Get-ChildItem Env: | ForEach-Object {
        \$name = \$_.Key
        \$value = \$_.Value
        if (\$name -ne 'PATH') {
            try {
                \$userVal = [Environment]::GetEnvironmentVariable(\$name, 'User')
                if (\$userVal) { \$vars[\$name] = \$userVal }
            } catch {}
        }
    }
    \$vars | ConvertTo-Json -Depth 10
    "
}

# Windows: 获取系统环境变量
win_get_system_env() {
    powershell -Command "
    \$vars = @{}
    \$vars['PATH'] = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
    Get-ChildItem Env: | ForEach-Object {
        \$name = \$_.Key
        \$value = \$_.Value
        if (\$name -ne 'PATH') {
            try {
                \$sysVal = [Environment]::GetEnvironmentVariable(\$name, 'Machine')
                if (\$sysVal) { \$vars[\$name] = \$sysVal }
            } catch {}
        }
    }
    \$vars | ConvertTo-Json -Depth 10
    "
}

# Linux/Mac: 获取用户环境变量
unix_get_user_env() {
    local vars_file="$BACKUP_DIR/.temp_vars.json"
    echo "{" > "$vars_file"

    # 获取 PATH
    local path_val=$(echo "$PATH")
    echo "\"PATH\": \"$path_val\"" >> "$vars_file"

    # 获取其他用户变量 (从配置文件)
    local config_files=("$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile")

    for cfg in "${config_files[@]}"; do
        if [[ -f "$cfg" ]]; then
            grep -E "^export [A-Z_]+=" "$cfg" 2>/dev/null | while read -r line; do
                local name=$(echo "$line" | sed 's/export //' | sed 's/=.*//' | tr -d '"')
                local value=$(echo "$line" | sed 's/export [A-Z_]*="//' | sed 's/"$//' | tr -d '"')
                if [[ -n "$name" && "$name" != "PATH" ]]; then
                    echo ",\"$name\": \"$value\"" >> "$vars_file"
                fi
            done
        fi
    done

    echo "}" >> "$vars_file"
    cat "$vars_file"
    rm -f "$vars_file"
}

# 备份环境变量
backup_env() {
    local note="${1:-}"
    local scope="${2:-user}"  # user or system
    local timestamp=$(get_timestamp)
    local backup_file="$BACKUP_DIR/${timestamp}_${scope}.json"

    init_backup_dir

    echo "正在备份 $scope 环境变量..."

    if [[ "$OS_TYPE" == "windows" ]]; then
        if [[ "$scope" == "user" ]]; then
            win_get_user_env > "$backup_file"
        else
            win_get_system_env > "$backup_file"
        fi
    else
        unix_get_user_env > "$backup_file"
    fi

    # 添加元数据
    local meta_file="$BACKUP_DIR/${timestamp}_${scope}.meta.json"
    echo "{\"timestamp\": \"$timestamp\", \"scope\": \"$scope\", \"note\": \"$note\", \"os\": \"$OS_TYPE\"}" > "$meta_file"
    append_change_log "$timestamp" "$scope" "backup created" "" "$0 backup --note \"$note\" --$scope" "success"

    echo "备份完成: $backup_file"
    echo "备份ID: $timestamp"
}

# 记录环境变量修改
log_change() {
    local backup_id=""
    local scope="user"
    local summary=""
    local changed_items=()
    local command_text=""
    local result="unspecified"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --backup-id) backup_id="${2:-}"; shift 2 ;;
            --scope) scope="${2:-user}"; shift 2 ;;
            --user) scope="user"; shift ;;
            --system) scope="system"; shift ;;
            --summary) summary="${2:-}"; shift 2 ;;
            --changed) changed_items+=("${2:-}"); shift 2 ;;
            --command) command_text="${2:-}"; shift 2 ;;
            --result) result="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$summary" ]]; then
        echo "请提供 --summary 描述本次修改"
        return 1
    fi

    local changed_joined=""
    local item
    for item in "${changed_items[@]}"; do
        if [[ -n "$changed_joined" ]]; then
            changed_joined="${changed_joined}; ${item}"
        else
            changed_joined="$item"
        fi
    done

    append_change_log "$backup_id" "$scope" "$summary" "$changed_joined" "$command_text" "$result"
    echo "变更记录已写入: $CHANGE_LOG"
}

# 查看环境变量修改记录
show_change_log() {
    init_change_log

    echo "=== 环境变量变更记录 ==="
    echo "文件: $CHANGE_LOG"
    echo ""

    if command -v column &>/dev/null; then
        column -t -s $'\t' "$CHANGE_LOG"
    else
        cat "$CHANGE_LOG"
    fi
}

# 列出所有备份
list_backups() {
    init_backup_dir

    echo "=== 环境变量备份列表 ==="
    echo ""

    if [[ ! -d "$BACKUP_DIR" || -z "$(ls -A $BACKUP_DIR/*.json 2>/dev/null)" ]]; then
        echo "暂无备份记录"
        return
    fi

    for meta in "$BACKUP_DIR"/*.meta.json; do
        if [[ -f "$meta" ]]; then
            local timestamp=$(basename "$meta" | sed 's/_user.meta.json//;s/_system.meta.json//')
            local scope=$(cat "$meta" | grep -o '"scope": "[^"]*"' | sed 's/"scope": "//;s/"$//' || echo "unknown")
            local note=$(cat "$meta" | grep -o '"note": "[^"]*"' | sed 's/"note": "//;s/"$//' || echo "")
            local os=$(cat "$meta" | grep -o '"os": "[^"]*"' | sed 's/"os": "//;s/"$//' || echo "unknown")

            echo "[$timestamp] ($scope) [$os]"
            if [[ -n "$note" ]]; then
                echo "  备注: $note"
            fi
            echo ""
        fi
    done
}

# 显示备份内容
show_backup() {
    local backup_id="${1:-}"
    local scope="${2:-user}"

    if [[ -z "$backup_id" ]]; then
        echo "请指定备份ID"
        return 1
    fi

    local backup_file="$BACKUP_DIR/${backup_id}_${scope}.json"

    if [[ ! -f "$backup_file" ]]; then
        echo "备份文件不存在: $backup_file"
        return 1
    fi

    echo "=== 备份内容: $backup_id ($scope) ==="
    echo ""

    if command -v jq &>/dev/null; then
        jq . "$backup_file"
    else
        cat "$backup_file"
    fi
}

# 对比差异
diff_backup() {
    local backup_id="${1:-}"
    local scope="${2:-user}"

    if [[ -z "$backup_id" ]]; then
        echo "请指定备份ID"
        return 1
    fi

    local backup_file="$BACKUP_DIR/${backup_id}_${scope}.json"

    if [[ ! -f "$backup_file" ]]; then
        echo "备份文件不存在: $backup_file"
        return 1
    fi

    echo "=== 环境变量差异对比 ==="
    echo "备份: $backup_id ($scope)"
    echo "当前: 实时环境"
    echo ""

    # 获取当前环境变量
    local current_file="$BACKUP_DIR/.current_temp.json"
    if [[ "$OS_TYPE" == "windows" ]]; then
        if [[ "$scope" == "user" ]]; then
            win_get_user_env > "$current_file"
        else
            win_get_system_env > "$current_file"
        fi
    else
        unix_get_user_env > "$current_file"
    fi

    # 对比 PATH
    echo "=== PATH 变化 ==="
    local backup_path=$(grep '"PATH"' "$backup_file" | sed 's/.*"PATH"[[:space:]]*:[[:space:]]*"//;s/",*$//' | tail -1)
    local current_path=$(grep '"PATH"' "$current_file" | sed 's/.*"PATH"[[:space:]]*:[[:space:]]*"//;s/",*$//' | tail -1)

    # 分割 PATH 并对比
    local backup_paths=($(echo "$backup_path" | tr ';' '\n' | tr ':' '\n' | sort))
    local current_paths=($(echo "$current_path" | tr ';' '\n' | tr ':' '\n' | sort))

    # 找出新增的路径
    echo "新增:"
    for p in "${current_paths[@]}"; do
        if [[ -n "$p" ]]; then
            local found=0
            for bp in "${backup_paths[@]}"; do
                if [[ "$p" == "$bp" ]]; then
                    found=1
                    break
                fi
            done
            if [[ $found -eq 0 ]]; then
                echo "  + $p"
            fi
        fi
    done

    # 找出删除的路径
    echo ""
    echo "删除:"
    for p in "${backup_paths[@]}"; do
        if [[ -n "$p" ]]; then
            local found=0
            for cp in "${current_paths[@]}"; do
                if [[ "$p" == "$cp" ]]; then
                    found=1
                    break
                fi
            done
            if [[ $found -eq 0 ]]; then
                echo "  - $p"
            fi
        fi
    done

    rm -f "$current_file"
}

# 恢复环境变量 (仅显示命令，不自动执行)
restore_env() {
    local backup_id="${1:-}"
    local scope="${2:-user}"

    if [[ -z "$backup_id" ]]; then
        echo "请指定备份ID"
        return 1
    fi

    local backup_file="$BACKUP_DIR/${backup_id}_${scope}.json"

    if [[ ! -f "$backup_file" ]]; then
        echo "备份文件不存在: $backup_file"
        return 1
    fi

    echo "=== 恢复环境变量 ==="
    echo "备份: $backup_id ($scope)"
    echo ""

    # 读取备份的 PATH
    local backup_path=$(grep '"PATH"' "$backup_file" | sed 's/.*"PATH"[[:space:]]*:[[:space:]]*"//;s/",*$//' | tail -1)

    if [[ "$OS_TYPE" == "windows" ]]; then
        echo "请在 PowerShell 中执行以下命令:"
        echo ""
        echo "[Environment]::SetEnvironmentVariable('PATH', '$backup_path', '$scope')"
        echo ""
        echo "或使用管理员权限执行 (系统变量):"
        echo "[Environment]::SetEnvironmentVariable('PATH', '$backup_path', 'Machine')"
    else
        echo "请在终端执行以下命令或添加到配置文件:"
        echo ""
        echo "export PATH=\"$backup_path\""
        echo ""
        echo "永久生效: 添加到 ~/.bashrc 或 ~/.zshrc"
    fi
}

# 显示帮助
show_help() {
    echo "Env Backup - 环境变量备份与恢复工具"
    echo ""
    echo "用法:"
    echo "  $0 backup [--note \"描述\"] [--user|--system]  备份环境变量"
    echo "  $0 list                                    列出所有备份"
    echo "  $0 show <backup-id> [--user|--system]      显示备份内容"
    echo "  $0 diff <backup-id> [--user|--system]      对比差异"
    echo "  $0 restore <backup-id> [--user|--system]   生成恢复命令"
    echo "  $0 log --backup-id <id> --summary <text> [--changed <text>] [--command <text>] [--result <text>]  记录修改"
    echo "  $0 changelog                               查看修改记录"
    echo ""
    echo "平台: Windows / Linux / macOS"
}

# 主函数
main() {
    detect_os

    local command="${1:-help}"
    shift || true

    case "$command" in
        backup)
            local note=""
            local scope="user"
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --note) note="$2"; shift 2 ;;
                    --user) scope="user"; shift ;;
                    --system) scope="system"; shift ;;
                    *) shift ;;
                esac
            done
            backup_env "$note" "$scope"
            ;;
        list)
            list_backups
            ;;
        show)
            local backup_id="${1:-}"
            local scope="user"
            shift || true
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --user) scope="user"; shift ;;
                    --system) scope="system"; shift ;;
                    *) shift ;;
                esac
            done
            show_backup "$backup_id" "$scope"
            ;;
        diff)
            local backup_id="${1:-}"
            local scope="user"
            shift || true
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --user) scope="user"; shift ;;
                    --system) scope="system"; shift ;;
                    *) shift ;;
                esac
            done
            diff_backup "$backup_id" "$scope"
            ;;
        restore)
            local backup_id="${1:-}"
            local scope="user"
            shift || true
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --user) scope="user"; shift ;;
                    --system) scope="system"; shift ;;
                    *) shift ;;
                esac
            done
            restore_env "$backup_id" "$scope"
            ;;
        log)
            log_change "$@"
            ;;
        changelog|changes)
            show_change_log
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "未知命令: $command"
            show_help
            ;;
    esac
}

main "$@"
