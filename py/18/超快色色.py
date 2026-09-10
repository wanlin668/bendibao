# -*- coding: utf-8 -*-
"""
站点: 超快色色 (https://c9d0e1f2.ckss146.cc/)
功能: 分类全（从导航提取），图片显示，二级免嗅
说明: 由于该站视频列表可能 AJAX 加载，若列表为空，请提供真实列表接口
"""

import re
import json
import requests
import base64
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
        return "超快色色"

    def init(self, extend=""):
        self.host = "https://c9d0e1f2.ckss146.cc"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.host + '/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._class_cache = None
        self._play_cache = {}
        self.timeout = 10

    def _fetch(self, url, use_cache=False):
        if use_cache and url in self._play_cache:
            return self._play_cache[url]
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                content = r.text
                if use_cache and content:
                    self._play_cache[url] = content
                return content
        except Exception as e:
            print(f"[fetch] {e}")
        return ''

    # ---------- 分类提取（静态导航） ----------
    def _get_classes(self):
        if self._class_cache:
            return self._class_cache
        html = self._fetch(self.host + "/vodtype/28.html")
        if not html:
            # 保底分类
            return [{"type_id": "28", "type_name": "国产精品"}]
        soup = BeautifulSoup(html, 'html.parser')
        classes = []
        # 查找所有 /vodtype/数字.html 的链接（导航分类）
        for a in soup.find_all('a', href=re.compile(r'^/vodtype/\d+\.html')):
            href = a.get('href')
            m = re.search(r'/vodtype/(\d+)\.html', href)
            if m:
                tid = m.group(1)
                name = a.get_text(strip=True)
                if name and not any(c['type_id'] == tid for c in classes):
                    classes.append({'type_id': tid, 'type_name': name})
        self._class_cache = classes if classes else [{"type_id": "28", "type_name": "国产精品"}]
        print(f"[分类] 共提取 {len(self._class_cache)} 个分类")  # 调试日志
        return self._class_cache

    # ---------- 视频列表解析（兼容静态HTML） ----------
    def _parse_videos(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        # 尝试多种常见选择器
        for item in soup.select('div.vod-item, li.vod-item, div.video-item, div.movie-item'):
            a = item.find('a', href=re.compile(r'/vod/detail/id/\d+\.html|/voddetail/\d+\.html'))
            if not a:
                continue
            href = a.get('href')
            m = re.search(r'/id/(\d+)\.html|/voddetail/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1) or m.group(2)
            title = a.get('title') or a.get_text(strip=True)
            if not title:
                title_el = item.find('h3') or item.find('div', class_='title')
                if title_el:
                    title = title_el.get_text(strip=True)
            if not title:
                title = vid
            pic = ''
            img = item.find('img')
            if img:
                pic = (img.get('data-original') or 
                       img.get('data-src') or 
                       img.get('src') or '')
                if pic and not pic.startswith('http'):
                    pic = urljoin(self.host, pic)
            remark = ''
            time_el = item.find('span', class_='time') or item.find('span', class_='remarks')
            if time_el:
                remark = time_el.get_text(strip=True)
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark
            })
        # 如果没找到任何视频，尝试另一种结构：直接找 a 标签
        if not videos:
            for a in soup.find_all('a', href=re.compile(r'/voddetail/\d+\.html')):
                vid = re.search(r'/voddetail/(\d+)\.html', a.get('href')).group(1)
                title = a.get('title') or a.get_text(strip=True)
                if not title:
                    title = vid
                img = a.find('img')
                pic = ''
                if img:
                    pic = img.get('data-original') or img.get('src') or ''
                    if pic and not pic.startswith('http'):
                        pic = urljoin(self.host, pic)
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': ''
                })
        print(f"[列表] 共提取 {len(videos)} 个视频")  # 调试日志
        return videos

    # ---------- 分页页码 ----------
    def _get_pagecount(self, html, cur):
        soup = BeautifulSoup(html, 'html.parser')
        max_page = cur
        for a in soup.select('.page a, .pagination a, .pages a'):
            text = a.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
            href = a.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        if soup.find('a', string=re.compile(r'下一页|»')):
            if max_page <= cur:
                max_page = cur + 1
        return max_page if max_page > 1 else 1

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        html = self._fetch(self.host + "/vodtype/28.html")
        videos = self._parse_videos(html) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/vodtype/28.html")
        return {'list': self._parse_videos(html)[:20] if html else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        # 尝试两种格式：/vodtype/{tid}-{page}.html 和 /vodtype/{tid}.html
        if page == 1:
            url = f"{self.host}/vodtype/{tid}.html"
        else:
            url = f"{self.host}/vodtype/{tid}-{page}.html"
        html = self._fetch(url)
        if not html:
            # 如果获取不到，尝试 /vod/type/id/{tid}/page/{page}.html
            alt_url = f"{self.host}/vod/type/id/{tid}/page/{page}.html"
            html = self._fetch(alt_url)
        if not html:
            return {'list': [], 'page': page, 'pagecount': 1}
        videos = self._parse_videos(html)
        pagecount = self._get_pagecount(html, page)
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * 20
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        # 尝试多种详情页格式
        urls = [
            f"{self.host}/voddetail/{vid}.html",
            f"{self.host}/vod/detail/id/{vid}.html",
            f"{self.host}/index.php/vod/detail/id/{vid}.html"
        ]
        html = None
        for u in urls:
            html = self._fetch(u)
            if html:
                break
        if not html:
            return {'list': []}
        soup = BeautifulSoup(html, 'html.parser')

        title_tag = soup.find('h1') or soup.find('meta', property='og:title')
        title = title_tag.get_text(strip=True) if title_tag and hasattr(title_tag, 'get_text') else vid

        pic = ''
        img_tag = soup.find('meta', property='og:image')
        if img_tag:
            pic = img_tag.get('content', '')
        if not pic:
            img_tag = soup.find('img', class_='vod_img')
            if img_tag:
                pic = img_tag.get('src') or img_tag.get('data-original') or ''
        if pic and not pic.startswith('http'):
            pic = urljoin(self.host, pic)

        desc = soup.find('meta', attrs={'name': 'description'})
        content = desc.get('content', '') if desc else ''

        # 提取播放列表
        play_from = []
        play_url = []

        from_match = re.search(r'vod_play_from\s*=\s*"([^"]+)"', html)
        url_match = re.search(r'vod_play_url\s*=\s*"([^"]+)"', html)
        if from_match and url_match:
            lines = from_match.group(1).split('$$$')
            urls = url_match.group(1).split('$$$')
            for i, line in enumerate(lines):
                if i < len(urls) and urls[i]:
                    eps = urls[i].split('#')
                    ep_list = []
                    for ep in eps:
                        if '$' in ep:
                            ep_list.append(ep)
                        else:
                            ep_list.append(f"第{len(ep_list)+1}集${ep}")
                    if ep_list:
                        play_from.append(line)
                        play_url.append('#'.join(ep_list))

        if not play_from:
            script = soup.find('script', text=re.compile(r'player_aaaa\s*='))
            if script:
                match = re.search(r'player_aaaa\s*=\s*({.*?});', script.string, re.S)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        vod_data = data.get('vod_data', {})
                        if vod_data:
                            lines = vod_data.get('vod_play_from', '').split('$$$')
                            urls = vod_data.get('vod_play_url', '').split('$$$')
                            for i, line in enumerate(lines):
                                if i < len(urls) and urls[i]:
                                    eps = urls[i].split('#')
                                    ep_list = []
                                    for ep in eps:
                                        if '$' in ep:
                                            ep_list.append(ep)
                                        else:
                                            ep_list.append(f"第{len(ep_list)+1}集${ep}")
                                    if ep_list:
                                        play_from.append(line)
                                        play_url.append('#'.join(ep_list))
                    except:
                        pass

        if not play_from:
            play_from = ['默认线路']
            play_url = [f"第1集${self.host}/vodplay/{vid}-1-1.html"]

        return {'list': [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }]}

    # ==================== 免嗅播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {'parse': 0, 'url': id, 'header': self.headers}
        play_url = id if id.startswith('http') else urljoin(self.host + '/', id)
        return self._extract_real_url(play_url, depth=0)

    def _extract_real_url(self, url, depth=0):
        if depth > 3:
            return {'parse': 1, 'url': url}
        html = self._fetch(url, use_cache=True)
        if not html:
            return {'parse': 1, 'url': url}

        # 快速匹配直链
        direct = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if direct:
            return {'parse': 0, 'url': direct.group(1), 'header': self.headers}

        # 常见变量
        var_match = re.search(r'var\s+(?:url|video_url|playurl)\s*=\s*["\']([^"\']+)["\']', html)
        if var_match:
            real = var_match.group(1)
            if not real.startswith('http'):
                real = urljoin(self.host + '/', real)
            if real.startswith('http'):
                return {'parse': 0, 'url': real, 'header': self.headers}

        # player_aaaa 等 JSON
        json_patterns = [
            r'player_aaaa\s*=\s*({.*?});',
            r'player_bbbb\s*=\s*({.*?});',
            r'player_data\s*=\s*({.*?});',
            r'var\s+config\s*=\s*({.*?});',
            r'var\s+video\s*=\s*({.*?});',
        ]
        for pat in json_patterns:
            match = re.search(pat, html, re.S)
            if match:
                try:
                    data = json.loads(match.group(1))
                    real = data.get('url') or data.get('src') or data.get('playUrl') or ''
                    if real:
                        enc = data.get('encrypt', 0)
                        if enc == 1:
                            real = unquote(real)
                        elif enc == 2:
                            real = base64.b64decode(real).decode('utf-8')
                        elif enc == 3:
                            real = unescape(real)
                        if not real.startswith('http'):
                            real = urljoin(self.host + '/', real)
                        if real.startswith('http'):
                            return {'parse': 0, 'url': real, 'header': self.headers}
                except:
                    pass

        # iframe 递归
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            if not iframe_url.startswith('http'):
                iframe_url = urljoin(self.host + '/', iframe_url)
            return self._extract_real_url(iframe_url, depth + 1)

        # video/source
        video_src = re.search(r'<video[^>]+src="([^"]+)"', html)
        if video_src:
            src = video_src.group(1)
            if not src.startswith('http'):
                src = urljoin(self.host + '/', src)
            if src.startswith('http'):
                return {'parse': 0, 'url': src, 'header': self.headers}
        source_src = re.search(r'<source[^>]+src="([^"]+)"', html)
        if source_src:
            src = source_src.group(1)
            if not src.startswith('http'):
                src = urljoin(self.host + '/', src)
            if src.startswith('http'):
                return {'parse': 0, 'url': src, 'header': self.headers}

        return {'parse': 1, 'url': url}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        url = f"{self.host}/vodsearch/-------------.html?wd={quote(key)}&page={page}"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page}
        videos = self._parse_videos(html)
        pagecount = self._get_pagecount(html, page)
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * 20
        }

    # ==================== 辅助 ====================
    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.session.close()
        self._play_cache.clear()

    def localProxy(self, param):
        return None