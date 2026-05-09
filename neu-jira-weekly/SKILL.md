---
name: neu-jira-weekly
description: 从东软Neusoft Jira自动生成工作周报。触发条件：用户要求生成周报/日报、提供Jira filter链接、提到"周报""工作汇报""Jira汇报"等关键词。支持按项目现场分组、按状态分类，输出简洁中文周报格式。每次使用需用户提供账号密码（不存储凭证）。
type: skill
agent_created: true
version: 1.0
---

# 东软 Jira 工作周报生成器

## 概述

从东软内部 Jira（Server 7.10.1）拉取任务数据，自动生成按项目现场分组的工作周报。

**核心流程**：用户提供账号密码 → 调用 Jira REST API → 按项目分组 → 生成周报

## 重要：凭证不存储

每次使用时用户需提供：
- Jira 用户名
- Jira 密码

**绝不将凭证写入任何文件、内存或配置中**。仅在当前会话的 curl 命令中使用。

## Jira 服务器信息

| 项目 | 值 |
|------|------|
| 地址 | `http://10.100.77.22:8888` |
| 版本 | Jira 7.10.1 (Server) |
| 认证 | Basic Auth（用户名+密码） |
| API | REST API v2 |

## 默认配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| Filter ID | 85890 | ddz查询过去一周提测的jira |
| 报告周期 | 过去6天 | 由 filter JQL 决定 |
| 输出格式 | 纯文本 | 按项目分组，条目式 |

## 工作流程

### Step 1: 获取凭证

向用户询问：
- 用户名（如 duandzh）
- 密码

如果用户已提供，直接使用。

### Step 2: 验证认证

```bash
curl -s -m 10 -u "{username}:{password}" \
  "http://10.100.77.22:8888/rest/api/2/myself"
```

返回 200 且包含用户信息 → 认证成功
返回 401 → 认证失败，提示用户检查账号密码

### Step 3: 获取 Filter JQL

用户可能提供以下任一形式：
- Filter URL：`http://10.100.77.22:8888/browse/XXX?filter=85890`
- Filter ID：`85890`
- 直接 JQL

获取 Filter 的 JQL：

```bash
curl -s -m 10 -u "{username}:{password}" \
  "http://10.100.77.22:8888/rest/api/2/filter/{filterId}"
```

从返回的 `searchUrl` 字段提取完整查询 URL，或从 `jql` 字段提取 JQL。

### Step 4: 查询任务列表

使用 Filter 的 JQL 查询，只请求必要字段：

```bash
curl -s -m 15 -u "{username}:{password}" \
  "http://10.100.77.22:8888/rest/api/2/search?jql={encoded_jql}&maxResults=50&fields=key,summary,status,issuetype,project,description,customfield_10116,customfield_10303,duedate,resolutiondate,created,updated"
```

### Step 5: 数据分组

按**项目**（project.name）分组，每组按**现场简称**命名。

**项目简称不硬编码**，每次从 Jira 返回数据中动态提取：
- 从 `project.name` 提取简称（如"第六-宁夏区第四人民医院"→"宁夏四院"，"战略-西安交大一附院"→"交大一附院"）
- 从 `summary` 前缀推断（如"交大hlwyyROC-"→"交大"，"宁夏四院-"→"宁夏四院")
- 规则：去掉"第六-"、"战略-"等部门前缀，取医院核心简称

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
- 去掉项目前缀重复部分（如"交大hlwyyROC-"简化为"交大-")
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
| `--name` | 指定姓名 | `--name 段大志` |
| `--days` | 指定天数范围 | `--days 7` |
| `--jql` | 自定义 JQL | `--jql "assignee=xxx"` |
| `--output` | 指定输出路径 | `--output ./reports/` |

## 错误处理

| 场景 | 处理 |
|------|------|
| 认证失败 | 提示用户检查账号密码，不重试 |
| Filter 不存在 | 提示用户确认 Filter ID |
| 查询无结果 | 提示用户可能本周无匹配任务 |
| API 超时 | 建议用户检查网络连通性 |

## 注意事项

1. **凭证安全**：密码仅在 curl -u 参数中使用，绝不写入文件
2. **Jira Server 版本限制**：不支持 PAT（需 8.14+），只能用 Basic Auth
3. **编码问题**：JQL 中的中文状态需 URL 编码
4. **字段差异**：不同项目的 customfield 可能不同，customfield_10116=任务类型，customfield_10303=变更类型

## Tags

`jira`, `weekly-report`, `neusoft`, `work-report`, `basic-auth`, `rest-api`

## Compatibility

- Claude Code: Yes
- OpenClaw: Yes
- Codex: Yes