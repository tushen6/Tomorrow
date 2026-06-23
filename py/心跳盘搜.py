# -*- coding: utf-8 -*-
import sys
import json
import re
import time
import requests
import base64
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append('..')
from base.spider import Spider

class DyuziPanSpider(Spider):
    """心跳4k剧场网盘资源搜索爬虫 - 终极修复流解析与新增动漫分组版"""
    
    SITE_URL = "https://ppan.dyuzi.com"
    WEB_SEARCH_API = f"{SITE_URL}/api/other/web_search"
    HOME_API = f"{SITE_URL}/api/frontend/home"
    RANKING_API = f"{SITE_URL}/api/frontend/ranking"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "text/event-stream, application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": SITE_URL,
        "X-Requested-With": "XMLHttpRequest"
    }

    REQUEST_TIMEOUT = 60
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 0.5
    REQUEST_DELAY = 0.5

    IS_TYPE_MAP = {
        0: 'quark', 1: 'uc', 2: 'baidu', 3: 'aliyun', 4: 'xunlei', 5: 'a189', 6: 'quark'
    }

    PAN_CONFIG = {
        'quark': {'name': '夸克云盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/quark.webp'},
        'uc': {'name': 'UC网盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/uc.webp'},
        'a189': {'name': '天翼云盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/189.webp'},
        'aliyun': {'name': '阿里云盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/aliyun.webp'},
        'baidu': {'name': '百度网盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/baidu.webp'},
        'xunlei': {'name': '迅雷云盘', 'icon': 'https://ppan.dyuzi.com/views/index/template/btlm/disk-icons/xunlei.webp'},
        'magnet': {'name': '磁力链接', 'icon': ''},
        'other': {'name': '其他网盘', 'icon': ''}
    }

    _PSQ_GROUP_ORDER = ["quark", "uc", "aliyun", "a189", "baidu", "xunlei", "magnet", "other"]

    def __init__(self):
        super().__init__()
        self.pan_priority = ''
        self._last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        retries = Retry(total=self.MAX_RETRIES, backoff_factor=self.BACKOFF_FACTOR, status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def init(self, extend):
        try:
            extend_dict = json.loads(extend) if extend else {}
            self.pan_priority = extend_dict.get('pan_priority', 'quark,a189,uc')
        except json.JSONDecodeError:
            self.pan_priority = 'quark,a189,uc'

    def getName(self): return "盘搜"
    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): return False

    # ======= 1. 分类栏增加动漫类别 =======
    def homeContent(self, filter):
        return {
            'class': [
                {"type_id": "1", "type_name": "电视剧"}, 
                {"type_id": "2", "type_name": "电影"},
                {"type_id": "3", "type_name": "动漫"}  # 新增动漫分类
            ], 
            'filters': {}, 
            'list': []
        }

    # ======= 2. 首页推荐位混合展现（电视剧+动漫） =======
    def homeVideoContent(self):
        vod_list = []
        # 抓取电视剧推荐 (前12个)
        try:
            resp = self.session.get(self.RANKING_API, params={'channel': '电视剧', 'limit': 12}, timeout=self.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and data.get('data', {}).get('list'):
                    for item in data['data']['list']:
                        vod_list.append({
                            "vod_id": self._b64e({'title': item.get('title', ''), 'type': 'ranking'}),
                            "vod_name": item.get('title', ''),
                            "vod_pic": item.get('src', ''),
                            "vod_remarks": f"剧集|热度:{item.get('hot_score', '0')[:4]}"
                        })
        except: pass

        # 抓取动漫推荐 (追加12个)
        try:
            resp = self.session.get(self.RANKING_API, params={'channel': '动漫', 'limit': 12}, timeout=self.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and data.get('data', {}).get('list'):
                    for item in data['data']['list']:
                        vod_list.append({
                            "vod_id": self._b64e({'title': item.get('title', ''), 'type': 'ranking'}),
                            "vod_name": item.get('title', ''),
                            "vod_pic": item.get('src', ''),
                            "vod_remarks": f"动漫|热度:{item.get('hot_score', '0')[:4]}"
                        })
        except: pass

        return {'list': vod_list}

    # ======= 3. 分类点击切换逻辑（支持动漫频道） =======
    def categoryContent(self, cid, page, filter, ext):
        try:
            channel_map = {'1': '电视剧', '2': '电影', '3': '动漫'}
            channel = channel_map.get(str(cid), '电视剧')
            
            resp = self.session.get(self.RANKING_API, params={'channel': channel, 'limit': 30}, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            vod_list = []
            if data.get('code') == 0 and data.get('data', {}).get('list'):
                for item in data['data']['list']:
                    vod_list.append({
                        "vod_id": self._b64e({'title': item.get('title', ''), 'type': 'ranking'}),
                        "vod_name": item.get('title', ''),
                        "vod_pic": item.get('src', ''),
                        "vod_remarks": f"评分:{item.get('score_avg', '0')}"
                    })
            return {'list': vod_list, 'page': 1, 'pagecount': 1, 'limit': 30, 'total': len(vod_list)}
        except: return {'list': []}

    def _get_pan_type(self, is_type): return self.IS_TYPE_MAP.get(is_type, 'other')

    def _b64e(self, obj):
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if not isinstance(obj, str) else obj
        return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

    def _b64d(self, s):
        try:
            s += "=" * (-len(s) % 4)
            decoded = base64.urlsafe_b64decode(s.encode()).decode()
            try: return json.loads(decoded)
            except: return decoded
        except: return s

    def _parse_sse_response(self, response_text):
        results = []
        if not response_text: return results
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if line.startswith('data:') and '[DONE]' not in line:
                try:
                    data = json.loads(line[5:].strip())
                    if 'title' in data and 'url' in data: results.append(data)
                except: continue
        return results

    def _psq_quality_score(self, title):
        score = 0
        t_upper = title.upper()
        if "杜比" in title or "DOLBY" in t_upper or "DOVI" in t_upper: score += 120000
        if "DV" in t_upper: score += 100000
        if "高码" in title or "HQ" in t_upper: score += 90000
        if "HDR10+" in t_upper: score += 85000
        if "HDR10" in t_upper: score += 80000
        if "HDR" in t_upper: score += 75000
        if "4K" in t_upper or "2160P" in t_upper or "UHD" in t_upper: score += 65000
        if "1080P" in t_upper or "FHD" in t_upper: score += 45000
        if "蓝光" in title or "BLURAY" in t_upper: score += 40000
        if "REMUX" in t_upper: score += 35000
        return score

    def _psq_extract_size_gb(self, title):
        try:
            match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([mMgGtT])[bB]?', title)
            if match:
                val = float(match.group(1))
                unit = match.group(2).lower()
                if unit == 't': return val * 1024
                if unit == 'g': return val
                if unit == 'm': return val / 1024
        except: pass
        return 0.0

    def _clean_resource_title(self, title):
        t = re.sub(r'https?://\S+', '', title)
        t = re.sub(r'\[夸克网盘\]|\[UC网盘\]|\[天翼云盘\]|微云|百度云', '', t)
        t = re.sub(r'^\s*【.*?】|^\s*\[.*?\]', '', t)
        t = t.split('◆')[0].split('▶')[0]
        t = re.sub(r'\s+', ' ', t).strip()
        return t if t else title

    def _secure_fetch_items(self, keywords):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY: time.sleep(self.REQUEST_DELAY - elapsed)
        try:
            params = {'title': keywords, 'is_type': 'all', 'is_show': '1', 'skip_check': '0', 'status': '1', 'max': '120'}
            resp = self.session.get(self.WEB_SEARCH_API, params=params, timeout=self.REQUEST_TIMEOUT)
            self._last_request_time = time.time()
            if resp.status_code == 200:
                return self._parse_sse_response(resp.text)
        except Exception as e:
            print(f"[DyuziPan] 安全拉取接口异常被拦截: {e}")
        return []

    def searchContent(self, key, quick, pg="1"): return self._perform_search(key, pg)
    def searchContentPage(self, key, quick, page): return self._perform_search(key, page)

    def _perform_search(self, keywords, page_str):
        try: page = int(page_str)
        except: page = 1
        result = {'list': [], 'page': page, 'pagecount': 1, 'limit': 60, 'total': 0}
        if not keywords or page > 1: return result

        items = self._secure_fetch_items(keywords)
        if not items: return result

        merged_resources = {}
        for item in items:
            title, url, is_type = item.get('title', ''), item.get('url', ''), item.get('is_type', -1)
            if not url or not title: continue
            
            pan_type = self._get_pan_type(is_type)
            clean_name = self._clean_resource_title(title)
            group_key = f"{pan_type}_{clean_name}"

            if group_key not in merged_resources:
                merged_resources[group_key] = {
                    'clean_name': clean_name,
                    'pan_type': pan_type,
                    'score': self._psq_quality_score(title) + self._psq_extract_size_gb(title),
                    'links': [] 
                }
            merged_resources[group_key]['links'].append({'title': title, 'url': url})

        sorted_resources = list(merged_resources.values())
        sorted_resources.sort(key=lambda x: x['score'], reverse=True)

        for res in sorted_resources:
            pan_cfg = self.PAN_CONFIG.get(res['pan_type'], self.PAN_CONFIG['other'])
            display_name = f"[{pan_cfg['name']}] {res['clean_name']}"
            result['list'].append({
                "vod_id": self._b64e({'is_group': True, 'resource_name': display_name, 'pan_type': res['pan_type'], 'links': res['links']}),
                "vod_name": display_name,
                "vod_pic": pan_cfg.get('icon', ''),
                "vod_remarks": f"包含 {len(res['links'])} 个文件"
            })

        result['total'] = len(result['list'])
        return result

    def detailContent(self, ids):
        result = {'list': []}
        if not ids or not ids[0]: return result
        try:
            vod_data = self._b64d(ids[0])
            if not isinstance(vod_data, dict): return result

            # ─── 首页排行榜/推荐页点击 ───
            if vod_data.get('type') == 'ranking':
                search_title = vod_data.get('title', '')
                if not search_title: return result
                
                items = self._secure_fetch_items(search_title)
                if not items: 
                    result['list'].append({
                        "vod_id": ids[0], "vod_name": search_title, "vod_pic": "",
                        "vod_content": f"提示：未在当前接口中检索到该动漫/影视的网盘分享。",
                        "vod_play_from": "暂无资源", "vod_play_url": "点击刷新重试$push://https://ppan.dyuzi.com", "vod_remarks": "无资源"
                    })
                    return result

                buckets = {k: [] for k in self._PSQ_GROUP_ORDER}
                for item in items:
                    title, url, is_type = item.get('title', ''), item.get('url', ''), item.get('is_type', -1)
                    if not url or not title: continue
                    pt = self._get_pan_type(is_type)
                    if pt not in buckets: pt = 'other'
                    buckets[pt].append({'title': title, 'url': url})

                play_from_list = []
                play_url_list = []

                for group_key in self._PSQ_GROUP_ORDER:
                    b_links = buckets.get(group_key, [])
                    if not b_links: continue
                    play_from_list.append(self.PAN_CONFIG.get(group_key, self.PAN_CONFIG['other'])['name'])
                    
                    eps = []
                    for idx, item in enumerate(b_links):
                        clean_ep = item['title'].replace('$', '').replace('#', '').strip()
                        if len(clean_ep) > 60: clean_ep = f"进入云盘播放-{idx+1}"
                        eps.append(f"{clean_ep}${item['url']}")
                    play_url_list.append("#".join(eps))

                if play_from_list:
                    result['list'].append({
                        "vod_id": ids[0],
                        "vod_name": search_title,
                        "vod_pic": "",
                        "vod_content": f"资源名称: {search_title}\n系统已为您全网智能检索相关网盘源。",
                        "vod_play_from": "$$$".join(play_from_list),
                        "vod_play_url": "$$$".join(play_url_list),
                        "vod_remarks": f"聚合 {len(play_from_list)} 个网盘线路"
                    })
                return result

            # ─── 搜索页点击 ───
            resource_name = vod_data.get('resource_name', '网盘资源')
            pan_type = vod_data.get('pan_type', 'other')
            links = vod_data.get('links', [])

            pan_cfg = self.PAN_CONFIG.get(pan_type, self.PAN_CONFIG['other'])
            episode_strings = []
            for idx, item in enumerate(links):
                clean_ep_title = item['title'].replace('$', '').replace('#', '').strip()
                if len(clean_ep_title) > 60: clean_ep_title = f"打开云盘-{idx+1}"
                episode_strings.append(f"{clean_ep_title}${item['url']}")

            result['list'].append({
                "vod_id": ids[0],
                "vod_name": resource_name,
                "vod_pic": pan_cfg.get('icon', ''),
                "vod_content": f"资源名称: {resource_name}\n专属线路: {pan_cfg['name']}",
                "vod_play_from": pan_cfg['name'],
                "vod_play_url": "#".join(episode_strings),
                "vod_remarks": f"共 {len(links)} 个资源版本"
            })
        except Exception as e:
            print("[DyuziPan] 详情页分栏异常:", e)
        return result

    def playerContent(self, flag, pid, vipFlags):
        result = {"parse": 0, "jx": 0, "url": "", "header": self.HEADERS}
        if not pid: return result
        try:
            url = pid.split('$', 1)[1] if '$' in pid else pid
            url = url.strip().replace(' ', '')
            if not url.startswith(('http://', 'https://', 'magnet:')):
                url = 'https://' + url
            if not url.startswith('push://'):
                url = 'push://' + url
            result['url'] = url
        except: pass
        return result

    def localProxy(self, params): return None

Spider = DyuziPanSpider