"""B站视频下载与拆帧脚本"""
import os
import subprocess
import sys
from pathlib import Path

# 视频信息
BV_ID = "BV14rzQB9EJj"
OUTPUT_DIR = Path("D:/ai-project/my-skills/output/BV14rzQB9EJj_analysis")

# 创建输出目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "images").mkdir(parents=True, exist_ok=True)

VIDEO_URL = f"https://www.bilibili.com/video/{BV_ID}"

def download_video():
    """使用 yt-dlp 下载视频"""
    video_path = OUTPUT_DIR / "video.mp4"
    video_only_path = OUTPUT_DIR / "video.f30064.mp4"

    if video_only_path.exists():
        print(f"视频已存在: {video_only_path}")
        return video_only_path

    print(f"正在下载视频: {VIDEO_URL}")

    # yt-dlp 下载命令 - 选择720p视频+最佳音频并合并
    cmd = [
        "yt-dlp",
        "-f", "30064+30280",  # 720p视频 + 最佳音频
        "-o", str(video_path),
        "--no-playlist",
        "--merge-output-format", "mp4",
        VIDEO_URL
    ]

    try:
        subprocess.run(cmd, check=True)
        # 检查实际下载的文件名（可能因缺少ffmpeg而未合并）
        if video_path.exists():
            print(f"视频下载完成: {video_path}")
            return video_path
        elif video_only_path.exists():
            print(f"视频下载完成（仅视频轨道）: {video_only_path}")
            return video_only_path
        else:
            # 查找下载的文件
            for f in OUTPUT_DIR.glob("video*.mp4"):
                print(f"视频下载完成: {f}")
                return f
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {e}")
        # 检查是否有部分下载的文件
        if video_only_path.exists():
            return video_only_path
        return None

def extract_frames(video_path, fps=0.2):
    """使用 imageio 提取帧"""
    import imageio
    import numpy as np
    from PIL import Image

    images_dir = OUTPUT_DIR / "images"

    print(f"正在读取视频: {video_path}")
    print(f"帧率设置: {fps} fps (每 {1/fps:.0f} 秒提取1帧)")

    reader = imageio.get_reader(str(video_path), fps=fps)

    # 获取视频信息
    meta = reader.get_meta_data()
    duration = meta.get('duration', 0)
    total_frames_estimate = int(duration * fps) if duration else 500

    print(f"视频时长: {duration:.1f} 秒")
    print(f"预计提取帧数: ~{total_frames_estimate}")

    frame_count = 0
    saved_count = 0
    interval = int(30 / fps)  # 每30秒的帧数，用于去重

    prev_frame = None
    similarity_threshold = 0.85

    for frame in reader:
        frame_count += 1

        # 转换为 PIL Image
        img = Image.fromarray(frame)

        # 相似帧去重
        if prev_frame is not None:
            # 简单的相似度检测：比较像素差异
            prev_array = np.array(prev_frame.resize(img.size))
            curr_array = np.array(img)
            diff = np.abs(prev_array - curr_array).mean() / 255
            if diff < (1 - similarity_threshold):
                continue  # 跳过相似帧

        # 保存帧
        frame_name = f"frame_{saved_count + 1:04d}.jpg"
        img.save(images_dir / frame_name, quality=85)
        saved_count += 1
        prev_frame = img

        if saved_count % 50 == 0:
            print(f"已保存 {saved_count} 帧...")

    reader.close()
    print(f"\n提取完成: 共保存 {saved_count} 帧到 {images_dir}")
    return saved_count

def main():
    print("=" * 50)
    print(f"BV号: {BV_ID}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 50)

    # Step 1: 下载视频
    video_path = download_video()
    if not video_path:
        print("视频下载失败，退出")
        return

    # Step 2: 提取帧
    extract_frames(video_path, fps=0.2)  # 每5秒1帧

    print("\n✅ 处理完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"帧图片: {OUTPUT_DIR / 'images'}")

if __name__ == "__main__":
    main()