# -*- coding: utf-8 -*-
"""
站点: 8X色色影 (https://722647.8xssy2011.top/8xse/)
功能: 分类全、图片显示、二级免嗅播放、翻页
解析: BeautifulSoup
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
        return "8X色色影"

    def init(self, extend=""):
        self.host = "https://722647.8xssy2011.top"
        self.base_path = "/8xse"
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

    def _fix_pic(self, pic):
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith('//'):
            pic = 'https:' + pic
        if pic.startswith('/'):
            pic = urljoin(self.host + self.base_path + '/', pic)
        if not pic.startswith('http'):
            pic = urljoin(self.host + self.base_path + '/', pic)
        return pic + "@Referer=" + self.host + "/"

    # ---------- 分类提取（动态从首页解析） ----------
    def _get_classes(self):
        if self._class_cache:
            return self._class_cache

        # 尝试从首页动态提取分类
        html = self._fetch(self.host + self.base_path + "/")
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            classes = []
            seen = set()
            # 查找所有 category-subs 中的子分类链接
            for a in soup.select('.category-subs a'):
                href = a.get('href', '')
                m = re.search(r'/vod/type/id/(\d+)\.html', href)
                if m:
                    tid = m.group(1)
                    name = a.get_text(strip=True)
                    if name and tid not in seen:
                        seen.add(tid)
                        classes.append({'type_id': tid, 'type_name': name})
            if classes:
                self._class_cache = classes
                return classes

        # 如果动态提取失败，使用硬编码分类（从源码中提取）
        self._class_cache = [
            {"type_id": "94", "type_name": "网曝黑料"},
            {"type_id": "95", "type_name": "国产视频"},
            {"type_id": "96", "type_name": "国产主播"},
            {"type_id": "97", "type_name": "国产传媒"},
            {"type_id": "98", "type_name": "女同性恋"},
            {"type_id": "99", "type_name": "网红头条"},
            {"type_id": "100", "type_name": "明星换脸"},
            {"type_id": "101", "type_name": "抖阴视频"},
            {"type_id": "102", "type_name": "激情动漫"},
            {"type_id": "103", "type_name": "SM调教"},
            {"type_id": "104", "type_name": "韩国主播"},
            {"type_id": "105", "type_name": "VR视角"},
            {"type_id": "106", "type_name": "人妖系列"},
            {"type_id": "107", "type_name": "中文字幕"},
            {"type_id": "108", "type_name": "日本有码"},
            {"type_id": "109", "type_name": "日本无码"},
            {"type_id": "110", "type_name": "欧美无码"},
            {"type_id": "111", "type_name": "女优明星"},
            {"type_id": "112", "type_name": "强奸乱伦"},
            {"type_id": "113", "type_name": "萝莉少女"},
            {"type_id": "114", "type_name": "伦理三级"},
            {"type_id": "115", "type_name": "制服诱惑"},
            {"type_id": "116", "type_name": "AV解说"},
            {"type_id": "62", "type_name": "国产乱伦"},
            {"type_id": "77", "type_name": "国产视频(二)"},
            {"type_id": "49", "type_name": "精品推荐"},
            {"type_id": "50", "type_name": "直播做爱"},
            {"type_id": "54", "type_name": "自拍偷拍"},
            {"type_id": "57", "type_name": "探花约炮"},
            {"type_id": "56", "type_name": "同性恋"},
            {"type_id": "55", "type_name": "网曝流出"},
            {"type_id": "59", "type_name": "SM调教(二)"},
            {"type_id": "58", "type_name": "人妻约炮"},
            {"type_id": "60", "type_name": "制服诱惑(二)"},
            {"type_id": "61", "type_name": "麻豆视频"},
            {"type_id": "51", "type_name": "欧美精品"},
            {"type_id": "63", "type_name": "明星换脸(二)"},
            {"type_id": "67", "type_name": "自拍偷拍(三)"},
            {"type_id": "65", "type_name": "传媒视频"},
            {"type_id": "73", "type_name": "网爆黑料(三)"},
            {"type_id": "75", "type_name": "调教视频"},
            {"type_id": "74", "type_name": "moss极品"},
            {"type_id": "70", "type_name": "女同性恋(三)"},
            {"type_id": "71", "type_name": "男同性恋"},
            {"type_id": "69", "type_name": "动漫出品"},
            {"type_id": "68", "type_name": "欧美高清"},
            {"type_id": "66", "type_name": "探花做爱"},
            {"type_id": "76", "type_name": "AI换脸"},
            {"type_id": "64", "type_name": "主播直播"},
        ]
        return self._class_cache

    # ---------- 视频列表解析 ----------
    def _parse_videos(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        for li in soup.select('ul.thumbnail-group li'):
            a = li.find('a', class_='thumbnail')
            if not a:
                continue
            href = a.get('href')
            m = re.search(r'/vod/detail/id/(\d+)\.html', href)
            if not m:
                continue
            vid = m.group(1)

            # 标题
            title_el = li.find('h5')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                title = vid

            # 图片
            img = a.find('img')
            pic = ''
            if img:
                pic = img.get('data-original') or img.get('src') or ''
                if pic and 'loading.svg' not in pic:
                    pic = self._fix_pic(pic)

            # 备注（分类+日期）
            remark = ''
            p = li.find('p', class_='vodtitle')
            if p:
                remark = p.get_text(strip=True)

            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark
            })
        return videos

    # ---------- 分页页码 ----------
    def _get_pagecount(self, html, cur):
        soup = BeautifulSoup(html, 'html.parser')
        # 提取总页数，如 "当前页数1/177页"
        match = re.search(r'当前页数(\d+)/(\d+)页', html)
        if match:
            return int(match.group(2))
        # 查找尾页链接
        last_link = soup.find('a', string='尾页')
        if last_link:
            href = last_link.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                return int(m.group(1))
        # 如果当前页有视频，返回 cur+1 试探
        if len(soup.select('ul.thumbnail-group li')) > 0:
            return cur + 1
        return cur

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=False):
        classes = self._get_classes()
        # 默认显示第一个分类（网曝黑料）
        html = self._fetch(self.host + self.base_path + "/index.php/vod/type/id/94.html")
        videos = self._parse_videos(html) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + self.base_path + "/index.php/vod/type/id/94.html")
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
        url = f"{self.host}{self.base_path}/index.php/vod/detail/id/{vid}.html"
        html = self._fetch(url)
        if not html:
            return {'list': []}
        soup = BeautifulSoup(html, 'html.parser')

        # 标题
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

        # 图片
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

        # 简介
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

        # 2. 其他变量
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