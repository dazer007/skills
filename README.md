# My Agent Skills

Agent skills collection - 技能生态通用。

## Platform Support

本仓库技能支持多平台，生态通用：

| Platform | Description |
|----------|-------------|
| **Claude Code** | Anthropic官方CLI |
| **openClaw** | 兼容生态任意国产龙虾：WorkBuddy、QClaw等 |

## Skills

| Skill | Description |
|-------|-------------|
| [xjtu-doctor-scraper](./xjtu-doctor-scraper) | 爬取西安交通大学第一附属医院官网医生列表 |

## Install

```bash
# Claude Code / openClaw 通用安装命令
npx skills add dazer007/my-skills@xjtu-doctor-scraper

# 或手动克隆安装
git clone https://github.com/dazer007/my-skills.git
cp -r my-skills/xjtu-doctor-scraper ~/.claude/skills/   # Claude Code
cp -r my-skills/xjtu-doctor-scraper ~/.openclaw/skills/ # openClaw
```

## Discover More Skills

探索更多技能生态：

| Platform | URL |
|----------|-----|
| skillhub.cn | https://skillhub.cn |
| skills.sh | https://skills.sh |
| clawhub.ai | https://clawhub.ai |

## Usage

安装后通过斜杠命令调用：

```
/xjtu-doctor-scraper
```