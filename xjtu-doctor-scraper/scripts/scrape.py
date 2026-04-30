"""西安交通大学第一附属医院 - 医生列表全流程爬虫
用法:
  # 步骤1: 解析主页面，生成医生列表（自动过滤科室分类页面）
  python scrape.py parse doctors_list.json

  # 步骤2: 多线程爬取医生详情（5线程，每批100条）
  python scrape.py batch doctors_list.json output.csv 0 100
  python scrape.py batch doctors_list.json output.csv 100 100
  ...

  # 步骤3: 多线程修复已有CSV的图片URL和研究方向字段
  python scrape.py fix doctors_list.json input.csv output.csv
"""
import requests, re, json, time, csv, sys, os, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://www.dyyy.xjtu.edu.cn"
FIELDNAMES = ['科室大类', '科室小类', '科室名称', '医生名称', '医生职称',
              '医生科室', '研究方向与专长', '专家介绍', '医生图片URL']

# 需要过滤的非医生条目名称
SKIP_NAMES = {'相关资讯', '相关科普文章', '更多', '详情', 'more'}

# 多线程配置
MAX_WORKERS = 5

# 线程安全的 requests Session（每个线程用独立 Session 避免竞争）
_session_local = threading.local()

def _get_session():
    """每个线程获取独立的 requests.Session"""
    if not hasattr(_session_local, 'session'):
        sess = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": BASE})
        _session_local.session = sess
    return _session_local.session

# 主线程用的全局 Session（parse 等单线程操作）
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": BASE})

# ─── 工具函数 ───

def fetch_html(url, timeout=8, session=None):
    try:
        sess = session or s
        r = sess.get(url, timeout=timeout)
        r.encoding = 'utf-8'
        return r.text
    except:
        return ""

def get_api(account_id, session=None):
    """调用医生详情API，返回data或None"""
    if not account_id:
        return None
    try:
        sess = session or s
        r = sess.get(f"{BASE}/services/industry/patient/static/userDoctor/detailByAccount/{account_id}", timeout=8)
        d = r.json()
        if d.get('status') and d.get('code') == 10000:
            return d.get('data')
    except:
        pass
    return None

def extract_account_id(url, session=None):
    """从医生详情页HTML提取account_id"""
    html = fetch_html(f"{BASE}/{url}", session=session)
    match = re.search(r"detailByAccount/(\d+)", html)
    return match.group(1) if match else None

def build_doctor_row(api_data, fallback_name='', fallback_dep=''):
    """从API数据构建CSV行"""
    if not api_data:
        return {
            '科室大类': '', '科室小类': '', '科室名称': fallback_dep,
            '医生名称': fallback_name, '医生职称': '', '医生科室': fallback_dep,
            '研究方向与专长': '', '专家介绍': '', '医生图片URL': ''
        }

    # 研究方向与专长 → acaTitle（可读文本），不要用goodDirectionList（UUID代码）
    aca_title = (api_data.get('acaTitle') or '').strip()

    # 图片URL → photoShortUrl是UUID格式shortcode，不要用doctorAccount（数字ID）
    photo_shortcode = api_data.get('photoShortUrl', '')
    img_url = (f"{BASE}/services/industry/app-filesystem/file-show?appId=patient&shortcode={photo_shortcode}"
               if photo_shortcode else '')

    return {
        '科室大类': api_data.get('depTypeDicCodeName', ''),
        '科室小类': api_data.get('parentDepTypeDicCodeName', ''),
        '科室名称': api_data.get('departmentName', fallback_dep),
        '医生名称': api_data.get('name', fallback_name),
        '医生职称': api_data.get('docJobTitleDicCodeName', ''),
        '医生科室': f"{api_data.get('departmentName', '')} {api_data.get('hospitalName', '西安交通大学第一附属医院')}".strip(),
        '研究方向与专长': aca_title,
        '专家介绍': api_data.get('introduce', ''),
        '医生图片URL': img_url
    }

def save_csv(rows, path):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

# ─── 命令实现 ───

def cmd_parse(output_path):
    """解析主页面，提取医生列表（过滤科室分类页面）

    URL结构区分：
    - 科室分类页面：zjjs/nkxt/e_k.htm (3级路径：大类/小类.htm)
    - 医生详情页面：zjjs/nkxt/e_k/lxh.htm (4级路径：大类/小类/医生缩写.htm)

    只有4级路径才是真正的医生链接
    """
    r = s.get(f"{BASE}/zjjs.htm", timeout=15)
    r.encoding = 'utf-8'
    html = r.text

    pattern = r'href=["\']?(zjjs/[^"\'>\s]+\.htm)["\']?[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html)

    seen = set()
    doctors = []
    skipped_dept = 0  # 科室分类页面计数
    skipped_other = 0  # 其他非医生条目计数

    for link, name in matches:
        name = name.strip()

        # 过滤非医生条目：相关资讯、相关科普文章等
        if not name or name in SKIP_NAMES:
            if name in SKIP_NAMES and name not in ('更多', '详情', 'more'):
                skipped_other += 1
            continue

        # 关键过滤：URL路径深度
        # link 格式：zjjs/nkxt/e_k.htm (科室) 或 zjjs/nkxt/e_k/lxh.htm (医生)
        parts = link.split('/')
        # parts = ['zjjs', 'nkxt', 'e_k.htm'] -> 3个元素 = 科室页面
        # parts = ['zjjs', 'nkxt', 'e_k', 'lxh.htm'] -> 4个元素 = 医生页面
        if len(parts) < 4:
            # 这是科室分类页面，不是医生详情页
            skipped_dept += 1
            continue

        key = (name, link)
        if key in seen:
            continue
        seen.add(key)

        parent_dep = parts[1] if len(parts) > 1 else ''
        dep_name = parts[2] if len(parts) > 2 else ''
        doctors.append([name, link, parent_dep, dep_name])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(doctors, f, ensure_ascii=False, indent=2)

    print(f"✅ 找到 {len(doctors)} 个医生链接（已过滤 {skipped_dept} 个科室分类页面、{skipped_other} 条其他非医生条目），已保存到 {output_path}")


