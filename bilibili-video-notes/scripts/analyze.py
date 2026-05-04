#!/usr/bin/env python3
"""
Bilibili Video Notes Generator v3.0
优先使用 bili-cli 获取 AI 摘要，失败时退到帧分析

改进点：
1. v3.0: 优先使用 bili video --ai 获取摘要（秒级完成）
2. v3.0: 支持 bili video --subtitle 获取字幕
3. v2.0: 智能采样：场景变化检测 + 相似帧去重
4. v2.0: 单线程分析：避免 Agent 输出超限
5. v2.0: 支持本地视频文件：直接分析已下载的视频

Usage:
    # 首选：使用 bili-cli 获取 AI 摘要（秒级）
    bili video BV1xx411c7mD --ai

    # 备选：帧分析生成图文笔记
    python analyze.py BV1xx411c7mD -o ./output --frames

    # 本地视频分析
    python analyze.py --video ./local_video.mp4 -o ./output
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)


class BiliCliFetcher:
    """使用 bili-cli 获取视频信息（优先方式）"""

    @staticmethod
    def check_bili_cli() -> bool:
        """检测 bili 命令是否可用"""
        try:
            result = subprocess.run(
                ["bili", "--help"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def get_video_info(bvid: str) -> Optional[Dict]:
        """使用 bili video --ai 获取视频信息和 AI 摘要"""
        try:
            result = subprocess.run(
                ["bili", "video", bvid, "--ai", "--json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                # 解析 YAML/JSON 输出
                data = BiliCliFetcher._parse_bili_output(result.stdout)
                return data
        except Exception as e:
            print(f"bili-cli 获取失败: {str(e)[:50]}")
        return None

    @staticmethod
    def get_subtitle(bvid: str) -> Optional[str]:
        """使用 bili video --subtitle 获取字幕"""
        try:
            result = subprocess.run(
                ["bili", "video", bvid, "--subtitle"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                # 解析字幕文本
                return BiliCliFetcher._extract_subtitle(result.stdout)
        except:
            pass
        return None

    @staticmethod
    def _parse_bili_output(output: str) -> Dict:
        """解析 bili 命令输出"""
        data = {
            "title": "",
            "author": "",
            "duration": 0,
            "view_count": 0,
            "url": f"https://www.bilibili.com/video/{bvid}",
            "ai_summary": "",
            "subtitle": "",
        }

        # 解析 YAML 格式输出
        lines = output.split('\n')
        for line in lines:
            if line.startswith('title:'):
                data["title"] = line.split(':', 1)[1].strip().strip("'")
            elif line.startswith('owner:') or 'name:' in line:
                # 解析 owner name
                if 'name:' in line:
                    data["author"] = line.split('name:')[1].strip().strip("'")
            elif line.startswith('duration_seconds:'):
                data["duration"] = int(line.split(':')[1].strip())
            elif 'view:' in line:
                data["view_count"] = int(line.split('view:')[1].strip())
            elif line.startswith('ai_summary:'):
                data["ai_summary"] = line.split(':', 1)[1].strip()

        # 如果没解析到，尝试从 data 字块提取
        if not data["ai_summary"]:
            ai_match = re.search(r'ai_summary:\s*(.+)', output)
            if ai_match:
                data["ai_summary"] = ai_match.group(1).strip()

        return data

    @staticmethod
    def _extract_subtitle(output: str) -> str:
        """从 bili 输出提取字幕文本"""
        # 提取 subtitle items
        text_lines = []
        in_subtitle = False
        for line in output.split('\n'):
            if 'subtitle:' in line or 'items:' in line:
                in_subtitle = True
            elif in_subtitle and line.strip().startswith('text:'):
                text = line.split('text:')[1].strip().strip("'")
                text_lines.append(text)
        return '\n'.join(text_lines)


class VideoInfoExtractor:
    """视频信息提取器（支持本地文件）"""

    @staticmethod
    def get_video_duration(video_path: Path) -> int:
        """使用 ffprobe 获取视频时长（秒）"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return int(duration)
        except:
            pass
        return 0

    @staticmethod
    def get_video_resolution(video_path: Path) -> tuple:
        """获取视频分辨率"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                str(video_path)
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
        except:
            pass
        return 0, 0

    @staticmethod
    def extract_title_from_filename(video_path: Path) -> str:
        """从文件名提取标题"""
        name = video_path.stem
        # 移除常见后缀
        name = re.sub(r'[_\-\s]*(MP4|mp4|avi|mkv|flv|mov)$', '', name, flags=re.IGNORECASE)
        # 移除 BV号前缀
        name = re.sub(r'^BV[a-zA-Z0-9]+[_\-\s]*', '', name)
        # 清理特殊字符
        name = re.sub(r'[^\w\s\-一-鿿]', ' ', name)
        return name.strip() or "本地视频"


class EnvironmentDetector:
    """环境检测器"""

    @staticmethod
    def check_dotnet() -> bool:
        """检测 .NET 10 SDK"""
        try:
            result = subprocess.run(
                ["dotnet", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                # 检查版本是否 >= 10.0
                major = int(version.split('.')[0])
                return major >= 10
        except:
            pass
        return False

    @staticmethod
    def check_ytdlp() -> bool:
        """检测 yt-dlp"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            pass
        return False

    @staticmethod
    def check_ffmpeg() -> bool:
        """检测 ffmpeg"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            pass
        return False


class FrameDeduplicator:
    """相似帧去重器"""

    @staticmethod
    def calculate_similarity_ffmpeg(frame1: Path, frame2: Path) -> float:
        """使用 ffmpeg 计算帧相似度（SSIM）"""
        try:
            result = subprocess.run([
                "ffmpeg", "-i", str(frame1), "-i", str(frame2),
                "-lavfi", "ssim", "-f", "null", "-"
            ], capture_output=True, text=True, timeout=30)

            # 解析 SSIM 输出
            match = re.search(r"All:(\d+\.?\d*)", result.stderr)
            if match:
                return float(match.group(1))
        except:
            pass
        return 0.0

    @staticmethod
    def deduplicate_frames(images_dir: Path, threshold: float = 0.80) -> int:
        """去重相似帧"""
        frames = sorted(images_dir.glob("frame_*.jpg"))
        if len(frames) < 2:
            return len(frames)

        print(f"  去重相似帧（阈值: {threshold:.0%}）...")

        to_delete = []
        for i in range(len(frames) - 1):
            if frames[i] in to_delete:
                continue

            similarity = FrameDeduplicator.calculate_similarity_ffmpeg(
                frames[i], frames[i + 1]
            )

            if similarity >= threshold:
                to_delete.append(frames[i + 1])

        # 删除相似帧
        for frame in to_delete:
            try:
                frame.unlink()
            except:
                pass

        # 重新编号
        remaining = sorted(images_dir.glob("frame_*.jpg"))
        for i, frame in enumerate(remaining):
            new_name = images_dir / f"frame_{i+1:04d}.jpg"
            if frame != new_name:
                # 使用临时名避免冲突
                temp_name = images_dir / f"temp_{i+1:04d}.jpg"
                frame.rename(temp_name)

        # 重命名临时文件
        temps = sorted(images_dir.glob("temp_*.jpg"))
        for i, temp in enumerate(temps):
            final_name = images_dir / f"frame_{i+1:04d}.jpg"
            temp.rename(final_name)

        final_count = len(list(images_dir.glob("frame_*.jpg")))
        print(f"  去重完成: {len(frames)} → {final_count} 帧（删除 {len(to_delete)} 帧）")
        return final_count


class BilibiliAnalyzer:
    """B站视频分析器 v2.0"""

    # 智能采样策略
    SAMPLING_STRATEGY = {
        "short": {"max_duration": 600, "fps": 0.5, "max_frames": 60, "scene_threshold": 0.25},
        "medium": {"max_duration": 1800, "fps": 0.3, "max_frames": 90, "scene_threshold": 0.30},
        "long": {"max_duration": float('inf'), "fps": 0.2, "max_frames": 120, "scene_threshold": 0.35},
    }

    # Vision API 配置
    API_CONFIG = {
        "dashscope": {
            "url": "https://coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages",
            "model": "glm-5",
        },
        "anthropic": {
            "url": "https://api.anthropic.com/v1/messages",
            "model": "claude-sonnet-4-20250514",
        },
    }

    def __init__(self, bvid: str = None, output_dir: str = "./output",
                 local_video: str = None, video_title: str = None,
                 max_frames: int = None, scene_threshold: float = None,
                 similarity_threshold: float = 0.80):
        """
        初始化分析器

        参数：
            bvid: B站视频BV号（用于下载）
            output_dir: 输出目录
            local_video: 本地视频文件路径（跳过下载）
            video_title: 视频标题（用于本地视频）
            max_frames: 最大帧数
            scene_threshold: 场景变化阈值
            similarity_threshold: 相似帧去重阈值
        """
        # 本地视频模式
        self.local_video_path = None
        self.is_local_mode = False

        if local_video:
            self.local_video_path = Path(local_video)
            if not self.local_video_path.exists():
                raise FileNotFoundError(f"本地视频不存在: {local_video}")
            self.is_local_mode = True
            # 使用文件名作为标识符
            self.bvid = self.local_video_path.stem[:20]  # 截取前20字符作为标识
        elif bvid:
            self.bvid = self._parse_bvid(bvid)
        else:
            raise ValueError("必须提供 bvid 或 local_video 参数")

        # 输出目录
        if self.is_local_mode:
            # 本地视频模式：输出到视频同目录或指定目录
            if output_dir == "./output":
                self.output_dir = self.local_video_path.parent / f"{self.bvid}_分析"
            else:
                self.output_dir = Path(output_dir) / self.bvid
        else:
            self.output_dir = Path(output_dir) / self.bvid

        self.images_dir = self.output_dir / "images"
        self.video_title_override = video_title
        self.max_frames = max_frames
        self.scene_threshold = scene_threshold
        self.similarity_threshold = similarity_threshold

        self.video_info = {}
        self.frame_analysis = []
        self.api_key = None
        self.api_type = None

        # 检测环境
        self.has_dotnet = EnvironmentDetector.check_dotnet()
        self.has_ytdlp = EnvironmentDetector.check_ytdlp()
        self.has_ffmpeg = EnvironmentDetector.check_ffmpeg()

        # 本地视频模式下检测 ffprobe
        if self.is_local_mode:
            self.has_ffprobe = self._check_ffprobe()

    def _parse_bvid(self, input_str: str) -> str:
        """解析BV号"""
        if input_str.startswith("BV"):
            return input_str
        match = re.search(r"BV[a-zA-Z0-9]+", input_str)
        if match:
            return match.group()
        raise ValueError(f"无法解析BV号: {input_str}")

    def _check_ffprobe(self) -> bool:
        """检测 ffprobe"""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            pass
        return False

    def _load_api_config(self) -> bool:
        """加载 Vision API 配置"""
        config_path = Path.home() / ".summarize" / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text())
            if "apiKeys" in config:
                if config["apiKeys"].get("anthropic"):
                    self.api_key = config["apiKeys"]["anthropic"]
                    self.api_type = "dashscope"
                    return True

        if os.environ.get("ANTHROPIC_API_KEY"):
            self.api_key = os.environ["ANTHROPIC_API_KEY"]
            self.api_type = "anthropic"
            return True

        return False

    def _run_command(self, cmd: list, timeout: int = 300) -> tuple:
        """运行命令"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"

    def print_environment_status(self):
        """打印环境状态"""
        print(f"\n{'='*50}")
        print(f"环境检测:")
        print(f"  .NET 10 SDK: {'✓ 可用' if self.has_dotnet else '✗ 不可用'}")
        print(f"  yt-dlp: {'✓ 可用' if self.has_ytdlp else '✗ 不可用'}")
        print(f"  ffmpeg: {'✓ 可用' if self.has_ffmpeg else '✗ 不可用'}")
        print(f"{'='*50}\n")

    def get_video_info(self) -> dict:
        """获取视频信息"""
        # 本地视频模式
        if self.is_local_mode:
            return self._get_local_video_info()

        # B站在线视频模式
        url = f"https://www.bilibili.com/video/{self.bvid}"

        print(f"[1/5] 获取视频信息: {self.bvid}")

        # 优先使用 yt-dlp 获取信息（更可靠）
        if self.has_ytdlp:
            code, stdout, stderr = self._run_command([
                "yt-dlp", "--print-json", "--no-download", url
            ], timeout=30)

            if code == 0:
                try:
                    data = json.loads(stdout)
                    self.video_info = {
                        "title": data.get("title", "未知标题"),
                        "author": data.get("uploader", "未知作者"),
                        "duration": data.get("duration", 0),
                        "view_count": data.get("view_count", 0),
                        "description": data.get("description", ""),
                        "url": url,
                    }
                    return self.video_info
                except:
                    pass

        # 备用：直接调用 B站 API
        return self._get_video_info_api()

    def _get_local_video_info(self) -> dict:
        """获取本地视频信息"""
        print(f"[1/5] 获取本地视频信息: {self.local_video_path.name}")

        # 获取时长
        duration = VideoInfoExtractor.get_video_duration(self.local_video_path)
        width, height = VideoInfoExtractor.get_video_resolution(self.local_video_path)

        # 获取标题
        if self.video_title_override:
            title = self.video_title_override
        else:
            title = VideoInfoExtractor.extract_title_from_filename(self.local_video_path)

        self.video_info = {
            "title": title,
            "author": "本地视频",
            "duration": duration,
            "view_count": 0,
            "description": f"本地视频文件: {self.local_video_path.name}",
            "url": str(self.local_video_path),
            "resolution": f"{width}x{height}" if width else "未知",
            "file_size": self.local_video_path.stat().st_size / (1024 * 1024),  # MB
        }

        return self.video_info

    def _get_video_info_api(self) -> dict:
        """直接调用 B站 API 获取信息"""
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={self.bvid}"
        try:
            resp = requests.get(api_url, timeout=10)
            data = resp.json()
            if data["code"] == 0:
                info = data["data"]
                self.video_info = {
                    "title": info["title"],
                    "author": info["owner"]["name"],
                    "duration": info["duration"],
                    "view_count": info["stat"]["view"],
                    "description": info["desc"],
                    "url": f"https://www.bilibili.com/video/{self.bvid}",
                }
                return self.video_info
        except Exception as e:
            print(f"API 获取失败: {e}")

        return {"title": self.bvid, "url": f"https://www.bilibili.com/video/{self.bvid}"}

    def download_video_dotnet(self) -> bool:
        """使用 .NET prepare.cs 下载"""
        script_path = Path(__file__).parent / "prepare.cs"
        if not script_path.exists():
            print("prepare.cs 脚本不存在")
            return False

        url = self.video_info.get("url", f"https://www.bilibili.com/video/{self.bvid}")

        print("  使用 .NET prepare.cs 下载...")

        code, stdout, stderr = self._run_command([
            "dotnet", "run", str(script_path),
            url, "-o", str(self.output_dir),
            "--video-only"
        ], timeout=600)

        video_path = self.output_dir / "video.mp4"
        if code == 0 and video_path.exists():
            print(f"  下载完成: {video_path}")
            return True

        print(f"  .NET 下载失败: {stderr[:200]}")
        return False

    def download_video_ytdlp(self) -> bool:
        """使用 yt-dlp 下载"""
        url = self.video_info.get("url", f"https://www.bilibili.com/video/{self.bvid}")
        video_path = self.output_dir / "video.mp4"

        print("  使用 yt-dlp 下载...")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 尝试不同画质
        formats = [
            "30064+30280",  # 720p
            "30032+30280",  # 480p
            "30016+30280",  # 360p
            "bestvideo+bestaudio/best"
        ]

        for fmt in formats:
            code, stdout, stderr = self._run_command([
                "yt-dlp", "-f", fmt, "-o", str(video_path),
                url, "--no-playlist", "--merge-output-format", "mp4"
            ], timeout=600)

            if code == 0 and video_path.exists():
                print(f"  下载完成: {video_path}")
                return True

        print(f"  yt-dlp 下载失败")
        return False

    def download_video(self) -> bool:
        """下载视频（智能选择方式）"""
        # 本地视频模式：复制或链接视频文件
        if self.is_local_mode:
            return self._prepare_local_video()

        print(f"[2/5] 下载视频...")

        video_path = self.output_dir / "video.mp4"
        if video_path.exists():
            print(f"  视频已存在: {video_path}")
            return True

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 优先使用 .NET 方式
        if self.has_dotnet:
            if self.download_video_dotnet():
                return True

        # 退到 yt-dlp 方式
        if self.has_ytdlp:
            if self.download_video_ytdlp():
                return True

        print("下载失败：请安装 .NET 10 SDK 或 yt-dlp")
        return False

    def _prepare_local_video(self) -> bool:
        """准备本地视频（复制或创建硬链接）"""
        print(f"[2/5] 准备本地视频...")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        video_path = self.output_dir / "video.mp4"

        if video_path.exists():
            print(f"  视频已存在: {video_path}")
            return True

        # 尝试创建硬链接（节省空间）
        try:
            if os.name == 'nt':  # Windows
                # Windows 使用复制
                import shutil
                shutil.copy2(str(self.local_video_path), str(video_path))
                print(f"  复制视频: {self.local_video_path} -> {video_path}")
            else:  # Linux/macOS
                os.link(str(self.local_video_path), str(video_path))
                print(f"  创建硬链接: {video_path}")
        except Exception as e:
            # 硬链接失败，使用复制
            print(f"  硬链接失败，使用复制: {str(e)[:50]}")
            import shutil
            shutil.copy2(str(self.local_video_path), str(video_path))

        if video_path.exists():
            file_size = video_path.stat().st_size / (1024 * 1024)
            print(f"  视频大小: {file_size:.1f} MB")
            return True

        print("准备本地视频失败")
        return False

    def extract_frames_smart(self) -> int:
        """智能采样拆帧（场景变化检测）"""
        video_path = self.output_dir / "video.mp4"
        if not video_path.exists() or not self.has_ffmpeg:
            return self._extract_frames_fallback()

        self.images_dir.mkdir(parents=True, exist_ok=True)

        # 计算采样策略
        duration = self.video_info.get("duration", 0)
        strategy = self._get_sampling_strategy(duration)

        fps = strategy["fps"]
        max_frames = strategy["max_frames"]
        scene_threshold = self.scene_threshold or strategy["scene_threshold"]

        print(f"[3/5] 智能采样拆帧:")
        print(f"  fps={fps:.2f}, 场景阈值={scene_threshold:.0%}, 最大帧={max_frames}")

        # 场景变化检测 + fps 控制
        # select='gt(scene,N)' 选取场景变化 > N 的帧
        code, stdout, stderr = self._run_command([
            "ffmpeg", "-i", str(video_path),
            "-vf", f"select='gt(scene,{scene_threshold})',fps={fps}",
            "-vframes", str(max_frames),
            "-q:v", "2",
            str(self.images_dir / "frame_%04d.jpg")
        ], timeout=120)

        if code != 0:
            print(f"  场景检测拆帧失败，尝试普通拆帧...")
            return self._extract_frames_fallback()

        frames = list(self.images_dir.glob("frame_*.jpg"))
        print(f"  生成 {len(frames)} 帧")
        return len(frames)

    def _extract_frames_fallback(self) -> int:
        """普通拆帧（备用）"""
        video_path = self.output_dir / "video.mp4"
        if not video_path.exists():
            print("视频文件不存在")
            return 0

        self.images_dir.mkdir(parents=True, exist_ok=True)

        duration = self.video_info.get("duration", 0)
        strategy = self._get_sampling_strategy(duration)

        fps = strategy["fps"]
        max_frames = strategy["max_frames"]

        print(f"  普通拆帧: fps={fps:.2f}, max_frames={max_frames}")

        code, stdout, stderr = self._run_command([
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps={fps}",
            "-vframes", str(max_frames),
            "-q:v", "2",
            str(self.images_dir / "frame_%04d.jpg")
        ], timeout=120)

        if code != 0:
            print(f"ffmpeg 拆帧失败: {stderr[:100]}")
            return 0

        frames = list(self.images_dir.glob("frame_*.jpg"))
        return len(frames)

    def _get_sampling_strategy(self, duration: int) -> dict:
        """获取采样策略"""
        if self.max_frames:
            fps = self.max_frames / max(duration, 1)
            return {"fps": min(fps, 1.0), "max_frames": self.max_frames, "scene_threshold": 0.30}

        for name, config in self.SAMPLING_STRATEGY.items():
            if duration <= config["max_duration"]:
                return config

        return self.SAMPLING_STRATEGY["long"]

    def deduplicate_frames(self) -> int:
        """去重相似帧"""
        if not self.has_ffmpeg:
            return len(list(self.images_dir.glob("frame_*.jpg")))

        print(f"[4/5] 去重相似帧...")
        return FrameDeduplicator.deduplicate_frames(
            self.images_dir, self.similarity_threshold
        )

    def analyze_frames(self, sample_count: int = 60) -> list:
        """单线程分析帧内容"""
        if not self._load_api_config():
            print("未找到 Vision API 配置")
            print("请设置 ANTHROPIC_API_KEY 或 ~/.summarize/config.json")
            return []

        frames = sorted(self.images_dir.glob("frame_*.jpg"))
        if not frames:
            print("没有帧图片")
            return []

        # 采样分析（最多分析 sample_count 帧）
        total = len(frames)
        step = max(1, total // sample_count)
        analyze_frames = [frames[i] for i in range(0, total, step)][:sample_count]

        print(f"[5/5] 分析帧内容: 共{total}帧，分析{len(analyze_frames)}帧")

        api_config = self.API_CONFIG[self.api_type]
        results = []

        for i, frame_path in enumerate(analyze_frames):
            frame_name = frame_path.stem
            frame_num = int(frame_name.split("_")[1])
            timestamp = self._estimate_timestamp(frame_num)

            print(f"  [{i+1}/{len(analyze_frames)}] {frame_name} ({timestamp//60}:{timestamp%60:02d})...")

            try:
                result = self._analyze_single_frame(frame_path, timestamp)
                if result:
                    result["frame"] = frame_name
                    result["frame_num"] = frame_num
                    result["timestamp"] = timestamp
                    results.append(result)
            except Exception as e:
                print(f"    分析失败: {str(e)[:50]}")

            time.sleep(0.3)  # 避免 API 限速

        self.frame_analysis = results
        return results

    def _estimate_timestamp(self, frame_num: int) -> int:
        """估算帧对应的时间戳"""
        duration = self.video_info.get("duration", 0)
        total_frames = len(list(self.images_dir.glob("frame_*.jpg")))
        if total_frames > 0:
            return int(duration * frame_num / total_frames)
        return frame_num * 5  # 默认每帧5秒

    def _analyze_single_frame(self, frame_path: Path, timestamp: int) -> Optional[dict]:
        """分析单帧"""
        with open(frame_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode()

        api_config = self.API_CONFIG[self.api_type]

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        prompt = f"""分析这张视频截图（时间: {timestamp//60}分{timestamp%60}秒），返回JSON格式：
{{
    "scene_type": "代码编辑器/终端/浏览器/PPT/演示/其他",
    "title": "当前演示的标题或主题（简短）",
    "key_text": "屏幕上的关键文字内容（代码、命令、配置等）",
    "action": "正在演示的操作",
    "code_snippets": ["如果有代码，完整转录"],
    "config_items": {"如果有配置项，记录键值"},
    "notes": "重要说明或注意事项"
}}
只返回JSON，不要其他内容。"""

        payload = {
            "model": api_config["model"],
            "max_tokens": 800,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }},
                    {"type": "text", "text": prompt}
                ]
            }]
        }

        resp = requests.post(api_config["url"], headers=headers, json=payload, timeout=90)
        result = resp.json()

        if "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    text = item["text"]
                    try:
                        json_match = re.search(r'\{[\s\S]*\}', text)
                        if json_match:
                            return json.loads(json_match.group())
                    except:
                        return {"raw_text": text, "scene_type": "其他"}

        return None

    def generate_notes(self) -> Path:
        """生成Markdown笔记"""
        title = self.video_info.get("title", self.bvid)
        author = self.video_info.get("author", "未知")
        duration = self.video_info.get("duration", 0)
        view_count = self.video_info.get("view_count", 0)
        url = self.video_info.get("url", "")
        description = self.video_info.get("description", "")

        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        note_path = self.output_dir / f"{safe_title}_笔记.md"

        print(f"\n生成笔记: {note_path}")

        content = self._build_note_content(
            title, author, duration, view_count, url, description
        )

        note_path.write_text(content, encoding="utf-8")
        return note_path

    def _build_note_content(self, title, author, duration, view_count, url, description) -> str:
        """构建笔记内容"""
        lines = []

        # 标题和元信息
        lines.append(f"# {title}\n\n")
        lines.append(f"> 视频来源: [{url}]({url})\n")
        lines.append(f"> 作者: {author}\n")
        lines.append(f"> 时长: {duration//60}:{duration%60:02d}\n")
        if view_count:
            lines.append(f"> 播放量: {view_count}\n")
        lines.append("\n")

        # 概述
        lines.append("## 概述\n\n")
        if self.frame_analysis:
            first = self.frame_analysis[0]
            lines.append(f"![{first['frame']}: 视频开始](./images/{first['frame']}.jpg)\n\n")

        if description:
            lines.append(f"**视频简介**：{description[:300]}\n\n")

        # 内容详解
        lines.append("---\n\n## 内容详解\n\n")

        for i, frame in enumerate(self.frame_analysis[1:], 1):
            ts = frame.get("timestamp", 0)
            frame_name = frame.get("frame", "")

            lines.append(f"### {ts//60}分{ts%60}秒\n\n")
            lines.append(f"![{frame_name}: {frame.get('title', '截图')}](./images/{frame_name}.jpg)\n\n")

            if frame.get("scene_type"):
                lines.append(f"**场景**：{frame['scene_type']}\n\n")

            if frame.get("key_text"):
                lines.append(f"**内容**：{frame['key_text'][:200]}\n\n")

            if frame.get("action"):
                lines.append(f"**操作**：{frame['action']}\n\n")

            if frame.get("code_snippets"):
                lines.append("```")
                for snippet in frame['code_snippets'][:2]:
                    lines.append(snippet)
                lines.append("```\n")
                lines.append(f"<!-- 代码来自 {frame_name} -->\n\n")

            if frame.get("notes"):
                lines.append(f"**注意**：{frame['notes']}\n\n")

        # 总结
        lines.append("---\n\n## 总结\n\n")
        for frame in self.frame_analysis:
            if frame.get("notes"):
                lines.append(f"- {frame['notes'][:100]}\n")

        # 截图索引
        lines.append("\n---\n\n## 截图索引\n\n")
        lines.append("| 帧号 | 时间 | 内容 |\n")
        lines.append("|------|------|------|\n")
        for frame in self.frame_analysis:
            ts = frame.get("timestamp", 0)
            lines.append(f"| {frame['frame']} | {ts//60}:{ts%60:02d} | {frame.get('title', '截图')} |\n")

        return "".join(lines)

    def run(self) -> Optional[Path]:
        """完整运行流程"""
        print(f"\n{'='*60}")
        print(f"Bilibili Video Notes Generator v3.0")

        if self.is_local_mode:
            print(f"模式: 本地视频分析")
            print(f"视频: {self.local_video_path.name}")
        else:
            print(f"模式: B站在线视频")
            print(f"BV号: {self.bvid}")

        print(f"{'='*60}")

        self.print_environment_status()

        # Step 1: 获取视频信息
        self.get_video_info()
        print(f"  标题: {self.video_info.get('title', '未知')}")
        print(f"  时长: {self.video_info.get('duration', 0)}秒")

        if self.is_local_mode:
            file_size = self.video_info.get('file_size', 0)
            print(f"  文件大小: {file_size:.1f} MB")

        # Step 2: 下载/准备视频
        if not self.download_video():
            print("\n视频准备失败，流程终止")
            return None

        # Step 3: 智能采样拆帧
        frame_count = self.extract_frames_smart()
        if frame_count == 0:
            print("\n拆帧失败，流程终止")
            return None

        # Step 4: 去重相似帧
        self.deduplicate_frames()

        # Step 5: 分析帧内容
        self.analyze_frames()

        if not self.frame_analysis:
            print("\n帧分析失败，生成基础笔记")
            self.frame_analysis = [{
                "frame": "frame_0001",
                "timestamp": 0,
                "title": "视频内容",
                "scene_type": "其他"
            }]

        # Step 6: 生成笔记
        note_path = self.generate_notes()

        print(f"\n{'='*60}")
        print(f"完成!")
        print(f"  输出目录: {self.output_dir}")
        print(f"  笔记文件: {note_path}")
        print(f"  帧图片: {len(list(self.images_dir.glob('*.jpg')))} 张")
        print(f"{'='*60}")

        return note_path


