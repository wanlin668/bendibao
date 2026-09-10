# -*- coding: utf-8 -*-
"""
站点: Pektino (https://pektino.com)
模板: Next.js 13 App Router (RSC Flight 流数据 + JSON-LD)
功能: 分类全（日/周/月/总/收藏）、图片显示、二级免嗅直链播放
解析: Flight 流数据 + JSON-LD（双路兜底）
"""

import re
import json
import requests
from urllib.parse import urljoin, quote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass


class Spider(BaseSpider):
    def getName(self):
        return "Pektino"

    def init(self, extend=""):
        self.host = "https://pektino.com"
        self.lang = "/zh-CN"
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        # Twitter 视频 CDN 需要 Referer（防盗链）
        self.play_headers = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': 'https://twitter.com/',
            'Origin': 'https://twitter.com',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.timeout = 15

    # ---------------- HTTP ----------------
    def _fetch(self, url):
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                return r.text
        except Exception as e:
            print(f"[fetch] {url} -> {e}")
        return ''

    # ---------------- 图片防盗链 ----------------
    def _fix_pic(self, pic):
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith('//'):
            pic = 'https:' + pic
        elif pic.startswith('/'):
            pic = self.host + pic
        if 'twimg.com' in pic:
            return pic + "@Referer=https://twitter.com/"
        return pic + "@Referer=" + self.host + "/"

    # ---------------- 分类 ----------------
    def _get_classes(self):
        return [
            {"type_id": "daily",    "type_name": "日榜"},
            {"type_id": "weekly",   "type_name": "周榜"},
            {"type_id": "monthly",  "type_name": "月榜"},
            {"type_id": "all",      "type_name": "总榜"},
            {"type_id": "favorite", "type_name": "收藏"},
        ]

    # ---------------- Flight 流数据解析（核心） ----------------
    def _flight_text(self, html):
        """拼接所有 __next_f.push 分片为完整文本"""
        if not html:
            return ''
        fragments = re.findall(
            r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)',
            html
        )
        text = ''
        for frag in fragments:
            try:
                text += frag.encode('utf-8').decode('unicode_escape')
            except Exception:
                pass
        return text

    def _extract_medias(self, text):
        """
        从 Flight 文本中提取所有 media 对象。
        每个 media 对象结构:
        {"id":N,"url_cd":"xxx","url":"https://video.twimg.com/...","time":N,
         "thumbnail":"https://pbs.twimg.com/...","pv":"N","favorite":"N",...}
        """
        videos = []
        seen = set()

        # 主匹配：包含 pv + favorite 的完整 media 对象
        pattern = (
            r'\{"id":\d+,"url_cd":"([^"]+)","url":"([^"]+)","time":(\d+),'
            r'"thumbnail":"([^"]+)"[^}]*?"pv":"?(\d+)"?[^}]*?"favorite":"?(\d+)"?'
        )
        for m in re.finditer(pattern, text):
            url_cd = m.group(1)
            if url_cd in seen:
                continue
            seen.add(url_cd)
            videos.append({
                'url_cd': url_cd,
                'url': m.group(2).replace('\\/', '/'),
                'time': int(m.group(3)),
                'thumbnail': m.group(4).replace('\\/', '/'),
                'pv': m.group(5),
                'favorite': m.group(6),
            })

        # 兜底：宽松匹配（可能缺 pv / favorite）
        if not videos:
            pattern2 = r'"url_cd":"([^"]+)","url":"([^"]+)","time":(\d+),"thumbnail":"([^"]+)"'
            for m in re.finditer(pattern2, text):
                url_cd = m.group(1)
                if url_cd in seen:
                    continue
                seen.add(url_cd)
                videos.append({
                    'url_cd': url_cd,
                    'url': m.group(2).replace('\\/', '/'),
                    'time': int(m.group(3)),
                    'thumbnail': m.group(4).replace('\\/', '/'),
                    'pv': '',
                    'favorite': '',
                })

        return videos

    def _format_duration(self, sec):
        try:
            sec = int(sec)
            if sec >= 3600:
                return f"{sec // 3600}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
            return f"{sec // 60}:{sec % 60:02d}"
        except Exception:
            return ''

    def _media_to_vod(self, m):
        remark_parts = []
        dur = self._format_duration(m.get('time', 0))
        if dur:
            remark_parts.append(dur)
        if m.get('pv'):
            remark_parts.append(f"👁{m['pv']}")
        if m.get('favorite'):
            remark_parts.append(f"❤{m['favorite']}")
        return {
            'vod_id': m['url_cd'],          # ★ 关键：用 url_cd 作为 ID
            'vod_name': m['url_cd'],
            'vod_pic': self._fix_pic(m.get('thumbnail', '')),
            'vod_remarks': ' '.join(remark_parts),
        }

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        html = self._fetch(self.host + self.lang + "/")
        text = self._flight_text(html)
        medias = self._extract_medias(text)
        videos = [self._media_to_vod(m) for m in medias[:30]]
        return {'class': classes, 'list': videos, 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + self.lang + "/")
        text = self._flight_text(html)
        medias = self._extract_medias(text)
        return {'list': [self._media_to_vod(m) for m in medias[:20]]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        path_map = {
            "daily":    f"{self.lang}/",
            "weekly":   f"{self.lang}/weekly",
            "monthly":  f"{self.lang}/monthly",
            "all":      f"{self.lang}/all",
            "favorite": f"{self.lang}/favorite",
        }
        path = path_map.get(tid, f"{self.lang}/")
        if page > 1:
            url = f"{self.host}{path}?page={page}"
        else:
            url = f"{self.host}{path}"

        html = self._fetch(url)
        text = self._flight_text(html)
        medias = self._extract_medias(text)
        videos = [self._media_to_vod(m) for m in medias]

        if not videos and page > 1:
            return {'list': [], 'page': page, 'pagecount': page}

        return {
            'list': videos,
            'page': page,
            'pagecount': 999,
            'limit': len(videos) or 20,
            'total': 0,
        }

    def detailContent(self, ids):
        url_cd = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}{self.lang}/movie/{url_cd}"
        html = self._fetch(url)
        if not html:
            return {'list': []}

        # ① 从 Flight 数据中匹配 url_cd 对应的主 media
        text = self._flight_text(html)
        medias = self._extract_medias(text)
        main = None
        for m in medias:
            if m['url_cd'] == url_cd:
                main = m
                break
        if not main and medias:
            main = medias[0]

        # ② JSON-LD 兜底（从 VideoObject 中取 contentUrl）
        if not main:
            m_ld = re.search(
                r'"contentUrl":"([^"]+)"',
                html
            )
            m_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            m_dur = re.search(r'"duration":"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"', html)
            secs = 0
            if m_dur:
                secs = int(m_dur.group(1) or 0) * 3600 + \
                       int(m_dur.group(2) or 0) * 60 + \
                       int(m_dur.group(3) or 0)
            if m_ld:
                main = {
                    'url_cd': url_cd,
                    'url': m_ld.group(1).replace('\\/', '/'),
                    'thumbnail': m_img.group(1) if m_img else '',
                    'time': secs,
                    'pv': '',
                    'favorite': '',
                }

        if not main:
            return {'list': []}

        # 标题
        title = url_cd
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if h1:
            t = re.sub(r'<[^>]+>', '', h1.group(1)).strip()
            if t:
                title = t
        if not title:
            og_t = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if og_t:
                title = og_t.group(1)

        # 简介
        desc = ''
        og_d = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if og_d:
            desc = og_d.group(1)

        return {'list': [{
            'vod_id': url_cd,
            'vod_name': title,
            'vod_pic': self._fix_pic(main.get('thumbnail', '')),
            'vod_content': desc,
            'vod_play_from': 'Twitter',
            'vod_play_url': f"正片${main['url']}",
        }]}

    # ==================== 免嗅播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        # ① 已是 mp4/m3u8 直链
        if id.startswith('http') and ('.mp4' in id or '.m3u8' in id):
            return {'parse': 0, 'url': id, 'header': self.play_headers}

        # ② 传入的是 url_cd → 请求详情页提取直链
        if re.match(r'^[A-Za-z0-9_-]+$', id):
            url = f"{self.host}{self.lang}/movie/{id}"
            html = self._fetch(url)
            if html:
                # 先试 JSON-LD
                m = re.search(r'"contentUrl":"([^"]+)"', html)
                if m:
                    return {
                        'parse': 0,
                        'url': m.group(1).replace('\\/', '/'),
                        'header': self.play_headers,
                    }
                # 再试 Flight
                text = self._flight_text(html)
                for mm in self._extract_medias(text):
                    if mm['url_cd'] == id:
                        return {'parse': 0, 'url': mm['url'], 'header': self.play_headers}

        # ③ 兜底交给 TVBox 嗅探
        return {'parse': 1, 'url': id, 'header': self.headers}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        url = f"{self.host}/search?tag={quote(key)}"
        if page > 1:
            url += f"&page={page}"
        html = self._fetch(url)
        text = self._flight_text(html)
        medias = self._extract_medias(text)
        videos = [self._media_to_vod(m) for m in medias]
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if videos else page,
            'limit': len(videos) or 20,
            'total': 0,
        }

    # ==================== 辅助 ====================
    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|ts)(\?|$)', url or ''))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def localProxy(self, param):
        return None