#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

CHANNEL_FILE = "channels.txt"
OUTPUT_FILE = "live.m3u"

EPG_URL_XML = "http://192.168.6.15:5678/t.xml.gz"
EPG_JSON_URL = "https://raw.githubusercontent.com/badboys88888/hk/main/epg_data.json"


# ===================== 读取远程EPG ===================== #
def load_epg():
    try:
        r = requests.get(EPG_JSON_URL, timeout=10)
        data = r.json()
    except:
        print("❌ EPG加载失败")
        return {}

    epg_map = {}

    for item in data.get("epgs", []):
        epgid = item.get("epgid", "").strip()
        logo = item.get("logo", "").strip()
        names = item.get("name", "")

        alias_list = [n.strip() for n in names.split(",") if n.strip()]

        for name in alias_list:
            epg_map[normalize(name)] = {
                "id": epgid,
                "logo": logo
            }

    return epg_map


# ===================== 名字清洗 ===================== #
def normalize(name):
    name = name.upper()
    name = name.replace("HD", "")
    name = name.replace("高清", "")
    name = name.replace("[", "").replace("]", "")
    name = name.replace("频道", "")
    name = name.strip()
    return name


# ===================== 匹配 ===================== #
def match_epg(channel_name, epg_map):
    key = normalize(channel_name)

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


# ===================== 展开m3u ===================== #
def expand_m3u(url):
    try:
        r = requests.get(url, timeout=10)
        r.encoding = "utf-8"
        lines = r.text.splitlines()
    except:
        return []

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

    return result


# ===================== 主逻辑 ===================== #
def generate():
    epg_map = load_epg()

    with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f'#EXTM3U x-tvg-url="{EPG_URL_XML}"\n')

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

                for sub_name, sub_url in subs:
                    sub_name = sub_name.strip()

                    epg = match_epg(sub_name, epg_map)

                    out.write(
                        f'#EXTINF:-1 tvg-id="{epg["id"]}" tvg-name="{sub_name}" tvg-logo="{epg["logo"]}" group-title="{group}",{sub_name}\n'
                    )
                    out.write(f"{sub_url}\n")

                continue

            # ===== 普通频道 =====
            epg = match_epg(name, epg_map)

            out.write(
                f'#EXTINF:-1 tvg-id="{epg["id"]}" tvg-name="{name}" tvg-logo="{epg["logo"]}" group-title="{group}",{name}\n'
            )
            out.write(f"{url}\n")

    print("✅ live.m3u 生成完成")


if __name__ == "__main__":
    generate()
