# -*- coding: utf-8 -*-
"""
站点: AI情色 (https://ikkop5236.aixxx.top/)
功能: 
  - 分类全（含"⭐推荐"分页，已修正路径格式）
  - 图片显示（支持背景图）
  - 二级免嗅播放
  - 搜索强制翻页
  - 标题提取增强（多重备选）
"""

import re
import json
import requests
import base64
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote, urlparse, parse_qs

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
        return "AI情色"

    def init(self, extend=""):
        self.host = "https://ikkop5236.aixxx.top"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
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
                if '验证' in content or 'captcha' in content.lower():
                    print("[调试] 被反爬拦截")
                    return ''
                if use_cache and content:
                    self._play_cache[url] = content
                return content
        except Exception as e:
            print(f"[fetch] {e}")
        return ''

    def _fix_pic(self, pic):
        if not pic:
            return ''
        if not pic.startswith('http'):
            pic = urljoin(self.host, pic)
        return pic + "@Referer=" + self.host + "/"

    # ---------- 分类提取（增加推荐分类） ----------
    def _get_classes(self):
        if self._class_cache:
            return self._class_cache
        html = self._fetch(self.host + "/")
        if not html:
            return [{"type_id": "recommend", "type_name": "⭐推荐"}]
        soup = BeautifulSoup(html, 'html.parser')
        classes = []
        for a in soup.select('.header-list-row ul li a'):
            href = a.get('href', '')
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            k = params.get('k', [''])[0]
            if not k:
                continue
            name = a.get_text(strip=True)
            name = re.sub(r'[^\w\u4e00-\u9fa5]', '', name)
            if name and k:
                classes.append({'type_id': k, 'type_name': name})
        # 将推荐分类放在第一位
        recommend = {"type_id": "recommend", "type_name": "⭐推荐"}
        self._class_cache = [recommend] + classes if classes else [recommend]
        return self._class_cache

    # ---------- 视频列表解析（增强标题提取） ----------
    def _parse_videos(self, html, debug=False):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        for a in soup.find_all('a', href=re.compile(r'/video/.*\.html')):
            href = a.get('href')
            if not href:
                continue
            vid = href.split('/')[-1].replace('.html', '')
            
            # ---- 标题提取（多重后备） ----
            title = None
            # 1. 从 a 标签的 title 属性
            title = a.get('title', '').strip()
            # 2. 如果无，从 img 的 alt/title 属性
            if not title:
                img = a.find('img')
                if img:
                    title = img.get('alt', '').strip()
                    if not title:
                        title = img.get('title', '').strip()
            # 3. 从父级容器中的标题类（常见类名）
            if not title:
                parent = a.parent
                if parent:
                    for cls in ['th-title', 'title', 'video-title', 'name', 'vod-name']:
                        el = parent.find('a', class_=cls) or parent.find('div', class_=cls)
                        if el:
                            title = el.get_text(strip=True)
                            break
                    if not title:
                        h3 = parent.find(['h3', 'h2'])
                        if h3:
                            title = h3.get_text(strip=True)
            # 4. 如果还为空，尝试从 a 标签的文本
            if not title:
                title = a.get_text(strip=True)
            # 5. 最终回退到 vid
            if not title:
                title = vid
            
            # ---- 图片提取 ----
            pic = ''
            img = a.find('img')
            if img:
                pic = img.get('src') or img.get('data-src') or ''
                if pic and 'data:image' not in pic:
                    pic = self._fix_pic(pic)
            # 如果图片仍为空，尝试从父级背景图提取
            if not pic:
                parent = a.parent
                if parent:
                    bg = parent.get('style') or ''
                    m = re.search(r'url\(["\']?(.+?)["\']?\)', bg)
                    if m:
                        pic = m.group(1)
                        if not pic.startswith('http'):
                            pic = urljoin(self.host, pic)
                        pic = self._fix_pic(pic)
            
            # ---- 备注（时长/清晰度） ----
            duration = ''
            quality = ''
            parent = a.parent
            if parent:
                dur_el = parent.find('span', class_='th-duration')
                if dur_el:
                    duration = dur_el.get_text(strip=True).replace('⏱', '').strip()
                q_el = parent.find('span', class_='th-videos')
                if q_el:
                    quality = q_el.get_text(strip=True).replace('✨', '').strip()
            remark = f"{duration} {quality}".strip()
            
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark
            })
        
        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique.append(v)
        
        if debug:
            print(f"[调试] 提取到 {len(unique)} 个视频")
            for i, v in enumerate(unique[:3]):
                print(f"  示例 {i+1}: {v['vod_name']} (ID: {v['vod_id']})")
        return unique

    # ---------- 翻页页码计算（兼容路径格式和查询参数） ----------
    def _get_pagecount(self, html, cur):
        soup = BeautifulSoup(html, 'html.parser')
        # 优先在分页容器中查找
        pagination = soup.find('div', class_='pages-row')
        if not pagination:
            pagination = soup.find('ul', class_='pagination')
        if pagination:
            max_page = cur
            for a in pagination.find_all('a', href=True):
                href = a['href']
                # 匹配路径格式 /数字（如 /10）
                m = re.search(r'/(\d+)$', href)
                if not m:
                    # 匹配查询参数 ?page=数字 或 &page=数字
                    m = re.search(r'[?&]page=(\d+)', href)
                if m:
                    p = int(m.group(1))
                    if p > max_page:
                        max_page = p
            return max_page
        else:
            # 没有分页容器，回退到旧逻辑
            max_page = cur
            for a in soup.find_all('a', href=re.compile(r'[?&]page=\d+')):
                m = re.search(r'page=(\d+)', a.get('href', ''))
                if m:
                    p = int(m.group(1))
                    if p > max_page:
                        max_page = p
            if max_page == cur:
                video_count = len(soup.select('div.th')) + len(soup.find_all('a', href=re.compile(r'/video/.*\.html')))
                if video_count >= 8:
                    return cur + 1
                else:
                    return cur
            return max_page

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        html = self._fetch(self.host + "/")
        videos = self._parse_videos(html, debug=True) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        return {'list': self._parse_videos(html)[:20] if html else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        if tid == "recommend":
            # 推荐分页使用路径格式：/数字
            if page == 1:
                url = self.host + "/"
            else:
                url = self.host + "/" + str(page)
        else:
            # 其他分类使用查询参数（保持原样）
            url = f"{self.host}/?k={tid}"
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

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}/video/{vid}.html"
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
            img = soup.find('img')
            if img:
                pic = img.get('src', '')
        if pic:
            pic = self._fix_pic(pic)

        desc = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')

        play_url = ''
        video = soup.find('video')
        if video:
            play_url = video.get('src', '')
        if not play_url:
            source = soup.find('source')
            if source:
                play_url = source.get('src', '')
        if not play_url:
            script = soup.find('script', text=re.compile(r'player_aaaa\s*='))
            if script:
                match = re.search(r'player_aaaa\s*=\s*({.*?});', script.string, re.S)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        play_url = data.get('url', '')
                        if play_url:
                            encrypt = data.get('encrypt', 0)
                            if encrypt == 1:
                                play_url = unquote(play_url)
                            elif encrypt == 2:
                                play_url = base64.b64decode(play_url).decode('utf-8')
                    except:
                        pass
        if not play_url:
            m = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
            if m:
                play_url = m.group(1)

        if play_url and not play_url.startswith('http'):
            play_url = urljoin(self.host, play_url)

        return {'list': [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': desc,
            'vod_play_from': '默认线路',
            'vod_play_url': f'正片${play_url}' if play_url else ''
        }]}

    # ==================== 免嗅播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {'parse': 0, 'url': id, 'header': self.headers}
        if not id.startswith('http'):
            id = urljoin(self.host + '/', id)
        return self._extract_real_url(id, depth=0)

    def _extract_real_url(self, url, depth=0):
        if depth > 3:
            return {'parse': 1, 'url': url}
        html = self._fetch(url, use_cache=True)
        if not html:
            return {'parse': 1, 'url': url}

        direct = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if direct:
            return {'parse': 0, 'url': direct.group(1), 'header': self.headers}

        var_match = re.search(r'var\s+(?:url|video_url|playurl)\s*=\s*["\']([^"\']+)["\']', html)
        if var_match:
            real = var_match.group(1)
            if not real.startswith('http'):
                real = urljoin(self.host + '/', real)
            if real.startswith('http'):
                return {'parse': 0, 'url': real, 'header': self.headers}

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
                        encrypt = data.get('encrypt', 0)
                        if encrypt == 1:
                            real = unquote(real)
                        elif encrypt == 2:
                            real = base64.b64decode(real).decode('utf-8')
                        elif encrypt == 3:
                            real = unescape(real)
                        if not real.startswith('http'):
                            real = urljoin(self.host + '/', real)
                        if real.startswith('http'):
                            return {'parse': 0, 'url': real, 'header': self.headers}
                except:
                    pass

        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            if not iframe_url.startswith('http'):
                iframe_url = urljoin(self.host + '/', iframe_url)
            return self._extract_real_url(iframe_url, depth + 1)

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

    # ==================== 搜索（强制翻页） ====================
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        url = f"{self.host}/?k={quote(key)}"
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
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.session.close()
        self._play_cache.clear()

    def localProxy(self, param):
        return None