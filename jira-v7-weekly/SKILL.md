---
name: jira-v7-weekly
description: 从 Jira Server 7.x 自动生成工作周报。触发条件：用户要求生成周报/日报、提供Jira filter链接、提到"周报""工作汇报""Jira汇报"等关键词。支持按项目现场分组、按状态分类，输出简洁中文周报格式。**首次使用需用户提供：Jira服务器地址、用户名、密码**，凭证可保存到本地配置目录供后续使用。
type: skill
agent_created: true
version: 1.1
---

# Jira Server 7.x 工作周报生成器

## 概述

从 Jira Server 7.x 拉取任务数据，自动生成按项目现场分组的工作周报。

**核心流程**：用户提供凭证 → 调用 Jira REST API → 按项目分组 → 生成周报

## 凭证管理

### 本地配置目录

凭证保存位置：`~/.jira-v7-weekly/config.json`

### 配置文件格式

```json
{
  "jira_host": "http://your-jira-server:port",
  "username": "your_username",
  "password": "your_password",
  "default_filter": "filter_id",
  "default_name": "你的姓名"
}
```

### 凭证处理流程

1. **首次使用**：向用户询问 Jira服务器地址、用户名、密码
2. **询问保存**：认证成功后询问是否保存到本地配置
3. **后续使用**：自动读取本地配置，无需重复输入
4. **配置更新**：用户可随时更新配置（如更换服务器或账号）

### 安全提示

- 配置文件位于用户主目录，仅当前用户可访问
- 如需更高安全性，可选择不保存凭证，每次手动输入
- 更换服务器或账号时，需更新配置文件

## Jira 服务器信息

| 项目 | 值 |
|------|------|
| 地址 | 从配置或用户输入获取 |
| 版本 | Jira Server 7.x |
| 认证 | Basic Auth（用户名+密码） |
| API | REST API v2 |

## 默认配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| Filter ID | 从配置获取或用户指定 | JQL查询过滤器 |
| 报告周期 | 过去6天 | 由 filter JQL 决定 |
| 输出格式 | 纯文本 | 按项目分组，条目式 |

## 工作流程

### Step 1: 获取凭证

检查本地配置 `~/.jira-v7-weekly/config.json`：
- 若存在且有效 → 直接使用
- 若不存在 → 向用户询问：
  - Jira 服务器地址（如 http://server:port）
  - 用户名
  - 密码

### Step 2: 验证认证

```bash
curl -s -m 10 -u "{username}:{password}" \
  "{jira_host}/rest/api/2/myself"
```

返回 200 且包含用户信息 → 认证成功
返回 401 → 认证失败，提示用户检查账号密码

认证成功后询问：是否保存凭证到本地配置？

### Step 3: 获取 Filter JQL

用户可能提供以下任一形式：
- Filter URL：`{jira_host}/browse/XXX?filter={filter_id}`
- Filter ID：从配置或用户指定
- 直接 JQL

获取 Filter 的 JQL：

```bash
curl -s -m 10 -u "{username}:{password}" \
  "{jira_host}/rest/api/2/filter/{filterId}"
```

从返回的 `searchUrl` 字段提取完整查询 URL，或从 `jql` 字段提取 JQL。

### Step 4: 查询任务列表

使用 Filter 的 JQL 查询，只请求必要字段：

```bash
curl -s -m 15 -u "{username}:{password}" \
  "{jira_host}/rest/api/2/search?jql={encoded_jql}&maxResults=50&fields=key,summary,status,issuetype,project,description,customfield_10116,customfield_10303,duedate,resolutiondate,created,updated"
```

### Step 5: 数据分组

按**项目**（project.name）分组，每组按**现场简称**命名。

**项目简称不硬编码**，每次从 Jira 返回数据中动态提取：
- 从 `project.name` 提取简称（如"部门-客户A项目"→"客户A"，"部门-客户B现场"→"客户B"）
- 从 `summary` 前缀推断（如"{客户代码}-"→"客户名")
- 规则：去掉部门前缀，取客户核心简称

组内按任务类型归类：
- 部署/环境类任务
- 缺陷/修复类
- 需求/接口对接类

### Step 6: 生成周报

#### 报告格式模板

```
{姓名}({用户名}) {起始日期} — {结束日期} 工作周报

一、{项目简称}{工作类别}
1.1、{任务简要描述} 【{Jira号}】
1.2、{任务简要描述} 【{Jira号}】

二、{项目简称}{工作类别}
2.1、{任务简要描述} 【{Jira号}】

下周
一、{下周计划1}
二、{下周计划2}
```

#### 格式要求

- **标题行**：姓名(用户名) 日期范围 工作周报
- **分组标题**：中文编号（一、二、三...）+ 项目简称 + 工作类别
- **条目编号**：1.1、1.2、2.1、2.2...（组内序号）
- **Jira号**：每条末尾附 `【KEY-NUM】`
- **描述简洁**：一句话概括核心内容，不含冗余信息
- **状态区分**：只在本周工作中体现，不单独标注状态
- **下周计划**：由用户手动补充或从进行中任务推断

#### 描述简化规则

- 从 `summary` 提取核心信息
- 从 `description` 补充关键修改点（如具体字段名、存储过程名）
- 去掉项目前缀重复部分（如"{客户代码}-"简化为"客户-")
- 同类任务可标注"同xxx"，减少重复描述

### Step 7: 输出保存

保存到当前工作目录：
```
weekly_report_{年份}W{周号}.txt
```

周号计算：ISO week number（如 5月9日 → W19）

### Step 8: 交互确认

生成后询问用户：
- 是否需要调整分组？
- 是否需要补充下周计划？
- 是否需要导出其他格式？

## 自定义参数

用户可通过参数覆盖默认值：

| 参数 | 说明 | 示例 |
|------|------|------|
| `--filter` | 指定 Filter ID | `--filter 12345` |
| `--name` | 指定姓名 | `--name 张三` |
| `--days` | 指定天数范围 | `--days 7` |
| `--jql` | 自定义 JQL | `--jql "assignee=xxx"` |
| `--output` | 指定输出路径 | `--output ./reports/` |
| `--reset` | 重置本地配置 | `--reset` |

## 错误处理

| 场景 | 处理 |
|------|------|
| 认证失败 | 提示用户检查账号密码，询问是否更新配置 |
| Filter 不存在 | 提示用户确认 Filter ID |
| 查询无结果 | 提示用户可能本周无匹配任务 |
| API 超时 | 建议用户检查网络连通性 |
| 配置损坏 | 提示用户使用 --reset 重置配置 |

## 注意事项

1. **凭证安全**：配置文件位于用户主目录，建议定期检查
2. **Jira Server 版本限制**：不支持 PAT（需 8.14+），只能用 Basic Auth
3. **编码问题**：JQL 中的中文状态需 URL 编码
4. **字段差异**：不同项目的 customfield 可能不同，customfield_10116=任务类型，customfield_10303=变更类型

## Tags

`jira`, `weekly-report`, `jira-server-7`, `work-report`, `basic-auth`, `rest-api`

## Compatibility

- Claude Code: Yes
- OpenClaw: Yes
- Codex: Yes