def _process_one_doctor(doc, idx, total, existing):
    """处理单个医生（线程工作函数），返回 (排序索引, 结果行或None, 日志信息)"""
    name, url, parent_dep, dep_name = doc
    if name in existing:
        return (idx, None, f"  跳过（已存在）: {name}")

    sess = _get_session()
    account_id = extract_account_id(url, session=sess)
    if not account_id:
        return (idx, None, f"  ⚠️ 未找到account_id: {name}")

    api_data = get_api(account_id, session=sess)
    row = build_doctor_row(api_data, name, dep_name)
    return (idx, row, f"  [{idx+1}/{total}] {name} (account: {account_id})")


def cmd_batch(list_path, csv_path, start, count, workers=MAX_WORKERS):
    """多线程分批爬取医生详情"""
    with open(list_path, 'r', encoding='utf-8') as f:
        doctors = json.load(f)

    # 断点续爬：读取已有记录
    existing = set()
    if os.path.exists(csv_path):
        for row in load_csv(csv_path):
            existing.add(row.get('医生名称', ''))

    batch = doctors[start:start + count]
    print(f"处理第 {start + 1} - {start + len(batch)} 条（共 {len(doctors)} 条），{workers} 线程并发")

    results = []
    lock = threading.Lock()
    completed = [0]  # 用列表以便在线程内修改

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for i, doc in enumerate(batch):
            future = executor.submit(_process_one_doctor, doc, i, len(batch), existing)
            futures[future] = i

        for future in as_completed(futures):
            idx, row, log_msg = future.result()
            print(log_msg)
            if row is not None:
                with lock:
                    results.append((idx, row))

    # 按原始顺序排序
    results.sort(key=lambda x: x[0])
    sorted_rows = [r for _, r in results]

    if sorted_rows:
        existing_rows = load_csv(csv_path) if os.path.exists(csv_path) else []
        save_csv(existing_rows + sorted_rows, csv_path)
        print(f"\n✅ 已保存 {len(sorted_rows)} 条新记录（总计 {len(existing_rows) + len(sorted_rows)} 条）")
    else:
        print(f"\n⚠️ 无新记录需要保存")


def _fix_one_row(row, idx, total, name_to_url):
    """修复单条记录（线程工作函数），返回 (排序索引, 修复计数, 日志信息)"""
    name = row.get('医生名称', '').strip()
    if not name:
        return (idx, 0, "")

    doc_url = name_to_url.get(name, '')
    if not doc_url:
        return (idx, 0, "")

    sess = _get_session()
    account_id = extract_account_id(doc_url, session=sess)
    if not account_id:
        return (idx, 0, "")

    api_data = get_api(account_id, session=sess)
    if not api_data:
        return (idx, 0, "")

    # 修复字段
    row['研究方向与专长'] = (api_data.get('acaTitle') or '').strip()
    photo = api_data.get('photoShortUrl', '')
    row['医生图片URL'] = (f"{BASE}/services/industry/app-filesystem/file-show?appId=patient&shortcode={photo}"
                           if photo else '')
    return (idx, 1, f"  [{idx+1}/{total}] 修复: {name}")


def cmd_fix(list_path, csv_in, csv_out=None, workers=MAX_WORKERS):
    """多线程修复已有CSV的图片URL和研究方向字段"""
    if csv_out is None:
        csv_out = csv_in.replace('.csv', '_fixed.csv')

    with open(list_path, 'r', encoding='utf-8') as f:
        doctors = json.load(f)
    name_to_url = {doc[0]: doc[1] for doc in doctors}

    rows = load_csv(csv_in)
    total = len(rows)
    print(f"共 {total} 条记录，{workers} 线程并发修复")

    fixed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for i, row in enumerate(rows):
            future = executor.submit(_fix_one_row, row, i, total, name_to_url)
            futures[future] = i

        done_count = 0
        for future in as_completed(futures):
            idx, fix_count, log_msg = future.result()
            if log_msg:
                print(log_msg)
            fixed += fix_count
            done_count += 1
            if done_count % 100 == 0:
                print(f"进度: {done_count}/{total} (已修复={fixed})")

    save_csv(rows, csv_out)
    print(f"\n✅ 已修复 {fixed} 条，保存到 {csv_out}")


# ─── 入口 ───

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'parse':
        output = sys.argv[2] if len(sys.argv) > 2 else "doctors_list.json"
        cmd_parse(output)

    elif cmd == 'batch':
        if len(sys.argv) < 5:
            print("用法: python scrape.py batch <doctors_list.json> <output.csv> <start> <count>")
            sys.exit(1)
        cmd_batch(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 100)

    elif cmd == 'fix':
        if len(sys.argv) < 4:
            print("用法: python scrape.py fix <doctors_list.json> <input.csv> [output.csv]")
            sys.exit(1)
        cmd_fix(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)

    else:
        print(f"未知命令: {cmd}")
        print("可用命令: parse, batch, fix")
        sys.exit(1)