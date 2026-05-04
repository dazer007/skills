"""爬取B站视频评论 - 保存头像、用户ID、评论内容"""
import requests
import csv
import time
import json
import os

# 视频信息
BV_ID = "BV1AcwczbEkN"
AID = 116210574299536  # 从视频信息获取

# Cookie
COOKIE = """buvid3=4F93C11D-3FE0-2E40-4A8F-933297F7C42912858infoc; b_nut=1764210212; _uuid=7289B6FA-D176-37BE-DDA7-E285FD55E7EC11037infoc; CURRENT_QUALITY=0; buvid4=0D96D3C9-4FFF-4D8B-96B0-97E4B7BA85D558495-024091704-d67+0GvyM7Atq8MPOSMwKA%3D%3D; buvid_fp=907c0214e90bda2709433c011ba8bfd9; rpdid=|(u|u~RJRlYl0J'u~YY)|JmYk; theme-tip-show=SHOWED; home_feed_column=5; theme-avatar-tip-show=SHOWED; theme-switch-show=SHOWED; SESSDATA=1d5c2191%2C1793164151%2C77435%2A52CjAf38dk99sOjCG5CSmpskxATDlON1SyyvreFzFFnlhf3vQ_jU3t0bLfGohgK3S8wg8SVmZqek5qVnRnbDlzaExjUDRKb0hkcTRxeVF4SU5BUU9NU01XRDY5RkVzb2p5RDI2bjBDSkU3QkhhTzRSc25fWlJQN2VOMnpkQ0laV0tJNXVLZ2tvWThRIIEC; bili_jct=f72bef14fdab3201afd9382fb1bf778a; DedeUserID=38819129; DedeUserID__ckMd5=41b56e4011367dec; sid=85ng1xko; CURRENT_FNVAL=4048; bp_t_offset_38819129=1197399760722460672; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Nzc4ODg5NjUsImlhdCI6MTc3NzYyOTcwNSwicGx0IjotMX0.IwqXPGW2SdZWtQw9PAsuSBPhlfog83mSp5yFLabreMI; bili_ticket_expires=1777888905"""

# 输出目录
OUTPUT_DIR = "D:/ai-project/my-skills/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.bilibili.com/video/{BV_ID}",
    "Cookie": COOKIE
}

def get_user_info(mid):
    """获取用户头像等信息"""
    try:
        url = f"https://api.bilibili.com/x/space/wbi/acc/info?mid={mid}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        if data.get('code') == 0:
            user_data = data.get('data', {})
            avatar = user_data.get('face', '')
            level = user_data.get('level', 'N/A')
            return avatar, level
    except:
        pass
    return '', 'N/A'

def get_all_comments(aid, max_pages=50):
    """获取所有一级评论"""
    comments = []
    page = 1

    while page <= max_pages:
        print(f"正在获取第 {page} 页评论...")

        url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&ps=20&pn={page}&sort_type=2"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()

            if data.get('code') != 0:
                print(f"API错误: {data.get('message')}")
                break

            replies = data.get('data', {}).get('replies', [])

            if not replies:
                print("没有更多评论了")
                break

            for r in replies:
                comment_id = r.get('rpid', '')
                author = r.get('member', {})
                mid = author.get('mid', '')
                name = author.get('uname', '')
                avatar = author.get('avatar', '')
                level = author.get('level_info', {}).get('current_level', 'N/A')
                message = r.get('content', {}).get('message', '')
                like = r.get('like', 0)

                comments.append({
                    'comment_id': comment_id,
                    'user_id': mid,
                    'user_name': name,
                    'user_avatar': avatar,
                    'user_level': level,
                    'comment': message,
                    'like_count': like
                })

            print(f"本页获取 {len(replies)} 条，累计 {len(comments)} 条")

            # 检查是否还有下一页
            page_info = data.get('data', {}).get('page', {})
            count = page_info.get('count', 0)
            if len(comments) >= count:
                break

            page += 1
            time.sleep(0.5)  # 防止请求过快

        except Exception as e:
            print(f"请求失败: {e}")
            break

    return comments

def save_to_csv(comments, filename):
    """保存为CSV"""
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['序号', '评论ID', '用户ID', '用户名称', 'B站等级', '用户头像URL', '评论内容', '点赞数'])
        writer.writeheader()

        for i, c in enumerate(comments, 1):
            writer.writerow({
                '序号': i,
                '评论ID': c['comment_id'],
                '用户ID': c['user_id'],
                '用户名称': c['user_name'],
                'B站等级': c['user_level'],
                '用户头像URL': c['user_avatar'],
                '评论内容': c['comment'],
                '点赞数': c['like_count']
            })

    print(f"\n✅ 已保存到: {filepath}")
    return filepath

def main():
    print(f"视频: {BV_ID}")
    print(f"AID: {AID}")
    print("=" * 50)

    # 获取评论
    comments = get_all_comments(AID, max_pages=100)

    if comments:
        # 保存CSV
        csv_file = save_to_csv(comments, f"{BV_ID}_评论数据.csv")
        print(f"共获取 {len(comments)} 条一级评论")
    else:
        print("未能获取到评论")

if __name__ == '__main__':
    main()