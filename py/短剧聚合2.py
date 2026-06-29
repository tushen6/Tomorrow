# -*- coding: utf-8 -*-
# 短剧聚合 Spider - 支持七猫、星芽、西饭、围观、河马
import re
import json
import base64
import hashlib
import time
import random
import requests
from urllib.parse import quote, unquote
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.keys = 'd3dGiJc651gSQ8w1'
        self.char_map = {
            '+': 'P', '/': 'X', '0': 'M', '1': 'U', '2': 'l', '3': 'E', '4': 'r', '5': 'Y', '6': 'W', '7': 'b', '8': 'd', '9': 'J',
            'A': '9', 'B': 's', 'C': 'a', 'D': 'I', 'E': '0', 'F': 'o', 'G': 'y', 'H': '_', 'I': 'H', 'J': 'G', 'K': 'i', 'L': 't',
            'M': 'g', 'N': 'N', 'O': 'A', 'P': '8', 'Q': 'F', 'R': 'k', 'S': '3', 'T': 'h', 'U': 'f', 'V': 'R', 'W': 'q', 'X': 'C',
            'Y': '4', 'Z': 'p', 'a': 'm', 'b': 'B', 'c': 'O', 'd': 'u', 'e': 'c', 'f': '6', 'g': 'K', 'h': 'x', 'i': '5', 'j': 'T',
            'k': '-', 'l': '2', 'm': 'z', 'n': 'S', 'o': 'Z', 'p': '1', 'q': 'V', 'r': 'v', 's': 'j', 't': 'Q', 'u': '7', 'v': 'D',
            'w': 'w', 'x': 'n', 'y': 'L', 'z': 'e'
        }
        self.headers_default = {
            'User-Agent': 'okhttp/3.12.11',
            'content-type': 'application/json; charset=utf-8'
        }
        self.platform = {
            '星芽': {
                'host': 'https://app.whjzjx.cn',
                'url1': '/cloud/v2/theater/home_page?theater_class_id',
                'url2': '/v2/theater_parent/detail',
                'search': '/v3/search',
                'classes': '/cloud/v2/theater/classes',
                'rankDetail': '/cloud/v1/first_level_ranking/detail',
                'loginUrl': 'https://u.shytkjgs.com/user/v1/account/login'
            },
            '西饭': {
                'host': 'https://xifan-api-cn.youlishipin.com',
                'url1': '/xifan/drama/portalPage',
                'url2': '/xifan/drama/getDuanjuInfo',
                'search': '/xifan/search/getSearchList'
            },
            '七猫': {
                'host': 'https://api-store.qmplaylet.com',
                'url1': '/api/v1/playlet/index',
                'url2': 'https://api-read.qmplaylet.com/player/api/v1/playlet/info',
                'search': '/api/v1/playlet/search'
            },
            '围观': {
                'host': 'https://api.drama.9ddm.com',
                'url1': '/drama/home/shortVideoTags',
                'url2': '/drama/home/shortVideoDetail',
                'search': '/drama/home/search'
            },
            '河马': {
                'host': 'https://www.kuaikaw.cn',
                'search': '/seo/video/6007'
            }
        }
        self.platform_list = [
            {'name': '七猫短剧', 'id': '七猫'},
            {'name': '星芽短剧', 'id': '星芽'},
            {'name': '西饭短剧', 'id': '西饭'},
            {'name': '围观短剧', 'id': '围观'},
            {'name': '河马短剧', 'id': '河马'}
        ]
        self.rule_filter_def = {
            '星芽': {'area': '1', 'class2': '0', 'rank': '1'},
            '西饭': {'area': '都市'},
            '七猫': {'area': '0'},
            '围观': {'area': ''},
            '河马': {'area': '462'}
        }
        self.filter_options = {
            '七猫': [{
                'key': 'area',
                'name': '分类',
                'value': [
                    {'n': '全部', 'v': '0'},
                    {'n': '男频', 'v': '1'},
                    {'n': '新剧', 'v': '3'},
                    {'n': '现代言情', 'v': '21'},
                    {'n': '神豪', 'v': '37'},
                    {'n': '萌宝', 'v': '356'},
                    {'n': '穿越', 'v': '373'},
                    {'n': '战神', 'v': '527'},
                    {'n': '神医', 'v': '1269'},
                    {'n': '古装', 'v': '1272'}
                ]
            }],
            '星芽': [{
                'key': 'area',
                'name': '剧场',
                'value': [
                    {'n': '剧场', 'v': '1'},
                    {'n': '热播短剧', 'v': '2'},
                    {'n': '会员专享', 'v': '8'},
                    {'n': '星选好剧', 'v': '7'},
                    {'n': '新剧', 'v': '3'},
                    {'n': '阳光剧场', 'v': '5'},
                    {'n': '排行榜', 'v': '9'}
                ]
            }, {
                'key': 'class2',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': '0'},
                    {'n': '都市', 'v': '4'},
                    {'n': '逆袭', 'v': '7'},
                    {'n': '古装', 'v': '5'},
                    {'n': '亲情', 'v': '41'},
                    {'n': '现代言情', 'v': '15'},
                    {'n': '重生', 'v': '6'},
                    {'n': '虐恋', 'v': '8'},
                    {'n': '玄幻', 'v': '35'},
                    {'n': '穿越', 'v': '17'},
                    {'n': '脑洞', 'v': '32'},
                    {'n': '甜宠', 'v': '33'},
                    {'n': '古代言情', 'v': '37'},
                    {'n': '战神', 'v': '24'},
                    {'n': '历史', 'v': '40'},
                    {'n': '赘婿', 'v': '26'},
                    {'n': '萌宝', 'v': '9'},
                    {'n': '神医', 'v': '25'}
                ]
            }, {
                'key': 'rank',
                'name': '榜单',
                'value': [
                    {'n': '实时热榜', 'v': '1'},
                    {'n': '热搜榜', 'v': '2'},
                    {'n': '新剧榜', 'v': '3'},
                    {'n': '剧单榜', 'v': '4'},
                    {'n': '口碑榜', 'v': '5'}
                ]
            }],
            '西饭': [{
                'key': 'area',
                'name': '分类',
                'value': [
                    {'n': '都市', 'v': '都市'},
                    {'n': '甜宠', 'v': '甜宠'},
                    {'n': '逆袭', 'v': '逆袭'},
                    {'n': '战神', 'v': '战神'},
                    {'n': '古装', 'v': '古装'},
                    {'n': '穿越', 'v': '穿越'},
                    {'n': '萌宝', 'v': '萌宝'}
                ]
            }],
            '围观': [{
                'key': 'area',
                'name': '分类',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '都市', 'v': '都市'},
                    {'n': '逆袭', 'v': '逆袭'},
                    {'n': '家庭', 'v': '家庭'},
                    {'n': '古装', 'v': '古装'},
                    {'n': '复仇', 'v': '复仇'},
                    {'n': '甜宠', 'v': '甜宠'},
                    {'n': '悬疑', 'v': '悬疑'},
                    {'n': '爱情', 'v': '爱情'},
                    {'n': '重生', 'v': '重生'},
                    {'n': '总裁', 'v': '总裁'},
                    {'n': '穿越', 'v': '穿越'},
                    {'n': '萌宝', 'v': '萌宝'},
                    {'n': '战神', 'v': '战神'},
                    {'n': '职场', 'v': '职场'},
                    {'n': '神豪', 'v': '神豪'},
                    {'n': '神医', 'v': '神医'},
                    {'n': '赘婿', 'v': '赘婿'}
                ]
            }],
            '河马': [{
                'key': 'area',
                'name': '分类',
                'value': [
                    {'n': '甜宠', 'v': '462'},
                    {'n': '古装仙侠', 'v': '1102'},
                    {'n': '现代言情', 'v': '1145'},
                    {'n': '青春', 'v': '1170'},
                    {'n': '豪门恩怨', 'v': '585'},
                    {'n': '逆袭', 'v': '417-464'},
                    {'n': '重生', 'v': '439-465'},
                    {'n': '系统', 'v': '1159'},
                    {'n': '总裁', 'v': '1147'},
                    {'n': '职场商战', 'v': '943'}
                ]
            }]
        }
        # 缓存
        self.qm_header = {'value': None, 'timestamp': 0}
        self.xingya_token = None
        self.xingya_headers = self.headers_default.copy()

    def init(self, extend=""):
        self.extend = extend
        return self

    def getName(self):
        return "短剧聚合"

    def _md5(self, text):
        return hashlib.md5(text.encode()).hexdigest().lower()

    def _base64_encode(self, text):
        return base64.b64encode(text.encode()).decode()

    def _base64_decode(self, text):
        try:
            return base64.b64decode(text).decode()
        except:
            return text

    def _get_qm_params_and_sign(self):
        now = int(time.time() * 1000)
        if self.qm_header['value'] and now - self.qm_header['timestamp'] < 300000:
            return self.qm_header['value']

        session_id = str(now)
        data = {
            "static_score": "0.8",
            "uuid": "00000000-7fc7-08dc-0000-000000000000",
            "device-id": "20250220125449b9b8cac84c2dd3d035c9052a2572f7dd0122edde3cc42a70",
            "sourceuid": "aa7de295aad621a6",
            "refresh-type": "0",
            "model": "22021211RC",
            "client-id": "aa7de295aad621a6",
            "brand": "Redmi",
            "sys-ver": "12",
            "phone-level": "H",
            "wlb-uid": "aa7de295aad621a6",
            "session-id": session_id
        }

        json_str = json.dumps(data, separators=(',', ':'))
        base64_str = self._base64_encode(json_str)
        qm_params = ''

        for char in base64_str:
            qm_params += self.char_map.get(char, char)

        params_str = f"AUTHORIZATION=app-version=10001application-id=com.duoduo.readchannel=unknownis-white=net-env=5platform=androidqm-params={qm_params}reg={self.keys}"
        sign = self._md5(params_str)

        self.qm_header['value'] = {'qmParams': qm_params, 'sign': sign}
        self.qm_header['timestamp'] = now
        return self.qm_header['value']

    def _get_header_x(self):
        qm = self._get_qm_params_and_sign()
        return {
            'net-env': '5',
            'reg': '',
            'channel': 'unknown',
            'is-white': '',
            'platform': 'android',
            'application-id': 'com.duoduo.read',
            'authorization': '',
            'app-version': '10001',
            'user-agent': 'webviewversion/0',
            'qm-params': qm['qmParams'],
            'sign': qm['sign']
        }

    def _ensure_xingya_auth(self):
        if self.xingya_headers.get('authorization'):
            return self.xingya_headers
        try:
            plat = self.platform['星芽']
            res = requests.post(
                plat['loginUrl'],
                headers={'User-Agent': 'okhttp/4.10.0', 'platform': '1', 'Content-Type': 'application/json'},
                json={'device': '24250683a3bdb3f118dff25ba4b1cba1a'},
                timeout=10,
                verify=False
            )
            data = res.json()
            token = data.get('data', {}).get('token') or data.get('token')
            if token:
                self.xingya_headers = {**self.headers_default, 'authorization': token}
                self.xingya_token = token
        except Exception as e:
            pass
        return self.xingya_headers

    def _request(self, url, method='GET', headers=None, data=None, timeout=5000):
        try:
            headers = {**self.headers_default, **(headers or {})}
            if method.upper() == 'POST':
                res = requests.post(url, headers=headers, json=data, timeout=timeout/1000, verify=False)
            else:
                res = requests.get(url, headers=headers, timeout=timeout/1000, verify=False)
            return res.json()
        except Exception as e:
            return None

    def homeContent(self, filter):
        classes = [{'type_name': p['name'], 'type_id': p['id']} for p in self.platform_list]
        filters = {}
        for item in self.platform_list:
            platform_id = item['id']
            if platform_id in self.filter_options:
                filters[platform_id] = self.filter_options[platform_id]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        return self.categoryContent('七猫', '1', False, {})

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        plat = self.platform.get(tid)
        area = extend.get('area') if extend.get('area') is not None else self.rule_filter_def.get(tid, {}).get('area', '')
        videos = []

        if not plat:
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

        try:
            if tid == '七猫':
                if pg > 1:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
                sign = self._md5(f"operation=1playlet_privacy=1tag_id={area}{self.keys}")
                url = f"{plat['host']}{plat['url1']}?tag_id={area}&playlet_privacy=1&operation=1&sign={sign}"
                header_x = self._get_header_x()
                res = self._request(url, headers={**header_x, **self.headers_default}, timeout=3000)
                if res and res.get('data', {}).get('list'):
                    for i in res['data']['list'][:6]:
                        videos.append({
                            'vod_id': f"七猫@{quote(str(i['playlet_id']))}",
                            'vod_name': i['title'],
                            'vod_pic': i['image_link'],
                            'vod_remarks': f"{i['total_episode_num']}集",
                            'vod_content': f"七猫短剧 | {i['total_episode_num']}集"
                        })
                return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}

            elif tid == '星芽':
                headers = self._ensure_xingya_auth()
                if area == '9':
                    rank = extend.get('rank') or extend.get('class2') or self.rule_filter_def['星芽'].get('rank', '1')
                    if pg > 1:
                        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
                    res = self._request(f"{plat['host']}{plat['rankDetail']}?id={rank}", headers=headers, timeout=10000)
                    for item in res.get('data', {}).get('list', []):
                        i = item.get('theater') or item
                        if not i or not i.get('id'):
                            continue
                        videos.append({
                            'vod_id': f"星芽@{plat['host']}{plat['url2']}?theater_parent_id={i['id']}",
                            'vod_name': i['title'],
                            'vod_pic': i['cover_url'],
                            'vod_remarks': f"{i.get('total', '')}集"
                        })
                    return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}

                class2 = extend.get('class2') or self.rule_filter_def['星芽'].get('class2', '0')
                url = f"{plat['host']}{plat['url1']}={area}&type=1&class2_ids={class2}&page_num={pg}&page_size=24"
                res = self._request(url, headers=headers, timeout=10000)
                data = res.get('data', {})
                for i in data.get('list', []):
                    item = i.get('theater') or i
                    if not item or not item.get('id'):
                        continue
                    videos.append({
                        'vod_id': f"星芽@{plat['host']}{plat['url2']}?theater_parent_id={item['id']}",
                        'vod_name': item['title'],
                        'vod_pic': item['cover_url'],
                        'vod_remarks': f"{item.get('total', '')}集"
                    })
                total = int(data.get('total') or len(videos))
                is_single_page = not videos or data.get('is_end') or total <= len(videos) or len(videos) > 24
                if is_single_page:
                    return {'list': videos if pg == 1 else [], 'page': pg, 'pagecount': 1, 'limit': len(videos) if pg == 1 else 0, 'total': total}
                pagecount = max(1, (total + 23) // 24)
                return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 24, 'total': total}

            elif tid == '西饭':
                if pg > 1:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
                search_url = f"{plat['host']}{plat['search']}?reqType=search&offset=0&keyword={quote(area or '')}&quickEngineVersion=-1&scene="
                search_res = self._request(search_url, timeout=10000)
                for block in search_res.get('result', {}).get('elements', []):
                    for item in block.get('contents', []):
                        dj = item.get('duanjuVo') or {}
                        if not dj.get('duanjuId'):
                            continue
                        categories = dj.get('categories', [])
                        if area and area not in categories:
                            continue
                        videos.append({
                            'vod_id': f"西饭@{dj['duanjuId']}#{dj['source']}",
                            'vod_name': dj['title'],
                            'vod_pic': dj['coverImageUrl'],
                            'vod_remarks': f"{dj.get('total', '')}集"
                        })
                return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}

            elif tid == '围观':
                device_name = 'Pixel 8 Pro'
                device_firm = 'Google'
                client_info = self._md5(str(int(time.time() * 1000))[-10:])
                url = f"{plat['host']}{plat['search']}?version_code=1500&version_name=1.5.0&device_name={quote(device_name)}&device_type=phone&is_first_day=true&is_first_24h=true&app_launch_way=icon&default_homepage=homepage_interaction&device_owning_firm={quote(device_firm)}&font_scale=default&os_type=1&clientInfo={client_info}"
                res = self._request(url, method='POST', headers={'User-Agent': 'okhttp/5.1.0', 'Content-Type': 'application/json; charset=utf-8'}, data={'audience': '全部', 'order': '最新', 'page': pg, 'pageSize': 30, 'searchWord': '', 'subject': area or ''}, timeout=10000)
                for i in res.get('data', []):
                    videos.append({
                        'vod_id': f"围观@{i['oneId']}",
                        'vod_name': i['title'],
                        'vod_pic': i.get('horzPoster') or i.get('vertPoster'),
                        'vod_remarks': f"{i.get('episodeCount', '')}集"
                    })
                return {'list': videos, 'page': pg, 'pagecount': pg if len(videos) < 30 else pg + 1, 'limit': 30, 'total': (pg - 1) * 30 + len(videos)}

            elif tid == '河马':
                url = f"{plat['host']}/browse/{area or self.rule_filter_def['河马']['area']}/{pg}"
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                        'Referer': url,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
                    }
                    res = requests.get(url, headers=headers, timeout=10, verify=False)
                    html = res.text
                    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>', html)
                    if match:
                        json_data = json.loads(match.group(1))
                        page_props = json_data.get('props', {}).get('pageProps', {})
                        for book in page_props.get('bookList', []):
                            if not book.get('bookId'):
                                continue
                            videos.append({
                                'vod_id': f"河马@/drama/{book['bookId']}",
                                'vod_name': book['bookName'],
                                'vod_pic': book.get('coverWap'),
                                'vod_remarks': f"{book.get('statusDesc', '')} {book.get('totalChapterNum', '')}集".strip()
                            })
                        pages = int(page_props.get('pages') or pg)
                        return {'list': videos, 'page': pg, 'pagecount': pages, 'limit': len(videos), 'total': pages * len(videos)}
                except Exception as e:
                    pass

        except Exception as e:
            pass

        return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}

    def detailContent(self, ids):
        videos = []
        for id in ids if isinstance(ids, list) else [ids]:
            if not id:
                continue
            parts = id.split('@', 1)
            if len(parts) < 2:
                continue
            plat_id, did = parts[0], parts[1]
            plat = self.platform.get(plat_id)
            if not plat:
                videos.append({'vod_id': id, 'vod_name': '平台不支持', 'vod_play_url': ''})
                continue

            vod = {'vod_id': id, 'vod_name': '未知', 'vod_pic': '', 'vod_remarks': '', 'vod_content': '', 'vod_play_from': '', 'vod_play_url': ''}

            try:
                if plat_id == '七猫':
                    did_decoded = unquote(did)
                    sign = self._md5(f"playlet_id={did_decoded}{self.keys}")
                    url = f"{plat['url2']}?playlet_id={did_decoded}&sign={sign}"
                    header_x = self._get_header_x()
                    res = self._request(url, headers={**header_x, **self.headers_default})
                    if res and res.get('data'):
                        d = res['data']
                        play_list = d.get('play_list', [])
                        play_url = '#'.join([f"{i['sort']}${i['video_url']}" for i in play_list])
                        vod = {**vod, 'vod_name': d['title'], 'vod_pic': d['image_link'], 'vod_remarks': f"{d['total_episode_num']}集", 'vod_content': d.get('intro', ''), 'vod_play_from': '七猫短剧', 'vod_play_url': play_url}

                elif plat_id == '星芽':
                    headers = self._ensure_xingya_auth()
                    res = self._request(did, headers=headers, timeout=10000)
                    if res and res.get('data'):
                        d = res['data']
                        theaters = d.get('theaters', [])
                        play_url = '#'.join([f"{i['num']}${i['son_video_url']}" for i in theaters])
                        vod = {**vod, 'vod_name': d['title'], 'vod_pic': d['cover_url'], 'vod_remarks': str(d.get('desc_tags', '')), 'vod_play_from': '星芽短剧', 'vod_play_url': play_url}

                elif plat_id == '西饭':
                    duanju_id, source = did.split('#', 1)
                    url = f"{plat['host']}{plat['url2']}?duanjuId={duanju_id}&source={source}"
                    res = self._request(url)
                    if res and res.get('result'):
                        d = res['result']
                        episode_list = d.get('episodeList', [])
                        play_url = '#'.join([f"{e['index']}${e['playUrl']}" for e in episode_list])
                        status = '已完结' if d.get('updateStatus') == 'over' else f"更新{d.get('total', '')}集"
                        vod = {**vod, 'vod_name': d['title'], 'vod_pic': d['coverImageUrl'], 'vod_remarks': f"{d.get('total', '')}集 {status}", 'vod_play_from': '西饭短剧', 'vod_play_url': play_url}

                elif plat_id == '围观':
                    device_name = 'Pixel 8 Pro'
                    device_firm = 'Google'
                    client_info = self._md5(str(int(time.time() * 1000))[-10:])
                    url = f"{plat['host']}{plat['url2']}?version_code=1500&version_name=1.5.0&device_name={quote(device_name)}&device_type=phone&is_first_day=true&is_first_24h=true&app_launch_way=icon&default_homepage=homepage_interaction&device_owning_firm={quote(device_firm)}&font_scale=default&os_type=1&clientInfo={client_info}&oneId={did}&page=1&pageSize=1000&userId=0&queryAll=true"
                    res = self._request(url, headers={'User-Agent': 'okhttp/5.1.0', 'Content-Type': 'application/json; charset=utf-8'}, timeout=10000)
                    episodes = res.get('data', [])
                    if episodes:
                        play_url = '#'.join([f"{e.get('playOrder') or e.get('title')}${self._base64_encode(json.dumps(e.get('videoClarityList', [])))}" for e in episodes])
                        vod = {**vod, 'vod_name': res.get('title') or episodes[0].get('title') or vod['vod_name'], 'vod_pic': res.get('vertPoster') or episodes[0].get('vertPoster') or '', 'vod_remarks': f"共{len(episodes)}集", 'vod_content': res.get('description', ''), 'vod_play_from': '围观短剧', 'vod_play_url': play_url}

                elif plat_id == '河马':
                    did_path = did if did.startswith('/drama/') else f"/drama/{did}"
                    full_url = f"{plat['host']}{did_path}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                        'Referer': full_url,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
                    }
                    res = requests.get(full_url, headers=headers, timeout=10, verify=False)
                    html = res.text
                    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>', html)
                    if match:
                        json_data = json.loads(match.group(1))
                        page_props = json_data.get('props', {}).get('pageProps', {})
                        book_info = page_props.get('bookInfoVo', {})
                        chapter_list = page_props.get('chapterList', [])
                        play_urls = []
                        for chapter in chapter_list:
                            chapter_id = chapter.get('chapterId')
                            chapter_name = chapter.get('chapterName')
                            video_vo = chapter.get('chapterVideoVo', {})
                            direct_url = video_vo.get('mp4') or video_vo.get('mp4720p') or video_vo.get('vodMp4Url')
                            if direct_url and re.search(r'\.(mp4|m3u8)', direct_url, re.I):
                                play_urls.append(f"{chapter_name}${direct_url}")
                            else:
                                drama_id = did_path.replace('/drama/', '')
                                play_urls.append(f"{chapter_name}${drama_id}+{chapter_id}")
                        vod = {**vod, 'vod_name': book_info.get('title') or book_info.get('bookName') or vod['vod_name'], 'vod_pic': book_info.get('coverWap') or '', 'vod_remarks': f"{book_info.get('statusDesc', '')} {book_info.get('totalChapterNum', '')}集".strip(), 'vod_content': book_info.get('introduction', ''), 'vod_play_from': '河马短剧', 'vod_play_url': '#'.join(play_urls)}

            except Exception as e:
                vod['vod_name'] = '加载失败'

            videos.append(vod)

        return {'list': videos}

    def playerContent(self, flag, id, vipFlags):
        if '七猫' in flag:
            return {'parse': 0, 'url': id}

        if '西饭' in flag:
            try:
                res = requests.get(id, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False, allow_redirects=True)
                final_url = res.url
                return {'parse': 0, 'url': final_url or id}
            except:
                return {'parse': 0, 'url': id}

        if '围观' in flag:
            try:
                ps = json.loads(self._base64_decode(id))
                urls = []
                for item in ps or []:
                    if item.get('name') and item.get('url'):
                        urls.extend([item['name'], item['url']])
                return {'parse': 0, 'url': urls if urls else id, 'headers': {'User-Agent': 'okhttp/5.1.0'}}
            except:
                return {'parse': 0, 'url': id}

        if '河马' in flag:
            if re.search(r'\.(mp4|m3u8)', id, re.I):
                return {'parse': 0, 'url': id}
            parts = id.split('+', 1)
            if len(parts) >= 2:
                drama_id, chapter_id = parts
                episode_url = f"{self.platform['河马']['host']}/episode/{drama_id}/{chapter_id}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                    'Referer': episode_url,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
                }
                try:
                    res = requests.get(episode_url, headers=headers, timeout=10, verify=False)
                    html = res.text
                    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>', html)
                    if match:
                        json_data = json.loads(match.group(1))
                        video_info = json_data.get('props', {}).get('pageProps', {}).get('chapterInfo', {}).get('chapterVideoVo', {})
                        video_url = video_info.get('mp4') or video_info.get('mp4720p') or video_info.get('vodMp4Url')
                        if not video_url:
                            m = re.search(r'(https?://[^"\']+\.mp4[^"\']*)', html)
                            video_url = m.group(1) if m else ''
                        return {'parse': 0, 'url': video_url}
                except:
                    pass
            return {'parse': 0, 'url': id}

        return {'parse': 0, 'url': id}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if pg else 1

        if not key:
            return {
                'list': [],
                'page': pg,
                'pagecount': 1,
                'limit': 0,
                'total': 0
            }

        videos = []
        seen = set()

        def safe_push(item):
            if not item:
                return

            vod_id = str(item.get('vod_id', '')).strip()
            vod_name = str(item.get('vod_name', '')).strip()

            if not vod_id or not vod_name:
                return

            if vod_id in seen:
                return

            item['vod_id'] = vod_id
            item['vod_name'] = vod_name

            seen.add(vod_id)
            videos.append(item)

        # 七猫搜索
        try:
            sign = self._md5(
                f"operation=2playlet_privacy=1search_word={key}{self.keys}"
            )

            url = (
                f"{self.platform['七猫']['host']}"
                f"{self.platform['七猫']['search']}"
                f"?search_word={quote(key)}"
                f"&playlet_privacy=1"
                f"&operation=2"
                f"&sign={sign}"
            )

            header_x = self._get_header_x()

            res = self._request(
                url,
                headers={**header_x, **self.headers_default},
                timeout=6000
            )
            if res:
                for i in res.get('data', {}).get('list', []):
                    safe_push({
                        'vod_id': f"七猫@{quote(str(i['playlet_id']))}",
                        'vod_name': i.get('title', ''),
                        'vod_pic': i.get('image_link', ''),
                        'vod_remarks': f"七猫短剧｜{i.get('total_episode_num', '')}集"
                    })

        except Exception:
            pass

        # 星芽搜索
        try:
            plat = self.platform['星芽']
            headers = self._ensure_xingya_auth()

            res = self._request(
                plat['host'] + plat['search'],
                method='POST',
                headers=headers,
                data={'text': key},
                timeout=10000
            )
            if res:
                data = res.get('data', {})

                search_list = (
                    data.get('theater', {}).get('search_data', [])
                    or data.get('search_data', [])
                    or data.get('list', [])
                )

                for i in search_list:
                    if not i.get('id'):
                        continue

                    safe_push({
                        'vod_id': f"星芽@{plat['host']}{plat['url2']}?theater_parent_id={i['id']}",
                        'vod_name': i.get('title', ''),
                        'vod_pic': i.get('cover_url', ''),
                        'vod_remarks': f"星芽短剧｜{i.get('total', '')}集"
                    })

        except Exception:
            pass

        # 西饭搜索
        try:
            plat = self.platform['西饭']

            url = (
                f"{plat['host']}{plat['search']}"
                f"?reqType=search"
                f"&offset={(pg - 1) * 30}"
                f"&keyword={quote(key)}"
                f"&quickEngineVersion=-1"
                f"&scene="
            )

            res = self._request(url)
            if res:
                elements = res.get('result', {}).get('elements', [])

                for block in elements:
                    if block.get('duanjuVo'):
                        contents = [block]
                    else:
                        contents = block.get('contents', [])

                    for item in contents:
                        dj = item.get('duanjuVo') or {}
                        if not dj.get('duanjuId'):
                            continue

                        safe_push({
                            'vod_id': f"西饭@{dj['duanjuId']}#{dj['source']}",
                            'vod_name': dj.get('title', ''),
                            'vod_pic': dj.get('coverImageUrl', ''),
                            'vod_remarks': f"西饭短剧｜{dj.get('total', '')}集"
                        })

        except Exception:
            pass

        # 围观搜索
        try:
            plat = self.platform['围观']

            device_name = 'Pixel 8 Pro'
            device_firm = 'Google'
            client_info = self._md5(str(int(time.time() * 1000))[-10:])

            url = (
                f"{plat['host']}{plat['search']}"
                f"?version_code=1500"
                f"&version_name=1.5.0"
                f"&device_name={quote(device_name)}"
                f"&device_type=phone"
                f"&is_first_day=true"
                f"&is_first_24h=true"
                f"&app_launch_way=icon"
                f"&default_homepage=homepage_interaction"
                f"&device_owning_firm={quote(device_firm)}"
                f"&font_scale=default"
                f"&os_type=1"
                f"&clientInfo={client_info}"
            )

            res = self._request(
                url,
                method='POST',
                headers={
                    'User-Agent': 'okhttp/5.1.0',
                    'Content-Type': 'application/json; charset=utf-8'
                },
                data={
                    'audience': '',
                    'order': '',
                    'page': pg,
                    'pageSize': 30,
                    'searchWord': key,
                    'subject': ''
                },
                timeout=10000
            )
            if res:
                for i in res.get('data', []):
                    safe_push({
                        'vod_id': f"围观@{i['oneId']}",
                        'vod_name': i.get('title', ''),
                        'vod_pic': i.get('horzPoster') or i.get('vertPoster'),
                        'vod_remarks': f"围观短剧｜{i.get('episodeCount', '')}集"
                    })

        except Exception:
            pass

        # 河马搜索
        try:
            plat = self.platform['河马']

            tmpid = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=16))

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': f"{plat['host']}/search?searchValue={quote(key)}",
                'Origin': 'https://www.kuaikaw.cn',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'pname': 'www.kuaikaw.cn',
                'tmpid': tmpid
            }

            res = self._request(
                f"{plat['host']}{plat['search']}",
                method='POST',
                headers=headers,
                data={
                    'sourceType': 1,
                    'keyword': key,
                    'index': pg,
                    'page': pg
                },
                timeout=10000
            )
            if res:
                for book in res.get('data', {}).get('bookList', []):
                    if not book.get('bookId'):
                        continue

                    safe_push({
                        'vod_id': f"河马@/drama/{book['bookId']}",
                        'vod_name': book.get('bookName', ''),
                        'vod_pic': book.get('coverWap', ''),
                        'vod_remarks': (
                            f"{book.get('statusDesc', '')} "
                            f"{book.get('totalChapterNum', '')}集"
                        ).strip()
                    })

        except Exception:
            pass

        return {
            'list': videos,
            'page': pg,
            'pagecount': 1,
            'limit': len(videos),
            'total': len(videos)
        }
