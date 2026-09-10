# -*- coding: utf-8 -*-
# 站点：倒茶小妹 (chamm238.xyz)
# TVBox 爬虫 - 免嗅强化版
# 功能：首页分类 / 列表 / 详情 / 播放（直链提取）/ 搜索
# 特点：playerContent 强制返回真实流地址（parse:0），无需TVBox嗅探

import re
import json
import requests
import base64
from urllib.parse import urljoin, quote, unquote
from base.spider import Spider

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class Spider(Spider):
    def getName(self):
        return "倒茶小妹"

    def init(self, extend=""):
        # ========================================
        # ★★★ 如果域名失效，只改这里 ★★★
        self.host = "https://y5z6a7b8.chamm238.xyz"
        # ========================================
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
        }
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ---------- 请求 ----------
    def _get(self, url, referer=None):
        if not url.startswith("http"):
            url = urljoin(self.host, url)
        headers = self.headers.copy()
        if referer:
            headers["Referer"] = referer
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print(f"请求失败: {e}")
        return ""

    # ---------- 图片处理 ----------
    def _pic(self, url):
        if not url:
            return ""
        if not url.startswith("http"):
            url = urljoin(self.host, url)
        return url + "@Referer=" + self.host + "/"

    # ========== 首页 ==========
    def homeContent(self, filter=False):
        classes = [
            {"type_id": "6", "type_name": "麻豆视频"},
            {"type_id": "7", "type_name": "91制片厂"},
            {"type_id": "8", "type_name": "天美传媒"},
            {"type_id": "9", "type_name": "蜜桃传媒"},
            {"type_id": "10", "type_name": "皇家华人"},
            {"type_id": "11", "type_name": "星空传媒"},
            {"type_id": "12", "type_name": "精东影业"},
            {"type_id": "20", "type_name": "乐播传媒"},
            {"type_id": "21", "type_name": "兔子先生"},
            {"type_id": "22", "type_name": "杏吧原创"},
            {"type_id": "23", "type_name": "玩偶姐姐"},
            {"type_id": "24", "type_name": "mini传媒"},
            {"type_id": "25", "type_name": "大象传媒"},
            {"type_id": "26", "type_name": "性视界"},
            {"type_id": "28", "type_name": "国产精品"},
            {"type_id": "29", "type_name": "华语AV"},
            {"type_id": "30", "type_name": "成人头条"},
            {"type_id": "31", "type_name": "开心鬼传媒"},
            {"type_id": "32", "type_name": "糖心Vlog"},
            {"type_id": "33", "type_name": "萝莉社"},
            {"type_id": "34", "type_name": "乌鸦传媒"},
            {"type_id": "37", "type_name": "PsychoPorn"},
            {"type_id": "62", "type_name": "主播网红"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self.categoryContent("6", "1", False, {})

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        url = f"/vodtype/{tid}.html" if page == 1 else f"/vodtype/{tid}-{page}.html"
        html = self._get(url)
        if not html:
            return {"list": [], "page": page, "pagecount": 1}

        videos = []
        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=re.compile(r"/voddetail/\d+\.html")):
                href = a.get("href")
                m = re.search(r"/voddetail/(\d+)\.html", href)
                if not m:
                    continue
                vid = m.group(1)
                title = a.get("title") or a.get_text(strip=True)
                if not title:
                    img = a.find("img")
                    if img and img.get("alt"):
                        title = img.get("alt")
                if not title:
                    title = vid
                pic = ""
                img = a.find("img")
                if img:
                    pic = img.get("data-src") or img.get("src") or ""
                pic = self._pic(pic)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
        else:
            pattern = r'<a[^>]+href="(/voddetail/(\d+)\.html)"[^>]*>(.*?)</a>'
            for match in re.finditer(pattern, html, re.DOTALL):
                href, vid, content = match.groups()
                title = re.sub(r'<[^>]+>', '', content).strip()
                if not title:
                    alt_m = re.search(r'<img[^>]+alt="([^"]+)"', content)
                    if alt_m:
                        title = alt_m.group(1)
                if not title:
                    title = vid
                pic = ""
                img_m = re.search(r'<img[^>]+(?:data-src|src)="([^"]+)"', content)
                if img_m:
                    pic = img_m.group(1)
                pic = self._pic(pic)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })

        page_nums = re.findall(r'page[/=](\d+)', html)
        if page_nums:
            max_page = max(map(int, page_nums))
        else:
            if re.search(r'下一页|»|next', html, re.I):
                max_page = page + 1
            else:
                max_page = page

        return {
            "list": videos,
            "page": page,
            "pagecount": max_page,
            "limit": len(videos),
            "total": max_page * (len(videos) if videos else 20),
        }

    # ========== 详情页 ==========
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        url = f"/voddetail/{vid}.html"
        html = self._get(url)
        if not html:
            return {"list": []}

        title = vid
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if h1:
            title = re.sub(r'<[^>]+>', '', h1.group(1)).strip()
        if not title:
            t = re.search(r'<title>(.*?)</title>', html)
            if t:
                title = t.group(1).split('-')[0].strip()

        pic = ""
        og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if og:
            pic = og.group(1)
        if not pic:
            img = re.search(r'<img[^>]+class="[^"]*poster[^"]*"[^>]+src="([^"]+)"', html)
            if img:
                pic = img.group(1)
        pic = self._pic(pic)

        content = ""
        desc = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        if desc:
            content = desc.group(1)

        play_from = "默认线路"
        play_url = f"第1集$/vodplay/{vid}-1-1.html"

        from_match = re.search(r'vod_play_from\s*=\s*"([^"]+)"', html)
        url_match = re.search(r'vod_play_url\s*=\s*"([^"]+)"', html)
        if from_match and url_match:
            f_str = from_match.group(1)
            u_str = url_match.group(1)
            if f_str and u_str:
                lines = f_str.split("$$$")
                urls = u_str.split("$$$")
                if lines and urls and len(lines) == len(urls):
                    play_from = lines[0]
                    eps = urls[0].split("#") if "#" in urls[0] else [urls[0]]
                    parts = []
                    for i, ep in enumerate(eps):
                        if '$' in ep:
                            name, ep_url = ep.split('$', 1)
                            parts.append(f"{name}${ep_url}")
                        else:
                            parts.append(f"第{i+1}集${ep}")
                    play_url = "#".join(parts)

        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": content,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }]}

    # ========== 播放页（免嗅核心） ==========
    def playerContent(self, flag, id, vipFlags=None):
        # 如果已经是直链
        if id.startswith("http") and (".m3u8" in id or ".mp4" in id):
            return {"parse": 0, "url": id}

        # 构建播放页URL
        if not id.startswith("http"):
            play_url = urljoin(self.host, id)
        else:
            play_url = id

        # 请求播放页（携带Referer）
        html = self._get(play_url, referer=self.host + "/")
        if not html:
            # 如果页面获取失败，尝试直接返回原始链接让TVBox嗅探（但这不是免嗅）
            # 这里我们尽力返回parse:0，所以继续尝试其他方式
            # 既然无法获取页面，只能返回parse:1让TVBox处理
            return {"parse": 1, "url": play_url}

        # ----- 提取真实播放地址（多种方式） -----

        # 1. player_aaaa
        real_url = self._extract_from_player_aaaa(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 2. player_bbb / player_data 等其他常见变量
        real_url = self._extract_from_other_players(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 3. iframe 嵌套（递归解析）
        real_url = self._extract_from_iframe(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 4. video 标签或 source 标签
        real_url = self._extract_from_video_tag(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 5. 直接匹配 m3u8/mp4 链接
        real_url = self._extract_direct_url(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 6. 尝试从页面中的 JavaScript 变量提取
        real_url = self._extract_from_js_vars(html)
        if real_url:
            return {"parse": 0, "url": real_url}

        # 所有方法都失败，交给TVBox嗅探（但尽量不走到这一步）
        return {"parse": 1, "url": play_url}

    # ----- 辅助提取方法 -----

    def _extract_from_player_aaaa(self, html):
        """从 player_aaaa 提取"""
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                url = data.get("url", "")
                if url:
                    encrypt = data.get("encrypt", 0)
                    if encrypt == 1:
                        url = unquote(url)
                    elif encrypt == 2:
                        url = base64.b64decode(url).decode("utf-8")
                    if url.startswith("http"):
                        return url
            except:
                pass
        return None

    def _extract_from_other_players(self, html):
        """从 player_bbb, player_data 等变量提取"""
        patterns = [
            r'player_bbb\s*=\s*(\{.*?\});',
            r'player_data\s*=\s*(\{.*?\});',
            r'var\s+video\s*=\s*(\{.*?\});',
            r'var\s+config\s*=\s*(\{.*?\});',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    url = data.get("url") or data.get("src") or data.get("playUrl") or ""
                    if url and url.startswith("http"):
                        return url
                except:
                    pass
        return None

    def _extract_from_iframe(self, html):
        """从 iframe 递归解析"""
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            if not iframe_url.startswith("http"):
                iframe_url = urljoin(self.host, iframe_url)
            # 递归请求 iframe 页面
            sub_html = self._get(iframe_url, referer=self.host + "/")
            if sub_html:
                # 在子页面再次尝试提取
                real = self._extract_from_player_aaaa(sub_html)
                if real:
                    return real
                real = self._extract_from_other_players(sub_html)
                if real:
                    return real
                real = self._extract_direct_url(sub_html)
                if real:
                    return real
        return None

    def _extract_from_video_tag(self, html):
        """从 <video> 或 <source> 标签提取"""
        m = re.search(r'<video[^>]+src="([^"]+)"', html)
        if m:
            url = m.group(1)
            if url.startswith("http"):
                return url
        m = re.search(r'<source[^>]+src="([^"]+)"', html)
        if m:
            url = m.group(1)
            if url.startswith("http"):
                return url
        return None

    def _extract_direct_url(self, html):
        """直接匹配 m3u8/mp4 链接"""
        m = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if m:
            return m.group(1)
        return None

    def _extract_from_js_vars(self, html):
        """从常见的 JS 变量名提取"""
        patterns = [
            r'var\s+url\s*=\s*"([^"]+)"',
            r'var\s+playUrl\s*=\s*"([^"]+)"',
            r'var\s+video_url\s*=\s*"([^"]+)"',
            r'var\s+src\s*=\s*"([^"]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                url = m.group(1)
                if url.startswith("http"):
                    return url
        return None

    # ========== 搜索 ==========
    def searchContent(self, key, quick=False, pg="1"):
        page = int(pg) if pg else 1
        url = f"/vodsearch/-------------.html?wd={quote(key)}&page={page}"
        html = self._get(url)
        if not html:
            return {"list": [], "page": page, "pagecount": 1}

        videos = []
        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=re.compile(r"/voddetail/\d+\.html")):
                href = a.get("href")
                m = re.search(r"/voddetail/(\d+)\.html", href)
                if not m:
                    continue
                vid = m.group(1)
                title = a.get("title") or a.get_text(strip=True)
                if not title:
                    img = a.find("img")
                    if img and img.get("alt"):
                        title = img.get("alt")
                if not title:
                    title = vid
                pic = ""
                img = a.find("img")
                if img:
                    pic = img.get("data-src") or img.get("src") or ""
                pic = self._pic(pic)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
        else:
            pattern = r'<a[^>]+href="(/voddetail/(\d+)\.html)"[^>]*>(.*?)</a>'
            for match in re.finditer(pattern, html, re.DOTALL):
                href, vid, content = match.groups()
                title = re.sub(r'<[^>]+>', '', content).strip()
                if not title:
                    alt_m = re.search(r'<img[^>]+alt="([^"]+)"', content)
                    if alt_m:
                        title = alt_m.group(1)
                if not title:
                    title = vid
                pic = ""
                img_m = re.search(r'<img[^>]+(?:data-src|src)="([^"]+)"', content)
                if img_m:
                    pic = img_m.group(1)
                pic = self._pic(pic)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })

        return {
            "list": videos,
            "page": page,
            "pagecount": page + 1 if len(videos) >= 20 else page,
            "limit": len(videos),
            "total": 9999,
        }

    # ========== 辅助 ==========
    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|ts)(\?|$)', url))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        if hasattr(self, "session"):
            self.session.close()