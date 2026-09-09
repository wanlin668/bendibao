# -*- coding: utf-8 -*-
"""
站点: rlmj.buzz (https://w5s.rlmj.live/)
模式: 列表爬虫 + WebView播放（解决播放卡顿/防盗链）
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def fetch(self, url, headers=None, timeout=10):
            try:
                r = requests.get(url, headers=headers, timeout=timeout)
                r.encoding = 'utf-8'
                return r
            except Exception:
                return None

class Spider(BaseSpider):
    def getName(self):
        return "RLMJ影视"

    def init(self, extend=""):
        self.host = "https://w5s.rlmj.live"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._class_cache = None
        self.timeout = 10

    def _fetch(self, url):
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                return r.text
        except Exception as e:
            print(f"[fetch] {e}")
        return ''

    def _fix_pic(self, pic):
        if not pic:
            return ''
        if not pic.startswith('http'):
            pic = urljoin(self.host, pic)
        return pic + "@Referer=" + self.host + "/"

    # ---------- 分类（硬编码，保证显示） ----------
    def _get_classes(self):
        if self._class_cache:
            return self._class_cache
        self._class_cache = [
            {"type_id": "29", "type_name": "真实偷拍"},
            {"type_id": "31", "type_name": "强奸迷奸"},
            {"type_id": "23", "type_name": "国产热播"},
            {"type_id": "24", "type_name": "反差母狗"},
            {"type_id": "25", "type_name": "美脚丝足"},
            {"type_id": "26", "type_name": "情侣自拍"},
            {"type_id": "27", "type_name": "私房俱乐部"},
            {"type_id": "28", "type_name": "偷情约炮"},
            {"type_id": "30", "type_name": "高潮喷水"},
            {"type_id": "32", "type_name": "户外露出"},
            {"type_id": "33", "type_name": "SM调教"},
            {"type_id": "35", "type_name": "精选探花"},
            {"type_id": "36", "type_name": "网曝门事件"},
            {"type_id": "67", "type_name": "国产AV"},
            {"type_id": "68", "type_name": "网红主播"},
            {"type_id": "83", "type_name": "3D动漫"},
            {"type_id": "92", "type_name": "无码流出"},
            {"type_id": "93", "type_name": "FC2"},
        ]
        return self._class_cache

    # ---------- 列表解析 ----------
    def _parse_videos(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        for a in soup.find_all('a', href=re.compile(r'/index\.php/vod/play/id/\d+')):
            href = a.get('href')
            m = re.search(r'/id/(\d+)', href)
            if not m:
                continue
            vid = m.group(1)
            title = a.get('title') or a.get_text(strip=True)
            if not title:
                img = a.find('img')
                if img:
                    title = img.get('alt', '')
            if not title:
                title = vid
            pic = ''
            img = a.find('img')
            if img:
                pic = img.get('src') or img.get('data-src') or ''
                if pic:
                    pic = self._fix_pic(pic)
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': ''
            })
        return videos

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        html = self._fetch(self.host + "/")
        videos = self._parse_videos(html) if html else []
        if not videos and classes:
            html = self._fetch(f"{self.host}/index.php/vod/type/id/{classes[0]['type_id']}.html")
            videos = self._parse_videos(html) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        videos = self._parse_videos(html) if html else []
        if not videos:
            classes = self._get_classes()
            if classes:
                html = self._fetch(f"{self.host}/index.php/vod/type/id/{classes[0]['type_id']}.html")
                videos = self._parse_videos(html) if html else []
        return {'list': videos[:20] if videos else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        url = f"{self.host}/index.php/vod/type/id/{tid}.html"
        if page > 1:
            url = f"{self.host}/index.php/vod/type/id/{tid}/page/{page}.html"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page, 'pagecount': 1}
        videos = self._parse_videos(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if len(videos) >= 20 else page,
            'limit': len(videos) or 20,
            'total': (page + 1) * 20
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        # 直接构造播放页 URL
        play_url = f"{self.host}/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
        return {'list': [{
            'vod_id': vid,
            'vod_name': f"视频{vid}",
            'vod_pic': '',
            'vod_content': '',
            'vod_play_from': '默认线路',
            'vod_play_url': f'正片${play_url}'
        }]}

    # ==================== 核心：WebView 播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        # 如果传入的是直链（m3u8/mp4），直接返回
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {
                'parse': 0,
                'url': id,
                'header': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': self.host + '/',
                    'Origin': self.host,
                }
            }
        # 否则返回 WebView 模式，让 TVBox 自己加载播放页去嗅探
        return {
            'parse': 1,          # 关键：TVBox WebView 加载
            'url': id,
            'header': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.host + '/'
            }
        }

    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        url = f"{self.host}/index.php/vod/search.html?wd={quote(key)}"
        if page > 1:
            url += f"&page={page}"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page, 'pagecount': 1}
        videos = self._parse_videos(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if len(videos) >= 20 else page,
            'limit': len(videos) or 20,
            'total': (page + 1) * 20
        }

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.session.close()

    def localProxy(self, param):
        return None