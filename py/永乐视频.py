# coding=utf-8
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

    def getName(self):
        return "永乐视频"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; M2102J2SC Build/UKQ1.240624.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.59v.net/',
        })

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    home_url = "https://www.59v.net"

    classes = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "剧集"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
    ]

    filters = {
        "1": [{"key": "sub", "name": "类型", "value": [
            {"n": "全部", "v": ""},       {"n": "动作片", "v": "6"},
            {"n": "喜剧片", "v": "7"},    {"n": "爱情片", "v": "8"},
            {"n": "科幻片", "v": "9"},    {"n": "恐怖片", "v": "10"},
            {"n": "剧情片", "v": "11"},   {"n": "战争片", "v": "12"},
            {"n": "动漫电影", "v": "26"},
        ]}],
        "2": [{"key": "sub", "name": "类型", "value": [
            {"n": "全部", "v": ""},      {"n": "国产剧", "v": "13"},
            {"n": "港台剧", "v": "14"},  {"n": "韩国剧", "v": "15"},
            {"n": "欧美剧", "v": "16"},  {"n": "日本剧", "v": "17"},
            {"n": "泰国剧", "v": "27"},
        ]}],
        "3": [{"key": "sub", "name": "类型", "value": [
            {"n": "全部", "v": ""},       {"n": "国内综艺", "v": "18"},
            {"n": "港台综艺", "v": "19"}, {"n": "日韩综艺", "v": "20"},
            {"n": "欧美综艺", "v": "21"},
        ]}],
        "4": [{"key": "sub", "name": "类型", "value": [
            {"n": "全部", "v": ""},       {"n": "国产动漫", "v": "22"},
            {"n": "欧美动漫", "v": "23"}, {"n": "日韩动漫", "v": "24"},
            {"n": "港台动漫", "v": "25"},
        ]}],
    }

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        videos = []
        try:
            resp = self.session.get(self.home_url, timeout=10)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            for item in soup.select('.module-item'):
                a = item if item.name == 'a' else item.select_one('a')
                if not a:
                    continue
                href = a.get('href', '')
                if not href.startswith('/voddetail/'):
                    continue
                title = a.get('title', '') or ''
                if not title:
                    t = a.select_one('.module-poster-item-title')
                    title = t.text.strip() if t else ''
                img = a.select_one('img')
                pic = (img.get('data-original') or img.get('src', '')) if img else ''
                note = a.select_one('.module-item-note')
                videos.append({
                    "vod_id":      href,
                    "vod_name":    title,
                    "vod_pic":     urljoin(self.home_url, pic),
                    "vod_remarks": note.text.strip() if note else '',
                })
        except Exception:
            pass
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        page = int(pg) if str(pg).isdigit() else 1
        sub = extend.get("sub", "") if isinstance(extend, dict) else ""
        cid = sub if sub else tid
        url = f"{self.home_url}/vodshow/{cid}--------{page}---/"
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            for item in soup.select('.module-item'):
                a = item if item.name == 'a' else item.select_one('a')
                if not a:
                    continue
                href = a.get('href', '')
                if not href.startswith('/voddetail/'):
                    continue
                title = a.get('title', '') or ''
                img = a.select_one('img')
                pic = (img.get('data-original') or img.get('src', '')) if img else ''
                note = a.select_one('.module-item-note')
                videos.append({
                    "vod_id":      href,
                    "vod_name":    title,
                    "vod_pic":     urljoin(self.home_url, pic),
                    "vod_remarks": note.text.strip() if note else '',
                })
        except Exception:
            pass
        return {
            'list':      videos,
            'page':      page,
            'pagecount': 999 if len(videos) >= 20 else page,
            'limit':     40,
            'total':     999999,
        }

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        try:
            vid = ids[0]
            url = urljoin(self.home_url, vid)
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            vod = {"vod_id": vid, "vod_name": "未知"}

            h1 = soup.select_one('.module-info-heading h1') or soup.select_one('.page-title')
            if h1:
                vod['vod_name'] = h1.text.strip()

            img = soup.select_one('.module-info-poster img') or soup.select_one('.module-item-pic img')
            if img:
                vod['vod_pic'] = urljoin(self.home_url, img.get('data-original') or img.get('src', ''))

            intro = soup.select_one('.module-info-introduction-content p')
            if intro:
                vod['vod_content'] = intro.text.strip()

            for item in soup.select('.module-info-item'):
                text = item.text
                if '导演：' in text:
                    vod['vod_director'] = text.replace('导演：', '').strip()
                elif '主演：' in text:
                    vod['vod_actor'] = text.replace('主演：', '').strip()
                elif '上映：' in text:
                    vod['vod_year'] = text.replace('上映：', '').strip()
                elif '备注：' in text:
                    vod['vod_remarks'] = text.replace('备注：', '').strip()

            play_sources = []
            tab_box = soup.select_one('.module-tab-items-box')
            tabs = tab_box.select('.tab-item') if tab_box else soup.select('.module-tab-item.tab-item')
            for tab in tabs:
                span = tab.select_one('span')
                name = span.text.strip() if span else re.sub(r'\d+$', '', tab.text).strip()
                if name and name not in play_sources:
                    play_sources.append(name)

            play_lists = []
            for list_div in soup.select('.module-play-list-content'):
                eps = []
                for link in list_div.select('a.module-play-list-link'):
                    span = link.select_one('span')
                    ep_name = span.text.strip() if span else link.text.strip()
                    ep_url = link.get('href', '')
                    if ep_url:
                        eps.append(f"{ep_name}${ep_url}")
                if eps:
                    play_lists.append("#".join(eps))

            if play_sources and play_lists:
                n = min(len(play_sources), len(play_lists))
                vod['vod_play_from'] = "$$$".join(play_sources[:n])
                vod['vod_play_url']  = "$$$".join(play_lists[:n])

            return {'list': [vod]}
        except Exception:
            pass
        return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            encoded = quote(key)
            if str(pg) == "1":
                url = f"{self.home_url}/vodsearch/{encoded}-------------/"
            else:
                url = f"{self.home_url}/vodsearch/{encoded}----------{pg}---/"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            videos = []
            items = soup.select('.module-card-item') or soup.select('.module-item')
            for item in items:
                try:
                    a = (item.select_one('.module-card-item-poster') or
                         item.select_one('.module-card-item-title a') or
                         item.select_one('a'))
                    if not a:
                        continue
                    href = a.get('href', '')
                    if not href.startswith('/voddetail/'):
                        continue
                    title_tag = (item.select_one('.module-card-item-title strong') or
                                 item.select_one('.module-card-item-title a'))
                    title = title_tag.text.strip() if title_tag else ''
                    img = item.select_one('img')
                    if not title and img:
                        title = img.get('alt', '')
                    pic = (img.get('data-original') or img.get('src', '')) if img else ''
                    note = item.select_one('.module-item-note')
                    videos.append({
                        "vod_id":      href,
                        "vod_name":    title,
                        "vod_pic":     urljoin(self.home_url, pic),
                        "vod_remarks": note.text.strip() if note else '',
                    })
                except Exception:
                    pass
            return {'list': videos}
        except Exception:
            pass
        return {'list': []}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        try:
            url = urljoin(self.home_url, id)
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            match = re.search(r'var\s+player_aaaa\s*=\s*({.+?})</script>', resp.text)
            if match:
                player_data = json.loads(match.group(1))
                real_url = player_data.get('url', '')
                if real_url.endswith('.m3u8') or real_url.endswith('.mp4'):
                    return {'parse': 0, 'url': real_url, 'header': ''}
            return {'parse': 1, 'url': url}
        except Exception:
            pass
        return {'parse': 1, 'url': id}

    def localProxy(self, params):
        return None