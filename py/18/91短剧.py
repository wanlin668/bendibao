# coding=utf-8
"""
目标站: 91成人短剧 (https://91crdj.com)
模板: 自建站 (HTML + JSON)
功能: 分类浏览、详情解析、搜索、m3u8播放
"""
import re
import sys
import json
import urllib.parse
import time
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://91crdj.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.categories = [
            {"type_id": "duanju", "type_name": "成人短剧"},
            {"type_id": "manju", "type_name": "成人漫剧"},
            {"type_id": "zhenrenju", "type_name": "真人剧"},
            {"type_id": "shipin", "type_name": "成人视频"},
        ]
        self.filters = {}

    def getName(self):
        return "91成人短剧"

    def _safe_fetch(self, url, headers=None, max_retry=3):
        if headers is None:
            headers = self.headers
        for i in range(max_retry):
            try:
                resp = self.fetch(url, headers=headers)
                if resp:
                    return resp
            except Exception:
                time.sleep(0.5)
        return None

    def _fix_url(self, url):
        if not url:
            return ''
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.site_url + url
        return self.site_url + '/' + url

    def _parse_video_list(self, soup):
        video_list = []
        seen = set()
        for card in soup.select('a.card'):
            href = card.get('href', '')
            m = re.search(r'/(duanju|manju|zhenrenju|shipin)/(\d+-[^/]+)/', href)
            if not m:
                continue
            vod_id = m.group(1) + '/' + m.group(2)
            if vod_id in seen:
                continue
            seen.add(vod_id)
            title = card.get('data-track-item-name', '') or ''
            if not title:
                h3 = card.select_one('h3')
                if h3:
                    title = h3.get_text(strip=True)
            if not title:
                continue
            pic = ''
            img = card.select_one('img.p-img')
            if img:
                pic = self._fix_url(img.get('src', ''))
            remark = ''
            eps_flag = card.select_one('.eps-flag')
            if eps_flag:
                remark = eps_flag.get_text(strip=True)
            video_list.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return video_list

    def _extract_page_info(self, soup):
        pagecount = 1
        pager = soup.select_one('nav.pager')
        if pager:
            pages_attr = pager.get('data-pages', '')
            if pages_attr:
                try:
                    pagecount = int(pages_attr)
                except ValueError:
                    pass
            for a in pager.select('a.pg'):
                href = a.get('href', '')
                m = re.search(r'/page/(\d+)/', href)
                if m:
                    pagecount = max(pagecount, int(m.group(1)))
        total = 24 * pagecount
        return pagecount, total

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self._safe_fetch(url)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            video_list = self._parse_video_list(soup)
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page <= 1:
            url = f"{self.site_url}/{tid}/"
        else:
            url = f"{self.site_url}/{tid}/page/{page}/"
        resp = self._safe_fetch(url)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(soup)
        pagecount, total = self._extract_page_info(soup)
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": total
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/{vod_id}/"
        resp = self._safe_fetch(url)
        if not resp:
            return {"list": []}
        soup = BeautifulSoup(resp.text, 'html.parser')

        vod_name = ''
        title_tag = soup.select_one('h1.detail-title')
        if title_tag:
            vod_name = title_tag.get_text(strip=True)
        if not vod_name:
            title_tag = soup.select_one('title')
            if title_tag:
                vod_name = title_tag.get_text().split('-')[0].strip()

        vod_pic = ''
        poster_img = soup.select_one('.d-poster img')
        if poster_img:
            vod_pic = self._fix_url(poster_img.get('src', ''))
        if not vod_pic:
            og_img = soup.select_one('meta[property="og:image"]')
            if og_img:
                vod_pic = og_img.get('content', '')

        vod_content = ''
        vi_text = soup.select_one('#viBody')
        if vi_text:
            vod_content = vi_text.get_text(' ', strip=True)

        vod_score = ''
        rv = soup.select_one('.rv')
        if rv:
            vod_score = rv.get_text(strip=True)

        vod_area = vod_year = ''
        vod_remarks = ''
        work_meta = soup.select_one('.work-meta')
        if work_meta:
            for div in work_meta.select('div'):
                dt = div.select_one('dt')
                dd = div.select_one('dd')
                if not dt or not dd:
                    continue
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key == '分类':
                    vod_area = val
                elif key == '集数':
                    vod_remarks = val
                elif key == '发布':
                    vod_year = val

        tag_list = []
        tags_div = soup.select_one('.d-tags')
        if tags_div:
            for el in tags_div.select('a, span'):
                t = el.get_text(strip=True)
                if t:
                    tag_list.append(t)
        vod_actor = ','.join(tag_list)

        play_from_list = []
        play_url_list = []
        ep_links = soup.select('.ep-grid a[href]')
        if ep_links:
            ep_items = []
            for ep in ep_links:
                href = ep.get('href', '')
                if not href or 'javascript' in href:
                    continue
                ep_num = ep.get_text(strip=True)
                if not ep_num:
                    ep_num = ep.get('data-ep', '1')
                play_url = self._fix_url(href)
                ep_items.append('第' + ep_num + '集$' + play_url)
            if ep_items:
                play_from_list.append('默认线路')
                play_url_list.append('#'.join(ep_items))

        if not play_url_list:
            play_btn = soup.select_one('#btnPlay')
            if play_btn:
                href = play_btn.get('href', '')
                if href:
                    play_url = self._fix_url(href)
                    play_from_list.append('默认线路')
                    play_url_list.append('播放$' + play_url)

        if not play_url_list:
            play_from_list.append('默认线路')
            play_url_list.append('播放$' + url)

        vod_play_from = '$$$'.join(play_from_list)
        vod_play_url = '$$$'.join(play_url_list)

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": '',
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_score": vod_score,
            "vod_remarks": vod_remarks,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search/?keyword={encoded_key}"
        resp = self._safe_fetch(url)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(soup)
        pagecount, _ = self._extract_page_info(soup)
        if not pagecount:
            pagecount = 1
        return {"list": video_list, "page": page, "pagecount": pagecount}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('http'):
            play_url = id
        elif id.startswith('/'):
            play_url = self.site_url + id
        else:
            play_url = self.site_url + '/' + id

        resp = self._safe_fetch(play_url)
        if not resp:
            return {"parse": 1, "url": play_url, "header": self.headers}

        html = resp.text

        m = re.search(r'<script\s+id="playInitialData"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                src = data.get('current', {}).get('src', '')
                if src and '.m3u8' in src:
                    return {"parse": 0, "url": src, "header": self.headers}
            except Exception:
                pass

        m2 = re.search(r'"contentUrl"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"', html)
        if m2:
            video_url = m2.group(1).replace('\\u0026', '&').replace('\\/', '/')
            return {"parse": 0, "url": video_url, "header": self.headers}

        m3 = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
        if m3:
            video_url = m3.group(0).replace('\\u0026', '&').replace('\\/', '/')
            return {"parse": 0, "url": video_url, "header": self.headers}

        return {"parse": 1, "url": play_url, "header": self.headers}
