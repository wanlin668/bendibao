# -*- coding: utf-8 -*-
"""
站点: 极品舞姬 (https://xn--88-11-fq5haa0376d.jpwji.sbs/facai/)
功能: 分类(仅视频一区及其子分类)、图片强制修复、二级免嗅播放、强制翻页
说明: 确保所有分类都能翻页，不受页面控件影响
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
        return "极品舞姬"

    def init(self, extend=""):
        self.host = "https://xn--88-11-fq5haa0376d.jpwji.sbs"
        self.base_path = "/facai"
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._class_cache = None
        self._play_cache = {}
        self.timeout = 15

        # 硬编码分类：仅视频一区及其子分类
        self.hardcoded_classes = [
            {"type_id": "1", "type_name": "视频一区"},
            {"type_id": "6", "type_name": "国产自拍"},
            {"type_id": "7", "type_name": "精品推荐"},
            {"type_id": "8", "type_name": "网曝门"},
            {"type_id": "9", "type_name": "国产传媒"},
            {"type_id": "10", "type_name": "主播秀色"},
            {"type_id": "11", "type_name": "自拍偷拍"},
            {"type_id": "12", "type_name": "国产乱伦"},
            {"type_id": "20", "type_name": "韩国主播"},
        ]

    def _fetch(self, url, use_cache=False):
        if use_cache and url in self._play_cache:
            return self._play_cache[url]
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                content = r.text
                if '验证' in content or 'captcha' in content.lower():
                    return ''
                if use_cache and content:
                    self._play_cache[url] = content
                return content
        except Exception as e:
            print(f"[fetch] {e}")
        return ''

    # ========== 终极图片提取与修复 ==========
    def _fix_pic(self, pic):
        """修复图片URL，确保绝对路径和Referer"""
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith('//'):
            pic = 'https:' + pic
        if pic.startswith('/'):
            base = self.host + self.base_path + '/'
            pic = urljoin(base, pic)
        if not pic.startswith('http'):
            base = self.host + self.base_path + '/'
            pic = urljoin(base, pic)
        return pic + "@Referer=" + self.host + "/"

    def _extract_pic_from_element(self, element):
        """从任意元素中提取图片URL，穷举所有可能"""
        img = element.find('img')
        if img:
            for attr in ['data-original', 'data-src', 'data-lazy-src', 'data-echo', 'src']:
                val = img.get(attr)
                if val:
                    return val
        style = element.get('style', '')
        bg_match = re.search(r'background(?:-image)?\s*:\s*url\([\'"]?([^\)\'"]+)[\'"]?\)', style)
        if bg_match:
            return bg_match.group(1)
        data_url = element.get('data-url') or element.get('data-cover') or element.get('data-poster')
        if data_url:
            return data_url
        if element.name == 'a':
            parent = element.parent
            if parent:
                return self._extract_pic_from_element(parent)
        return None

    def _get_classes(self):
        if self._class_cache:
            return self._class_cache
        self._class_cache = self.hardcoded_classes
        return self._class_cache

    # ---------- 视频列表解析 ----------
    def _parse_videos(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        items = soup.select('li.vod-item, div.vod-item, li.item, div.item, a[href*="/vod/detail/id/"]')
        if not items:
            items = soup.find_all('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
        for item in items:
            if item.name == 'a' and item.get('href', '').startswith('/facai/index.php/vod/detail/id/'):
                a = item
            else:
                a = item.find('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
                if not a:
                    continue
            href = a.get('href')
            m = re.search(r'/vod/detail/id/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1)
            title = a.get('title') or a.get_text(strip=True)
            if not title:
                title = a.find('img').get('alt', '') if a.find('img') else ''
            if not title:
                title = vid

            pic = ''
            pic_url = self._extract_pic_from_element(item)
            if pic_url:
                pic = self._fix_pic(pic_url)
            if not pic:
                pic_url = self._extract_pic_from_element(a)
                if pic_url:
                    pic = self._fix_pic(pic_url)
            if not pic:
                img = soup.find('img', alt=re.compile(title[:10]))
                if img:
                    pic = self._fix_pic(img.get('src') or img.get('data-src', ''))

            remark = ''
            span = item.find('span', class_='remark') or item.find('span', class_='time')
            if span:
                remark = span.get_text(strip=True)

            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark
            })
        return videos

    # ========== 强制分页逻辑 ==========
    def _get_pagecount(self, html, cur):
        """
        强制翻页：如果当前页有视频，则返回 cur+1，让 TVBox 尝试加载下一页。
        如果请求下一页返回空，TVBox 会自动停止。
        """
        # 1. 尝试从页面提取页码链接
        soup = BeautifulSoup(html, 'html.parser')
        page_links = soup.find_all('a', href=re.compile(r'/vod/type/id/\d+/page/\d+\.html'))
        if page_links:
            pages = []
            for a in page_links:
                m = re.search(r'/page/(\d+)\.html', a.get('href', ''))
                if m:
                    pages.append(int(m.group(1)))
            if pages:
                return max(pages)

        # 2. 如果当前页有视频（至少1个），强制返回 cur+1
        items = soup.select('li.vod-item, div.vod-item, li.item, div.item, a[href*="/vod/detail/id/"]')
        if len(items) > 0:
            return cur + 1

        # 3. 没有任何视频，说明已经是最后一页
        return cur

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        html = self._fetch(self.host + self.base_path + "/index.php/vod/type/id/20.html")
        videos = self._parse_videos(html) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + self.base_path + "/index.php/vod/type/id/20.html")
        return {'list': self._parse_videos(html)[:20] if html else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        if page == 1:
            url = f"{self.host}{self.base_path}/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.host}{self.base_path}/index.php/vod/type/id/{tid}/page/{page}.html"
        html = self._fetch(url)
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
        url = f"{self.host}{self.base_path}/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
        html = self._fetch(url)
        if not html:
            return {'list': []}
        soup = BeautifulSoup(html, 'html.parser')

        title = ''
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            og = soup.find('meta', property='og:title')
            if og:
                title = og.get('content', '')
        if not title:
            title = vid

        pic = ''
        og_img = soup.find('meta', property='og:image')
        if og_img:
            pic = og_img.get('content', '')
        if not pic:
            img = soup.find('img', class_='poster')
            if img:
                pic = img.get('src') or ''
        if pic:
            pic = self._fix_pic(pic)

        desc = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
        if not desc:
            desc_div = soup.find('div', class_='vod_content')
            if desc_div:
                desc = desc_div.get_text(strip=True)

        # ----- 提取播放列表（多线路） -----
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
            play_url = [f"第1集${self.host}{self.base_path}/index.php/vod/play/id/{vid}/sid/1/nid/1.html"]

        return {'list': [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': desc,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }]}

    # ==================== 免嗅播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {'parse': 0, 'url': id, 'header': self.headers}

        if not id.startswith('http'):
            id = urljoin(self.host + self.base_path + '/', id)

        html = self._fetch(id, use_cache=True)
        if not html:
            return {'parse': 1, 'url': id}

        # 1. player_aaaa
        match = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                real_url = data.get('url', '')
                if real_url:
                    encrypt = data.get('encrypt', 0)
                    if encrypt == 1:
                        real_url = unquote(real_url)
                    elif encrypt == 2:
                        real_url = base64.b64decode(real_url).decode('utf-8')
                    if real_url.startswith('http'):
                        return {'parse': 0, 'url': real_url, 'header': self.headers}
            except:
                pass

        # 2. other variables
        patterns = [
            r'player_bbbb\s*=\s*(\{.*?\});',
            r'player_data\s*=\s*(\{.*?\});',
            r'var\s+video\s*=\s*(\{.*?\});',
            r'var\s+config\s*=\s*(\{.*?\});',
            r'var\s+url\s*=\s*["\']([^"\']+)["\']',
            r'var\s+playUrl\s*=\s*["\']([^"\']+)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    raw = m.group(1)
                    if raw.startswith('{'):
                        data = json.loads(raw)
                        real_url = data.get('url') or data.get('src') or data.get('playUrl') or ''
                        if real_url:
                            if not real_url.startswith('http'):
                                real_url = urljoin(self.host + self.base_path + '/', real_url)
                            if real_url.startswith('http'):
                                return {'parse': 0, 'url': real_url, 'header': self.headers}
                    else:
                        real_url = raw
                        if not real_url.startswith('http'):
                            real_url = urljoin(self.host + self.base_path + '/', real_url)
                        if real_url.startswith('http'):
                            return {'parse': 0, 'url': real_url, 'header': self.headers}
                except:
                    pass

        # 3. iframe
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            if not iframe_url.startswith('http'):
                iframe_url = urljoin(self.host + self.base_path + '/', iframe_url)
            return self._extract_real_url(iframe_url, depth=1)

        # 4. video / source
        video_src = re.search(r'<video[^>]+src="([^"]+)"', html)
        if video_src:
            src = video_src.group(1)
            if not src.startswith('http'):
                src = urljoin(self.host + self.base_path + '/', src)
            if src.startswith('http'):
                return {'parse': 0, 'url': src, 'header': self.headers}
        source_src = re.search(r'<source[^>]+src="([^"]+)"', html)
        if source_src:
            src = source_src.group(1)
            if not src.startswith('http'):
                src = urljoin(self.host + self.base_path + '/', src)
            if src.startswith('http'):
                return {'parse': 0, 'url': src, 'header': self.headers}

        # 5. direct m3u8/mp4
        direct = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if direct:
            return {'parse': 0, 'url': direct.group(1), 'header': self.headers}

        return {'parse': 1, 'url': id}

    def _extract_real_url(self, url, depth=0):
        if depth > 3:
            return {'parse': 1, 'url': url}
        return self.playerContent(None, url, None)

    # ==================== 搜索 ====================
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        url = f"{self.host}{self.base_path}/index.php/vod/search.html?wd={quote(key)}"
        if page > 1:
            url += f"&page={page}"
        html = self._fetch(url)
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

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|ts)(\?|$)', url))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if hasattr(self, "session"):
            self.session.close()

    def localProxy(self, param):
        return None