---
name: bilibili-video-notes
description: B站视频内容分析与笔记生成工具。**优先使用 bili video --ai 获取 AI 摘要（秒级完成）**，如需详细图文笔记才进行帧提取分析。支持本地视频文件分析。触发条件：用户提供B站视频BV号或链接并要求分析/生成笔记，或用户提供本地视频文件路径。
type: skill
agent_created: true
version: 3.0
original_skill: bilibili-analyzer
---

# Bilibili Video Notes Skill v3.0

基于原 bilibili-analyzer 的优化版本，**v3.0 新增优先使用 bili-cli 获取 AI 摘要**。

## v3.0 核心改进

### AI 摘要作为内容参考（秒级预览）

```bash
# 首选：快速获取 AI 摘要作为参考
bili video BV1xx --ai --json  # < 1秒
```

**用途**：
- 快速了解视频内容主题
- 作为帧分析的内容参考
- 不直接生成笔记（仅参考）

### 工作流程优先级

```
Step 1: bili video BV1xx --ai --json  → 获取 AI 摘要参考（< 1秒）
        ↓ 摘要作为参考信息
Step 2: 帧提取 + Vision API          → 生成图文笔记
```

**判断逻辑**：
- AI 摘要 >= 30字：作为参考信息添加到笔记概述
- AI 摘要 < 30字或为空：跳过参考，直接帧分析

## 版本对比

| 特性 | v1.0 (原版) | v2.0 | **v3.0** |
|------|------------|------|----------|
| 获取摘要 | 逐帧 OCR | 逐帧 OCR | **bili --ai（秒级）** |
| 获取字幕 | ❌ | ❌ | **bili --subtitle** |
| 下载方式 | .NET | .NET/yt-dlp | **bili/yt-dlp** |
| 帧数控制 | 全量 | 智能采样 | 智能采样 |
| 分析方式 | 5 Agent 并行 | 单线程 | **优先 bili-cli** |

## 核心改进

### 1. 智能下载方式选择

```
检测环境 → 有.NET 10 SDK → 使用 prepare.cs（原生B站API）
                ↓ 无.NET
           检测 yt-dlp → 使用 yt-dlp + ffmpeg（通用方案）
```

**优势**：
- .NET 方式：直接调用 B站 API，下载速度快，无第三方依赖
- yt-dlp 方式：兼容性更好，无需安装 .NET SDK

### 2. 智能采样避免页面切换帧

原版问题：按固定 fps 拆帧，可能截取到页面切换中间帧（黑屏/半透明）

**改进方案**：
```
Step 1: ffmpeg 场景变化检测
        -vf "select='gt(scene,0.3)',fps=0.5"
        只选取场景变化明显的帧

Step 2: 相邻帧相似度去重（PSNR/SSIM）
        相似度 >= 80% 的帧只保留第一帧

Step 3: 限制最大帧数
        长视频最多120帧，短视频60帧
```

**效果**：
- 避免"正在切换页面"的中间帧
- 减少相似帧数量（减少 30-50%）
- 保留有意义的内容帧

### 3. 单线程稳定分析

原版问题：5个 Agent 并行分析，每个输出超 32MB 被截断

**改进方案**：
- 单线程 Python 脚本逐帧调用 Vision API
- 每帧返回结构化 JSON（约 500-800 tokens）
- 输出可控，不会超限

### 4. 本地视频支持（新增）

**适用场景**：
- 已下载的视频，避免重复下载
- 非 B站来源的视频（如本地录制、其他平台下载）
- 网络受限环境

**工作方式**：
```
提供本地视频路径 → ffprobe获取时长 → 复制/硬链接到输出目录 → 执行拆帧和分析
```

**自动标题推断**：
- 从文件名提取（移除后缀、BV号前缀等）
- 可用 `--title` 参数覆盖

## 安装依赖

### 方式1：.NET 方式（推荐）

```bash
# 安装 .NET 10 SDK
# Windows: https://dotnet.microsoft.com/download/dotnet/10.0
# macOS/Linux: 
wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
bash dotnet-install.sh --channel 10.0

# 安装 ffmpeg
# Windows: scoop install ffmpeg 或 choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Python 依赖
pip install requests pillow
```

### 方式2：yt-dlp 方式（备选）

```bash
# 安装 yt-dlp
pip install yt-dlp

# 安装 ffmpeg（同上）

# Python 依赖
pip install requests pillow
```

## 使用方式

### 方式1：首选 - 使用 bili-cli 获取 AI 摘要（推荐）

```bash
# 直接获取 B站 AI 摘要（秒级完成）
bili video BV1xx411c7mD --ai

# 同时获取字幕（如有）
bili video BV1xx411c7mD --subtitle

# 获取视频元数据
bili video BV1xx411c7mD --json
```

**适用场景**：快速了解视频内容，获取官方 AI 摘要

### 方式2：详细图文笔记（需要帧分析时）

```bash
# 通过 skill 调用帧分析
/skill bilibili-video-notes BV1xx411c7mD --frames

# 或直接运行 Python 脚本
python scripts/analyze.py BV1xx411c7mD -o ./output
```

**适用场景**：需要图文并茂的详细笔记、教程类视频、实操步骤记录

### 方式3：本地视频分析

