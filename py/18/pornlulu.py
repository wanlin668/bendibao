# -*- coding: utf-8 -*-
"""
目标站: pornlulu.net (镜像: pornlulu-25052.xxnet04.com)
模板: 自建站 (hex 编码 + window.videoConfig 直链)
功能: 分类浏览、详情解析、m3u8 播放、搜索
"""
import sys
import re
import json
import urllib.parse
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

sys.path.append("..")
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

    def getName(self):
        return "国产聚合"

    def init(self, extend=""):
        # 镜像站无 WAF，hex 编码内容
        self.host = "https://pornlulu-25052.xxnet04.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Referer": self.host + "/",
        }
        self.categories = [
            {"type_id": "48", "type_name": "中文字幕"},
            {"type_id": "270", "type_name": "日本无码"},
            {"type_id": "269", "type_name": "日本有码"},
            {"type_id": "259", "type_name": "日韩无码"},
            {"type_id": "254", "type_name": "无码专区"},
            {"type_id": "92", "type_name": "制服诱惑"},
            {"type_id": "401", "type_name": "AV明星"},
            {"type_id": "86", "type_name": "动漫精品"},
            {"type_id": "93", "type_name": "巨乳美乳"},
            {"type_id": "438", "type_name": "女优明星"},
            {"type_id": "274", "type_name": "成人动漫"},
            {"type_id": "22", "type_name": "亚洲情色"},
            {"type_id": "105", "type_name": "亚洲有码"},
            {"type_id": "367", "type_name": "伦理三级"},
            {"type_id": "260", "type_name": "欧美精品"},
            {"type_id": "130", "type_name": "卡通动漫"},
            {"type_id": "392", "type_name": "AV解说"},
            {"type_id": "452", "type_name": "SWAG"},
            {"type_id": "453", "type_name": "激情动漫"},
            {"type_id": "52", "type_name": "欧美性爱"},
            {"type_id": "115", "type_name": "女同性恋"},
            {"type_id": "125", "type_name": "童颜巨乳"},
            {"type_id": "275", "type_name": "日韩精品"},
            {"type_id": "111", "type_name": "美乳巨乳"},
            {"type_id": "265", "type_name": "欧美情色"},
            {"type_id": "266", "type_name": "欧美极品"},
            {"type_id": "425", "type_name": "性感人妻"},
            {"type_id": "23", "type_name": "人妻熟女"},
            {"type_id": "658", "type_name": "欧美无码"},
            {"type_id": "454", "type_name": "黑丝诱惑"},
            {"type_id": "84", "type_name": "三级伦理"},
            {"type_id": "273", "type_name": "邻家人妻"},
            {"type_id": "109", "type_name": "绝美少女"},
            {"type_id": "101", "type_name": "人妻系列"},
            {"type_id": "99", "type_name": "巨乳系列"},
            {"type_id": "416", "type_name": "麻豆传媒"},
            {"type_id": "267", "type_name": "熟女人妻"},
            {"type_id": "129", "type_name": "多人群交"},
            {"type_id": "403", "type_name": "日本片商"},
            {"type_id": "5", "type_name": "空姐模特"},
            {"type_id": "134", "type_name": "激情口交"},
            {"type_id": "424", "type_name": "丝袜OL"},
            {"type_id": "149", "type_name": "动漫卡通"},
            {"type_id": "110", "type_name": "口交视频"},
            {"type_id": "106", "type_name": "SM重味"},
            {"type_id": "451", "type_name": "VR视角"},
            {"type_id": "131", "type_name": "欧美系列"},
            {"type_id": "357", "type_name": "AI换脸"},
            {"type_id": "64", "type_name": "亚洲无码"},
            {"type_id": "132", "type_name": "女同性爱"},
            {"type_id": "467", "type_name": "日本精品"},
            {"type_id": "96", "type_name": "高潮喷吹"},
            {"type_id": "657", "type_name": "日本中文字幕"},
            {"type_id": "653", "type_name": "韩国主播"},
            {"type_id": "432", "type_name": "日本女优"},
            {"type_id": "643", "type_name": "禁漫"},
            {"type_id": "644", "type_name": "伦理片"},
            {"type_id": "666", "type_name": "日本高清有码"},
            {"type_id": "120", "type_name": "伦理影片"},
            {"type_id": "516", "type_name": "换脸明星"},
            {"type_id": "44", "type_name": "韩国伦理"},
            {"type_id": "246", "type_name": "欧美无码"},
            {"type_id": "717", "type_name": "日本素人"},
            {"type_id": "124", "type_name": "HEYZO"},
        ]
        self.filters = {}

    # ----------------------------------------------------------------------
    # helpers
    # ----------------------------------------------------------------------

    def _get(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = "utf-8"
            html = self._decode_hex(r.text)
            return html
        except Exception as e:
            print(f"[pornlulu] fetch error: {e}", file=sys.stderr)
            return ""

    @staticmethod
    def _decode_hex(raw_text):
        """Decode hex-encoded mirror content.
        Mirror serves: document.write(fn(unescape(fn("<hex>"))))
        Find longest hex string, fromhex, then url-unquote.
        """
        hex_candidates = re.findall(r"([0-9a-fA-F]{100,})", raw_text)
        if not hex_candidates:
            return raw_text
        hex_str = max(hex_candidates, key=len)
        try:
            decoded = bytes.fromhex(hex_str).decode("utf-8", errors="replace")
            decoded = urllib.parse.unquote(decoded)
            return decoded
        except Exception:
            return raw_text

    def _parse_cards(self, html):
        """Parse video cards from listing page."""
        videos = []
        pattern = re.compile(
            r'href="/v/([A-Za-z0-9]+)"[^>]*>\s*'
            r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"',
            re.DOTALL,
        )
        seen = set()
        for m in pattern.finditer(html):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            img = m.group(2)
            title = m.group(3).strip()
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": "",
            })
        return videos

    # ----------------------------------------------------------------------
    # TVBox API
    # ----------------------------------------------------------------------

    def homeContent(self, filter):
        html = self._get(self.host + "/?sort=id")
        return {"class": self.categories, "list": self._parse_cards(html), "filters": self.filters}

    def homeVideoContent(self):
        html = self._get(self.host + "/?sort=id")
        return {"list": self._parse_cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = f"{self.host}/cat/{tid}?page={page}"
        html = self._get(url)
        videos = self._parse_cards(html)

        # pagination
        page_nums = set()
        for m in re.finditer(r'href="[^"]*page=(\d+)"', html):
            page_nums.add(int(m.group(1)))
        pagecount = 1
        if page_nums:
            max_visible = max(page_nums)
            last_m = re.search(r'共\s*(\d+)\s*页', html)
            if last_m:
                pagecount = int(last_m.group(1))
            else:
                next_disabled = re.search(r'class="page-item next disabled"', html)
                if next_disabled and max_visible <= 5:
                    pagecount = max_visible
                else:
                    pagecount = max(max_visible, 999)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": len(videos),
            "total": pagecount * len(videos),
        }

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.host}/v/{vid}"
        html = self._get(url)

        # Extract m3u8 URL from window.videoConfig
        m3u8_url = ""
        m = re.search(r'window\.videoConfig\s*=\s*\{[^}]*url:\s*"([^"]+)"', html)
        if m:
            m3u8_url = m.group(1)

        # Extract thumbnail
        pic = ""
        m_pic = re.search(r'window\.videoConfig\s*=\s*\{[^}]*img:\s*"([^"]+)"', html)
        if m_pic:
            pic = m_pic.group(1)

        # Extract title
        title = vid
        m_title = re.search(r'<h1[^>]*class="title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m_title:
            raw = m_title.group(1)
            title = re.sub(r"<[^>]+>", "", raw)
            title = re.sub(r"\{\{.*?\}\}", "", title, flags=re.DOTALL).strip()
            title = re.sub(r"\s+", " ", title).strip()
        if not title:
            title = vid

        # Extract actor
        actor = ""
        m_actor = re.search(r'href="/actors/([^"]+)"', html)
        if m_actor:
            actor = urllib.parse.unquote(m_actor.group(1))

        # Build content
        desc_parts = []
        if actor:
            desc_parts.append(f"演员: {actor}")
        desc_parts.append(f"视频ID: {vid}")
        content = " | ".join(desc_parts)

        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": content,
            "vod_play_from": "pornlulu",
            "vod_play_url": f"播放${m3u8_url}#",
        }]}

    def searchContent(self, key, quick, pg="1"):
        pg_int = int(pg) if pg else 1
        url = f"{self.host}/q/{quote(key)}?page={pg_int}"
        html = self._get(url)
        videos = self._parse_cards(html)

        page_nums = set()
        for m in re.finditer(r'href="[^"]*page=(\d+)"', html):
            page_nums.add(int(m.group(1)))
        pagecount = max(page_nums) if page_nums else 1
        return {
            "list": videos,
            "page": pg_int,
            "pagecount": pagecount,
            "limit": len(videos),
            "total": pagecount * len(videos),
        }

    def playerContent(self, flag, id, vipFlags):
        """id is the direct m3u8 URL."""
        return {
            "parse": 0,
            "url": id,
            "header": "",
        }

    def localProxy(self, param):
        return {"code": 404, "content": ""}

    def isVideoFormat(self, url):
        return ".m3u8" in url.lower() or ".mp4" in url.lower()

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass
