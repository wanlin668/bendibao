# -*- coding: utf-8 -*-
"""
站点: 色妹妹AV (https://1xu7a6dx.8nndyhi.sbs)
功能: 精简分类 + 翻页修复 + 免嗅播放 + 搜索
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

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
        return "色妹妹AV"

    def init(self, extend=""):
        self.host = "https://1xu7a6dx.8nndyhi.sbs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + '/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._classes_cache = None

    def _fetch(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                resp.encoding = 'utf-8'
                return resp.text
            return ''
        except Exception:
            return ''

    # ----- 分类只保留四个大项 -----
    def _get_all_classes(self):
        if self._classes_cache is not None:
            return self._classes_cache
        classes = [
            {'type_id': '1', 'type_name': '国产精品'},
            {'type_id': '13', 'type_name': '美女主播'},
            {'type_id': '11', 'type_name': '国产传媒'},
            {'type_id': '12', 'type_name': '国产情色'},
            {'type_id': '16', 'type_name': '抖阴视频'},
            {'type_id': '15', 'type_name': 'AI换脸'},
            {'type_id': '17', 'type_name': '网曝门'},
            {'type_id': '18', 'type_name': '三级伦理'},
            {'type_id': '2', 'type_name': '日韩欧美'},
            {'type_id': '23', 'type_name': '亚洲有码'},
            {'type_id': '24', 'type_name': '亚洲无码'},
            {'type_id': '22', 'type_name': '女优明星'},
            {'type_id': '21', 'type_name': '中文字幕'},
            {'type_id': '25', 'type_name': '制服丝袜'},
            {'type_id': '27', 'type_name': '强奸乱伦'},
            {'type_id': '28', 'type_name': '综合其他'},
        ]
        self._classes_cache = classes
        return classes

    # ==================== 解析列表 ====================
    def _parse_video_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        items = soup.select('li.vod-item, div.vod-item, li.item, div.item, a[href*="/vod/detail/id/"]')
        if not items:
            items = soup.find_all('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
        for item in items:
            if item.name == 'a' and item.get('href'):
                a = item
            else:
                a = item.find('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
                if not a:
                    continue
            href = a.get('href')
            vid_match = re.search(r'/id/(\d+)\.html', href)
            if not vid_match:
                continue
            vod_id = vid_match.group(1)
            title = a.get('title') or a.get_text(strip=True)
            if not title:
                title_el = item.find('h3') or item.find('div', class_='title')
                if title_el:
                    title = title_el.get_text(strip=True)
            img = item.find('img')
            pic = ''
            if img:
                pic = img.get('data-original') or img.get('data-src') or img.get('src') or ''
            if pic and not pic.startswith('http'):
                pic = urljoin(self.host, pic)
            remark = ''
            time_span = item.find('span', class_='time') or item.find('span', class_='remarks')
            if time_span:
                remark = time_span.get_text(strip=True)
            if title:
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark
                })
        return videos

    def _get_pagecount(self, html, current_page=1):
        soup = BeautifulSoup(html, 'html.parser')
        max_page = 1
        # 1. 优先从“尾页”提取
        last = soup.find('a', string=re.compile(r'尾页|末页|最后'))
        if last:
            href = last.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        # 2. 从数字页码提取
        for a in soup.select('.page a, .pagination a, .pages a'):
            text = a.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
            href = a.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        # 3. 如果当前页有“下一页”链接，但无尾页，则至少有两页（加1）
        next_link = soup.find('a', string=re.compile(r'下一页|Next|»'))
        if next_link and max_page <= current_page:
            max_page = current_page + 1
        return max_page if max_page > 1 else 1

    # ==================== 首页 ====================
    def homeContent(self, filter=False):
        classes = self._get_all_classes()
        html = self._fetch(self.host + '/')
        videos = self._parse_video_list(html) if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + '/')
        if not html:
            return {'list': []}
        return {'list': self._parse_video_list(html)[:20]}

    # ==================== 分类（翻页修复） ====================
    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        url = f"{self.host}/index.php/vod/type/id/{tid}/page/{page}.html"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page, 'pagecount': 1}
        videos = self._parse_video_list(html)
        # 如果列表为空且page>1，说明没有更多页，pagecount设为page
        if not videos and page > 1:
            return {'list': [], 'page': page, 'pagecount': page}
        pagecount = self._get_pagecount(html, page)
        # 如果列表为空但pagecount>page，可能总页数判断有误，修正为page
        if not videos and pagecount > page:
            pagecount = page
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * (len(videos) or 20)
        }

    # ==================== 详情（多线路多集） ====================
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}/index.php/vod/detail/id/{vid}.html"
        html = self._fetch(url)
        if not html:
            return {'list': []}
        soup = BeautifulSoup(html, 'html.parser')

        title = ''
        title_tag = soup.find('h1') or soup.find('meta', property='og:title')
        if title_tag:
            title = title_tag.get_text(strip=True) if hasattr(title_tag, 'get_text') else title_tag.get('content', '')
        if not title:
            title = vid

        pic = ''
        img = soup.find('img', class_='vod_img') or soup.find('meta', property='og:image')
        if img:
            pic = img.get('src') or img.get('data-original') or img.get('content', '')
        if pic and not pic.startswith('http'):
            pic = urljoin(self.host, pic)

        content = ''
        desc = soup.find('div', class_='vod_content') or soup.find('meta', attrs={'name': 'description'})
        if desc:
            content = desc.get_text(strip=True) if hasattr(desc, 'get_text') else desc.get('content', '')

        # 提取播放列表
        play_from = []
        play_url = []

        # 从页面变量提取
        from_match = re.search(r'vod_play_from\s*=\s*"([^"]+)"', html)
        url_match = re.search(r'vod_play_url\s*=\s*"([^"]+)"', html)
        if from_match and url_match:
            from_str = from_match.group(1)
            url_str = url_match.group(1)
            from_list = from_str.split('$$$') if '$$$' in from_str else [from_str]
            url_list = url_str.split('$$$') if '$$$' in url_str else [url_str]
            for i, line_name in enumerate(from_list):
                if i < len(url_list) and url_list[i]:
                    episodes = url_list[i].split('#') if '#' in url_list[i] else [url_list[i]]
                    ep_list = []
                    for ep in episodes:
                        if '$' in ep:
                            ep_name, ep_url = ep.split('$', 1)
                            ep_list.append(f"{ep_name}${ep_url}")
                        else:
                            ep_list.append(f"第{len(ep_list)+1}集${ep}")
                    if ep_list:
                        play_from.append(line_name)
                        play_url.append('#'.join(ep_list))

        # 从 player_aaaa 提取
        if not play_from:
            for script in soup.find_all('script'):
                if 'player_aaaa' in script.text:
                    match = re.search(r'player_aaaa\s*=\s*(\{.*?\});', script.text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            vod_data = data.get('vod_data', {})
                            if vod_data:
                                from_str = vod_data.get('vod_play_from', '')
                                url_str = vod_data.get('vod_play_url', '')
                                if from_str and url_str:
                                    from_list = from_str.split('$$$') if '$$$' in from_str else [from_str]
                                    url_list = url_str.split('$$$') if '$$$' in url_str else [url_str]
                                    for i, line_name in enumerate(from_list):
                                        if i < len(url_list) and url_list[i]:
                                            episodes = url_list[i].split('#') if '#' in url_list[i] else [url_list[i]]
                                            ep_list = []
                                            for ep in episodes:
                                                if '$' in ep:
                                                    ep_name, ep_url = ep.split('$', 1)
                                                    ep_list.append(f"{ep_name}${ep_url}")
                                                else:
                                                    ep_list.append(f"第{len(ep_list)+1}集${ep}")
                                            if ep_list:
                                                play_from.append(line_name)
                                                play_url.append('#'.join(ep_list))
                        except:
                            pass

        # 保底
        if not play_from:
            play_from.append('默认线路')
            play_url.append(f"第1集${self.host}/index.php/vod/play/id/{vid}/sid/1/nid/1.html")

        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }
        return {'list': [vod]}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        encoded_key = quote(key)
        url = f"{self.host}/index.php/vod/search/wd/{encoded_key}/page/{page}.html"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page}
        videos = self._parse_video_list(html)
        pagecount = self._get_pagecount(html, page)
        if not videos and page > 1:
            pagecount = page
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * (len(videos) or 20)
        }

    # ==================== 免嗅播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {'parse': 0, 'url': id, 'header': self.headers}

        play_url = id if id.startswith('http') else urljoin(self.host, id)
        html = self._fetch(play_url)
        if not html:
            return {'parse': 1, 'url': play_url}

        # 提取 player_aaaa
        match = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                real_url = data.get('url', '')
                if real_url:
                    encrypt = data.get('encrypt', 0)
                    if encrypt == 1:
                        import urllib.parse
                        real_url = urllib.parse.unquote(real_url)
                    elif encrypt == 2:
                        import base64
                        real_url = base64.b64decode(real_url).decode('utf-8')
                    return {'parse': 0, 'url': real_url, 'header': self.headers}
            except:
                pass

        # 提取 iframe
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            return {'parse': 1, 'url': iframe.group(1), 'header': self.headers}

        # 直接匹配 m3u8/mp4
        direct = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if direct:
            return {'parse': 0, 'url': direct.group(1), 'header': self.headers}

        # 常见变量
        var_match = re.search(r'var\s+(?:url|video_url|playurl)\s*=\s*["\']([^"\']+)["\']', html)
        if var_match:
            return {'parse': 0, 'url': var_match.group(1), 'header': self.headers}

        return {'parse': 1, 'url': play_url}

    # ==================== 辅助 ====================
    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None