#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

CHANNEL_FILE = "channels.txt"
OUTPUT_FILE = "live.m3u"

EPG_XML = "http://192.168.6.15:5678/t.xml.gz"
EPG_JSON = "https://raw.githubusercontent.com/badboys88888/hk/main/epg_data.json"


# ===================== 名字清洗 ===================== #
def normalize(name):
    name = name.upper()
    for x in ["HD", "高清", "频道", "[", "]", " "]:
        name = name.replace(x, "")
    return name.strip()


# ===================== 读取EPG ===================== #
def load_epg():
    print("📥 加载EPG...")
    try:
        r = requests.get(EPG_JSON, timeout=10)
        data = r.json()
    except Exception as e:
        print("❌ EPG加载失败:", e)
        return {}

    epg_map = {}

    for item in data.get("epgs", []):
        epgid = item.get("epgid", "")
        logo = item.get("logo", "")
        names = item.get("name", "")

        for n in names.split(","):
            n = n.strip()
            if n:
                epg_map[normalize(n)] = {
                    "id": epgid,
                    "logo": logo
                }

    print("✅ EPG数量:", len(epg_map))
    return epg_map


# ===================== 匹配 ===================== #
def match_epg(name, epg_map):
    key = normalize(name)

    # 精确
    if key in epg_map:
        return epg_map[key]

    # 模糊
    for k in epg_map:
        if k in key or key in k:
            return epg_map[k]

    return {"id": "", "logo": ""}


# ===================== 判断m3u ===================== #
def is_m3u(url):
    return ".m3u" in url.lower()


# ===================== 展开m3u（带调试） ===================== #
def expand_m3u(url):
    print("\n📡 展开:", url)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://google.com"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print("状态码:", r.status_code)
        print("类型:", r.headers.get("Content-Type"))

        r.encoding = "utf-8"
        text = r.text

        print("前100字符:", text[:100])

    except Exception as e:
        print("❌ 请求失败:", e)
        return []

    lines = text.splitlines()

    result = []
    name = ""

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            name = line.split(",")[-1].strip()

        elif line.startswith("http"):
            result.append((name, line))

    print("✅ 解析数量:", len(result))
    return result


# ===================== 主逻辑 ===================== #
def generate():
    epg_map = load_epg()

    with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f'#EXTM3U x-tvg-url="{EPG_XML}"\n')

        group = ""

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # 分组
            if line.startswith("#genre#"):
                group = line.replace("#genre#", "").strip()
                continue

            if "," not in line:
                continue

            name, url = line.split(",", 1)
            name = name.strip()
            url = url.strip()

            # ===== m3u展开 =====
            if is_m3u(url):
                subs = expand_m3u(url)

                if not subs:
                    print("⚠️ 没解析到，跳过")
                    continue

                for sub_name, sub_url in subs:
                    epg = match_epg(sub_name, epg_map)

                    out.write(
                        f'#EXTINF:-1 tvg-id="{epg["id"]}" tvg-name="{sub_name}" tvg-logo="{epg["logo"]}" group-title="{group}",{sub_name}\n'
                    )
                    out.write(f"{sub_url}\n")

                    total += 1

                continue

            # ===== 普通频道 =====
            epg = match_epg(name, epg_map)

            out.write(
                f'#EXTINF:-1 tvg-id="{epg["id"]}" tvg-name="{name}" tvg-logo="{epg["logo"]}" group-title="{group}",{name}\n'
            )
            out.write(f"{url}\n")

            total += 1

    print("\n🎯 总频道数:", total)
    print("✅ live.m3u 生成完成")


# ===================== 启动 ===================== #
if __name__ == "__main__":
    generate()