def main():
    parser = argparse.ArgumentParser(
        description="B站视频笔记生成器 v3.0（优先使用 bili-cli）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 首选：使用 bili-cli 快速获取 AI 摘要（推荐）
  bili video BV1xx411c7mD --ai

  # 或使用本脚本的快速模式
  python analyze.py BV1xx411c7mD --quick

  # 详细图文笔记（帧分析）
  python analyze.py BV1xx411c7mD --frames -o ./output

  # 本地视频分析
  python analyze.py --video ./my_video.mp4 -o ./output
"""
    )

    # 输入源参数（互斥）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("bvid", nargs="?", help="B站视频BV号或URL")
    input_group.add_argument("--video", "-v", help="本地视频文件路径（跳过下载）")

    # 输出参数
    parser.add_argument("-o", "--output", default="./output", help="输出目录")

    # 本地视频专用参数
    parser.add_argument("--title", "-t", help="视频标题（用于本地视频）")

    # 模式选择
    parser.add_argument("--quick", "-q", action="store_true",
                        help="快速模式：优先使用 bili-cli 获取 AI 摘要（秒级完成）")
    parser.add_argument("--frames", action="store_true",
                        help="帧分析模式：提取关键帧生成图文笔记")

    # 分析参数
    parser.add_argument("-f", "--max-frames", type=int, default=60, help="最大帧数")
    parser.add_argument("--scene-threshold", type=float, default=0.3, help="场景变化阈值(0.1-0.5)")
    parser.add_argument("--similarity", type=float, default=0.80, help="相似帧去重阈值")

    # 控制参数
    parser.add_argument("--no-download", action="store_true", help="跳过下载")
    parser.add_argument("--no-dedup", action="store_true", help="跳过去重")

    args = parser.parse_args()

    # 快速模式：使用 bili-cli
    if args.quick and args.bvid and not args.video:
        print(f"\n{'='*60}")
        print("Bilibili Video Notes Generator v3.0 - 快速模式")
        print(f"{'='*60}\n")

        if BiliCliFetcher.check_bili_cli():
            print("[1/2] 使用 bili-cli 获取 AI 摘要...")
            data = BiliCliFetcher.get_video_info(args.bvid)

            if data and data.get("ai_summary"):
                print(f"  标题: {data.get('title', '未知')}")
                print(f"  作者: {data.get('author', '未知')}")
                print(f"  时长: {data.get('duration', 0)}秒")
                print(f"\n[2/2] AI 摘要:\n{data['ai_summary']}\n")

                # 生成简单笔记
                output_dir = Path(args.output) / args.bvid
                output_dir.mkdir(parents=True, exist_ok=True)
                note_path = output_dir / "视频笔记.md"

                lines = [
                    f"# {data.get('title', '视频笔记')}\n\n",
                    f"> 视频来源: {data.get('url', '')}\n",
                    f"> 作者: {data.get('author', '未知')}\n",
                    f"> 时长: {data.get('duration', 0)//60}分{data.get('duration', 0)%60:02d}秒\n\n",
                    "## AI 摘要\n\n",
                    f"{data['ai_summary']}\n\n",
                ]

                # 尝试获取字幕
                subtitle = BiliCliFetcher.get_subtitle(args.bvid)
                if subtitle:
                    lines.append("## 字幕内容\n\n")
                    lines.append(subtitle[:2000] + "\n\n")

                note_path.write_text("".join(lines), encoding="utf-8")
                print(f"笔记已保存: {note_path}")
                print(f"{'='*60}")
                return
            else:
                print("bili-cli 获取失败，退到帧分析模式...")
        else:
            print("bili-cli 未安装，退到帧分析模式...")
            print("安装方式: pipx install bilibili-cli")

    # 帧分析模式或快速模式失败
    analyzer = BilibiliAnalyzer(
        bvid=args.bvid,
        output_dir=args.output,
        local_video=args.video,
        video_title=args.title,
        max_frames=args.max_frames if args.frames else None,
        scene_threshold=args.scene_threshold,
        similarity_threshold=args.similarity if not args.no_dedup else 1.0
    )

    # 运行帧分析
    if args.no_download and not analyzer.is_local_mode:
        analyzer.output_dir.mkdir(parents=True, exist_ok=True)
        analyzer.get_video_info()
        analyzer.analyze_frames()
        analyzer.generate_notes()
    else:
        analyzer.run()


if __name__ == "__main__":
    main()