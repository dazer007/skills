---
name: summarize-config
description: 配置 summarize CLI 工具的 config.json 文件。**触发条件**：用户需要配置/修改/验证 summarize 配置、切换 API 代理、修复配置错误、查看配置技巧。
agent_created: false
---

# summarize-config

配置 `@steipete/summarize` CLI 工具的 `~/.summarize/config.json` 文件。

## 功能

- 交互式配置向导，引导用户正确填写配置
- 自动验证 JSON 语法，避免常见错误
- 支持多代理切换（DashScope、aicodemirror 等）
- 修复配置文件中的语法错误
- 显示当前配置和配置技巧

## 配置结构

```json
{
  "model": "provider/model-name",
  "anthropic": {
    "baseUrl": "https://proxy-url"
  },
  "openai": {
    "baseUrl": "https://proxy-url/v1"
  },
  "apiKeys": {
    "anthropic": "key",
    "openai": "key"
  }
}
```

## 常见错误

1. **JSON 语法错误** - 最后一个属性后不能有逗号
2. **model 格式错误** - 必须有 provider 前缀（如 `anthropic/claude-3-5-sonnet`）
3. **baseUrl 路径错误** - Anthropic 不需要 `/v1/messages`，OpenAI 需要 `/v1`

## 使用示例

```
# 配置 summarize
配置 summarize 使用 aicodemirror 代理

# 切换代理
把 summarize 切换到 DashScope

# 修复配置
summarize 配置有语法错误，帮我修复

# 查看配置
显示当前 summarize 配置
```

## 命令

| 命令 | 说明 |
|------|------|
| `summarize-config show` | 显示当前配置 |
| `summarize-config validate` | 验证配置文件语法 |
| `summarize-config fix` | 自动修复常见错误 |
| `summarize-config set-anthropic <baseUrl> <apiKey>` | 设置 Anthropic 代理 |
| `summarize-config set-openai <baseUrl> <apiKey>` | 设置 OpenAI 代理 |
| `summarize-config switch <provider>` | 切换当前使用的代理 |