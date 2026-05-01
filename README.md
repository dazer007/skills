# My Agent Skills

Agent skills collection - 技能生态通用。

## Platform Support

本仓库技能支持多平台，生态通用：

| Platform | Description |
|----------|-------------|
| **Claude Code** | Anthropic官方CLI |
| **OpenClaw** | 兼容生态任意国产龙虾：WorkBuddy、QClaw等 |

## Skills

本仓库包含的技能：

| Skill | Description |
|-------|-------------|
| [xjtu-doctor-scraper](./xjtu-doctor-scraper) | 爬取西安交通大学第一附属医院官网医生列表 |

## Installed Skills

本环境已安装的技能：

| Skill | Description | Install |
|-------|-------------|---------|
| `github` | 使用 `gh` CLI 与 GitHub 交互，处理 PR、CI、Issues 等 | [skillhub.cn](https://skillhub.cn/skills/github) / [skills.sh](https://skills.sh/github/awesome-copilot/gh-cli) / [clawhub.ai](https://clawhub.ai/steipete/github) / [GitHub](https://github.com/github/awesome-copilot/tree/main/skills/gh-cli) |
| `bilibili-cli` | B站CLI工具：视频详情、字幕、搜索、热门、评论、互动等 | [skills.sh](https://skills.sh/jackwener/bilibili-cli/bilibili-cli) / [GitHub](https://github.com/public-clis/bilibili-cli) / [ModelScope](https://www.modelscope.cn/skills/@hwj123hwj/bilibili-cli) |
| `bilibili-analyzer` | B站视频深度分析：下载视频拆帧、AI分析生成专题文档或实操教程 | [skills.sh](https://skills.sh/aidotnet/moyucode/bilibili-analyzer) / [ModelScope](https://www.modelscope.cn/skills/@aidotnet/bilibili-analyzer) / [GitHub](https://github.com/AIDotNet/MoYuCode/blob/main/skills/tools/bilibili-analyzer/SKILL.md) |

调用方式：`/github`、`/bilibili-cli`、`/bilibili-analyzer`

---

## Install

```bash
# Claude Code / OpenClaw 通用安装命令
npx skills add dazer007/my-skills@xjtu-doctor-scraper
# Target a specific agent 指定一个agent代理，写入：~/.claude-code/
npx skills add jackwener/bilibili-cli -a claude-code

# 使用国内ModelScope安装地址安装
npx skills add https://www.modelscope.cn/skills/@hwj123hwj/bilibili-cli     -a openclaw
npx skills add https://www.modelscope.cn/skills/@aidotnet/bilibili-analyzer -a claude-code

# 从GitHub仓库安装指定技能
npx skills add https://github.com/aidotnet/moyucode      --skill bilibili-analyzer
npx skills add https://github.com/github/awesome-copilot --skill gh-cli

# 或手动克隆安装
git clone https://github.com/dazer007/my-skills.git
cp -r my-skills/xjtu-doctor-scraper ~/.claude/skills/   # Claude Code
cp -r my-skills/xjtu-doctor-scraper ~/.openclaw/skills/ # OpenClaw
```

### 国内用户加速

如果 `npx skills add` 访问GitHub失败，配置git全局代理：

```bash
# 配置git全局代理（使用ghfast.top）
git config --global url.https://ghfast.top/https://github.com/.insteadof https://github.com/

# 然后正常使用npx安装
npx skills add dazer007/my-skills@xjtu-doctor-scraper

# 安装后可取消代理（可选）
git config --global --unset url.https://ghfast.top/https://github.com/.insteadof
```

或手动克隆：

```bash
git clone https://ghfast.top/https://github.com/dazer007/my-skills.git
cp -r my-skills/xjtu-doctor-scraper ~/.claude/skills/
```

网络实在不行？灵活处理：

- **手工下载ZIP**: 浏览器打开 https://ghfast.top/https://github.com/dazer007/my-skills/archive/refs/heads/master.zip ，解压后复制技能目录
- **从国内生态复制**: 访问 skillhub.cn / clawhub.ai 搜索同名技能，直接一键安装

## Discover More Skills

探索更多技能生态：

| Platform | URL |
|----------|-----|
| skills.sh | https://skills.sh |
| modelscope.cn | https://www.modelscope.cn/skills |
| clawhub.ai | https://clawhub.ai |
| skillhub.cn | https://skillhub.cn |
| skillkit.io | https://skillkit.io |

---

## 国内推送GitHub私有仓库

国内直连GitHub often受限，推荐使用 [ghfast.top](https://ghfast.top/) 代理。

### 拉取/克隆（公开仓库）

直接在URL前加代理前缀：

```bash
# 原始URL
git clone https://github.com/dazer007/my-skills.git

# 使用代理
git clone https://ghfast.top/https://github.com/dazer007/my-skills.git
```

### 推送私有仓库

私有仓库推送需要GitHub Personal Access Token：

**1. 创建Token**

访问 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

勾选权限：`repo`（完整仓库访问）

**2. 配置推送**

```bash
# 设置remote（带token）
git remote set-url origin https://用户名:TOKEN@ghfast.top/https://github.com/用户名/仓库名.git

# 推送
git push -u origin master

# 推送完成后移除token（安全考虑）
git remote set-url origin https://github.com/用户名/仓库名.git
```

**3. 一行命令推送**

```bash
git remote set-url origin https://dazer007:ghp_xxx@ghfast.top/https://github.com/dazer007/my-skills.git && \
git push && \
git remote set-url origin https://github.com/dazer007/my-skills.git
```

### 注意事项

- ⚠️ Token不要提交到仓库，推送后立即移除
- ✅ 代理支持HTTPS，不支持SSH
- ✅ 公开仓库拉取无需token

---

## Usage

安装后通过斜杠命令调用：

```
/xjtu-doctor-scraper
```