```bash
/skill bilibili-video-notes --video ./my_video.mp4
python scripts/analyze.py --video ./video.mp4 --title "标题" -o ./output
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `bvid` | B站视频BV号或完整URL | 与 --video 互斥 |
| `--video, -v` | **本地视频文件路径** | 与 bvid 互斥 |
| `--title, -t` | **视频标题（本地视频专用）** | 从文件名推断 |
| `-o, --output` | 输出目录 | `./output/{bvid}` |
| `-f, --frames` | 最大分析帧数 | 120 |
| `--scene-threshold` | 场景变化阈值 | 0.3 |
| `--similarity` | 相似帧去重阈值 | 0.80 |
| `--no-download` | 跳过下载（仅B站模式） | false |
| `--no-dedup` | 跳过去重 | false |

### 本地视频模式说明

当使用 `--video` 参数时：

1. **跳过下载环节**：直接使用提供的视频文件
2. **自动获取时长**：使用 ffprobe 读取视频元数据
3. **标题推断**：从文件名提取，或用 `--title` 指定
4. **输出位置**：默认在视频同目录创建 `{文件名}_分析/` 文件夹

## 输出结构

```
output/{bvid}/
├── {title}_笔记.md      # 生成的图文笔记
├── video.mp4            # 下载的视频文件
└── images/              # 帧图片目录（已去重）
    ├── frame_0001.jpg
    ├── frame_0002.jpg
    └── ...
```

## 工作流程

### Step 1: 检测环境并下载

```bash
# 检测 .NET SDK
dotnet --version >= 10.0 → 使用 prepare.cs

# 无.NET则检测 yt-dlp
yt-dlp --version → 使用 yt-dlp download
```

### Step 2: 智能采样拆帧

```bash
# 场景变化检测 + fps 控制
ffmpeg -i video.mp4 \
  -vf "select='gt(scene,0.3)',fps=0.2" \
  -vframes 120 \
  -q:v 2 images/frame_%04d.jpg
```

**场景变化检测原理**：
- `gt(scene,0.3)`：只选取场景变化 > 30% 的帧
- 页面切换中间帧通常变化很小，会被跳过
- 实际内容帧变化明显，会被保留

### Step 3: 相似帧去重

```bash
# 使用 prepare.cs 内置的去重功能
# 或 Python 脚本后处理
```

### Step 4: 单线程分析

```python
# 逐帧调用 Vision API
for frame in sampled_frames:
    result = analyze_frame(frame)  # 返回 JSON
    results.append(result)
```

### Step 5: 生成笔记

根据分析结果生成结构化 Markdown。

## 智能采样策略

| 视频时长 | 场景阈值 | fps | 最大帧数 | 预估分析时间 |
|----------|---------|-----|----------|-------------|
| <10分钟 | 0.25 | 0.5 | 60 | 60秒 |
| 10-30分钟 | 0.30 | 0.3 | 90 | 90秒 |
| >30分钟 | 0.35 | 0.2 | 120 | 120秒 |

## Vision API 配置

读取 `~/.summarize/config.json` 配置：

```json
{
  "apiKeys": {
    "zhipu": "xxx.yyy",       // GLM-OCR（推荐，专业OCR模型）
    "anthropic": "sk-xxx",    // DashScope 代理
    "openai": "sk-xxx"        // OpenAI API
  }
}
```

支持 API（按优先级）：
1. **智谱 GLM-OCR**（推荐）- 专业 OCR 模型，识别文字更准确
2. GLM-4V-Flash - 通用视觉模型
3. DashScope API（国内代理）
4. Anthropic API
5. OpenAI API

GLM-OCR 文档: https://docs.bigmodel.cn/cn/guide/tools/zhipu-ocr

## 常见问题

### Q: .NET SDK 版本不匹配？
A: prepare.cs 需要 .NET 10，脚本会自动检测并退到 yt-dlp 方式

### Q: 场景检测漏掉重要帧？
A: 降低 `--scene-threshold`（如 0.25），或禁用场景检测改用固定 fps

### Q: Vision API 超时？
A: 减少帧数 `-f 60`，或增加超时时间（脚本默认 90秒）

### Q: yt-dlp 下载失败？
A: 尝试使用 cookies：
```bash
yt-dlp --cookies-from-browser chrome "URL"
```

### Q: 本地视频无法分析？
A: 确保：
- ffmpeg 和 ffprobe 已安装
- 视频格式支持（MP4、MKV、AVI、MOV等）
- 文件路径正确（使用绝对路径更可靠）

### Q: 如何分析已下载的 B站视频？
A: 直接使用本地视频模式：
```bash
python analyze.py --video ./已下载的视频.mp4 --title "原标题"
```

## 质量检查清单

生成笔记前检查：

### 内容质量
- [ ] 内容按章节组织，非时间线流水账
- [ ] 章节结构清晰，有逻辑顺序
- [ ] 包含概述和总结
- [ ] 不看视频也能理解

### 图文对应
- [ ] 每张图片标注帧号
- [ ] 图片描述准确反映实际内容
- [ ] 代码标注来源帧号
- [ ] 不插入无关图片（如页面切换帧）

### 代码质量
- [ ] 代码来自截图，非编造
- [ ] 代码片段完整可复制
- [ ] 有完整代码汇总章节

## 示例输出

```markdown
# 视频标题

> 视频来源: [B站视频 BV1xx](https://www.bilibili.com/video/BV1xx)
> 作者: xxx | 时长: 15:30

## 概述

![frame_0001: 视频封面](./images/frame_0001.jpg)

核心功能介绍...

## 第一章：安装配置

![frame_0010: 安装界面](./images/frame_0010.jpg)

<!-- 代码来自 frame_0015 -->
```bash
pip install xxx
```

## 总结

- 要点1
- 要点2

## 截图索引

| 帧号 | 时间 | 内容描述 |
|------|------|----------|
| frame_0001 | 0:00 | 视频封面 |
| frame_0010 | 0:50 | 安装界面 |
```

## Tags

`bilibili`, `video-analysis`, `ai`, `frame-extraction`, `markdown`, `tutorial`, `smart-sampling`, `scene-detection`, `yt-dlp`, `ffmpeg`, `dotnet`

## Compatibility

- Claude Code: Yes
- OpenClaw: Yes
- Codex: Yes