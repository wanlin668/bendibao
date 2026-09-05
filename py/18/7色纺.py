# -*- coding: utf-8 -*-
"""
站点: 7色坊 (https://q7r8s9t0.rmxjj75.sbs/rm/)
功能: 精简分类 + 翻页修复 + 免嗅播放 + 搜索 + 终极图片提取
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
        return "7色坊"

    def init(self, extend=""):
        self.host = "https://q7r8s9t0.rmxjj75.sbs"
        self.base_path = "/rm"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + self.base_path + '/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._classes_cache = None
        # 调试开关：设为 True 可在控制台打印提取信息
        self.debug = False

    def _fetch(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                resp.encoding = 'utf-8'
                return resp.text
            return ''
        except Exception:
            return ''

    # ========== 统一图片URL修复 ==========
    def _fix_pic_url(self, pic, base_url=None):
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith('data:image'):
            return pic
        if pic.startswith('http://') or pic.startswith('https://'):
            return pic
        if pic.startswith('//'):
            return 'https:' + pic
        if base_url is None:
            base_url = self.host + self.base_path + '/'
        if pic.startswith('/'):
            return self.host + pic
        return urljoin(base_url, pic)

    # ========== 辅助：从img标签提取src（支持多种属性） ==========
    def _extract_img_src(self, img):
        for attr in ['data-original', 'data-src', 'data-lazy', 'src', 'data-srcset']:
            val = img.get(attr)
            if val:
                if attr == 'data-srcset':
                    # 取第一个URL（可能含尺寸描述）
                    val = val.split(',')[0].strip().split(' ')[0]
                return val
        return ''

    # ========== 分类动态获取 ==========
    def _get_all_classes(self):
        if self._classes_cache is not None:
            return self._classes_cache
        classes = []
        html = self._fetch(self.host + self.base_path + '/')
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=re.compile(r'/rm/index\.php/vod/type/id/\d+\.html')):
                href = a.get('href')
                m = re.search(r'/id/(\d+)\.html', href)
                if m:
                    type_id = m.group(1)
                    type_name = a.get_text(strip=True)
                    if type_name and type_id:
                        classes.append({'type_id': type_id, 'type_name': type_name})
        if not classes:
            classes = [
                {'type_id': '37', 'type_name': '抖阴视频'},
                {'type_id': '39', 'type_name': '网曝黑料'},
                {'type_id': '34', 'type_name': '国产主播'},
                {'type_id': '36', 'type_name': '明星换脸'},
                {'type_id': '28', 'type_name': '国产传媒'},
                {'type_id': '26', 'type_name': '国产视频'},
                {'type_id': '80', 'type_name': '网红主播'},
                {'type_id': '121', 'type_name': 'OnlyFans'},
                {'type_id': '81', 'type_name': '国产剧情'},
                {'type_id': '82', 'type_name': '国产自拍'},
                {'type_id': '83', 'type_name': '国产探花'},
                {'type_id': '84', 'type_name': '网曝吃瓜'},
                {'type_id': '111', 'type_name': 'AV解说'},
                {'type_id': '112', 'type_name': '三级伦理'},
            ]
        self._classes_cache = classes
        return classes

    # ========== 终极视频列表解析（图片提取强化） ==========
    def _parse_video_list(self, html, page_url=None):
        soup = BeautifulSoup(html, 'html.parser')
        videos = []

        # 查找所有视频链接
        links = soup.find_all('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
        if not links:
            # 兜底：用常见容器选择器
            for sel in ['li.vod-item', 'div.vod-item', 'li.item', 'div.item', '.video-item', '.movie-item']:
                items = soup.select(sel)
                for item in items:
                    a = item.find('a', href=re.compile(r'/vod/detail/id/\d+\.html'))
                    if a:
                        links.append(a)
                if links:
                    break

        for a in links:
            href = a.get('href')
            vid_match = re.search(r'/id/(\d+)\.html', href)
            if not vid_match:
                continue
            vod_id = vid_match.group(1)

            # 标题
            title = a.get('title') or a.get_text(strip=True)
            if not title:
                parent = a.parent
                if parent:
                    title_el = parent.find('h3') or parent.find('div', class_='title')
                    if title_el:
                        title = title_el.get_text(strip=True)

            # ---- 图片提取（超强穷举） ----
            pic = ''
            # 1) 从 a 内部 img
            img = a.find('img')
            if img:
                pic = self._extract_img_src(img)

            # 2) 从 a 的祖先中找 img（包括父、祖父等）
            if not pic:
                for ancestor in a.parents:
                    img = ancestor.find('img')
                    if img:
                        pic = self._extract_img_src(img)
                        break

            # 3) 从 a 或祖先的 style="background-image:url(...)" 提取
            if not pic:
                for elem in [a] + list(a.parents):
                    style = elem.get('style', '')
                    bg = re.search(r'background(?:-image)?\s*:\s*url\([\'"]?([^\)\'"]+)[\'"]?\)', style)
                    if bg:
                        pic = bg.group(1)
                        break

            # 4) 从兄弟元素找 img（如果图片在a外部）
            if not pic:
                parent = a.parent
                if parent:
                    siblings = parent.find_all('img')
                    for img in siblings:
                        if img.parent != a:  # 避免重复
                            pic = self._extract_img_src(img)
                            break

            # 补全图片 URL
            if pic:
                base = page_url if page_url else (self.host + self.base_path + '/')
                pic = self._fix_pic_url(pic, base_url=base)

            # 备注（时长等）
            remark = ''
            time_span = a.find('span', class_='time') or a.find('span', class_='remarks')
            if not time_span:
                parent = a.parent
                if parent:
                    time_span = parent.find('span', class_='time') or parent.find('span', class_='remarks')
            if time_span:
                remark = time_span.get_text(strip=True)

            if title:
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark
                })

        if self.debug:
            print(f"[DEBUG] 共提取 {len(videos)} 个视频")
            if videos:
                print(f"[DEBUG] 示例图片URL: {videos[0]['vod_pic']}")
        return videos

    def _get_pagecount(self, html, current_page=1):
        soup = BeautifulSoup(html, 'html.parser')
        max_page = 1
        last = soup.find('a', string=re.compile(r'尾页|末页|最后'))
        if last:
            href = last.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        for a in soup.select('.page a, .pagination a, .pages a'):
            text = a.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
            href = a.get('href', '')
            m = re.search(r'/page/(\d+)\.html', href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        next_link = soup.find('a', string=re.compile(r'下一页|Next|»'))
        if next_link and max_page <= current_page:
            max_page = current_page + 1
        return max_page if max_page > 1 else 1

    # ========== 首页 ==========
    def homeContent(self, filter=False):
        classes = self._get_all_classes()
        html = self._fetch(self.host + self.base_path + '/')
        videos = self._parse_video_list(html, page_url=self.host + self.base_path + '/') if html else []
        return {'class': classes, 'list': videos[:30], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + self.base_path + '/')
        if not html:
            return {'list': []}
        return {'list': self._parse_video_list(html, page_url=self.host + self.base_path + '/')[:20]}

    # ========== 分类 ==========
    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1
        url = f"{self.host}{self.base_path}/index.php/vod/type/id/{tid}/page/{page}.html"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page, 'pagecount': 1}
        videos = self._parse_video_list(html, page_url=url)
        if not videos and page > 1:
            return {'list': [], 'page': page, 'pagecount': page}
        pagecount = self._get_pagecount(html, page)
        if not videos and pagecount > page:
            pagecount = page
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * (len(videos) or 20)
        }

    # ========== 详情 ==========
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}{self.base_path}/index.php/vod/detail/id/{vid}.html"
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
            if img.name == 'meta':
                pic = img.get('content', '')
            else:
                for attr in ['src', 'data-original', 'data-src']:
                    val = img.get(attr)
                    if val:
                        pic = val
                        break
        if pic:
            pic = self._fix_pic_url(pic, base_url=url)

        content = ''
        desc = soup.find('div', class_='vod_content') or soup.find('meta', attrs={'name': 'description'})
        if desc:
            content = desc.get_text(strip=True) if hasattr(desc, 'get_text') else desc.get('content', '')

        # 提取播放列表
        play_from = []
        play_url = []
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
        if not play_from:
            play_from.append('默认线路')
            play_url.append(f"第1集${self.host}{self.base_path}/index.php/vod/play/id/{vid}/sid/1/nid/1.html")

        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }
        return {'list': [vod]}

    # ========== 搜索 ==========
    def searchContent(self, key, quick=False, pg='1'):
        page = int(pg) if pg else 1
        encoded_key = quote(key)
        url = f"{self.host}{self.base_path}/index.php/vod/search/wd/{encoded_key}/page/{page}.html"
        html = self._fetch(url)
        if not html:
            return {'list': [], 'page': page}
        videos = self._parse_video_list(html, page_url=url)
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

    # ========== 免嗅播放 ==========
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http') and ('.m3u8' in id or '.mp4' in id):
            return {'parse': 0, 'url': id, 'header': self.headers}
        play_url = id if id.startswith('http') else urljoin(self.host + self.base_path + '/', id)
        html = self._fetch(play_url)
        if not html:
            return {'parse': 1, 'url': play_url}
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
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            return {'parse': 1, 'url': iframe.group(1), 'header': self.headers}
        direct = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4)[^\s"\'<>]*)', html)
        if direct:
            return {'parse': 0, 'url': direct.group(1), 'header': self.headers}
        var_match = re.search(r'var\s+(?:url|video_url|playurl)\s*=\s*["\']([^"\']+)["\']', html)
        if var_match:
            return {'parse': 0, 'url': var_match.group(1), 'header': self.headers}
        return {'parse': 1, 'url': play_url}

    # ========== 辅助 ==========
    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None