# coding=utf-8
"""
目标站: 4kvm  首页: https://www.4kvm.net
动态筛选、精准分集、去重列表
"""
import re
import sys
import json
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://www.4kvm.top"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "动漫"}
        ]
        self._filters_cache = None

    # ================= 动态筛选解析 =================
    def _fetch_filters_for_classify(self, tid):
        """请求 /filter?classify=tid，解析页面筛选区域，返回该分类的筛选列表"""
        url = f"{self.site_url}/filter?classify={tid}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        filter_groups = []
        containers = soup.select('main div.flex.flex-wrap.items-center.gap-3')
        for container in containers:
            links = container.select('a[href]')
            if len(links) < 2:
                continue
            first_text = links[0].get_text(strip=True)
            if not first_text.startswith('全部'):
                continue
            group_name = first_text.replace('全部', '', 1).strip()
            # 从非全部的链接中提取参数键
            param_key = None
            for a in links[1:]:
                href = a.get('href', '')
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                for k in qs:
                    if k not in ('classify', 'page'):
                        param_key = k
                        break
                if param_key:
                    break
            if not param_key:
                continue
            if param_key in ('sort_by', 'order'):
                continue
            options = []
            for a in links:
                text = a.get_text(strip=True)
                href = a.get('href', '')
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                val = ''
                if param_key in qs:
                    val = qs[param_key][0] if qs[param_key] else ''
                if text.startswith('全部'):
                    val = ''
                options.append({"n": text, "v": val})
            if options:
                filter_groups.append({
                    "key": param_key,
                    "name": group_name,
                    "value": options
                })
        return filter_groups

    def _get_all_filters(self):
        if self._filters_cache is not None:
            return self._filters_cache
        filters = {}
        for cat in self.categories:
            tid = cat["type_id"]
            groups = self._fetch_filters_for_classify(tid)
            if groups:
                filters[tid] = groups
        # 为没有筛选的分类复用电影分类的筛选
        if "1" in filters:
            if "3" not in filters:
                filters["3"] = filters["1"]
            if "4" not in filters:
                filters["4"] = filters["1"]
        self._filters_cache = filters
        return filters

    # ================= 核心业务方法 =================
    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 使用唯一卡片容器
            cards = soup.select('div[data-vod-id]')
            for card in cards[:20]:
                a = card.select_one('a.block[href^="/play/"]')
                if not a:
                    continue
                vod_id = card.get('data-vod-id', '').strip()
                if not vod_id:
                    href = a.get('href', '')
                    vod_id = href.replace('/play/', '').strip()
                if not vod_id:
                    continue
                title_tag = card.select_one('h3.text-white') or card.select_one('h3')
                vod_name = title_tag.get_text(strip=True) if title_tag else ''
                if not vod_name:
                    continue
                img = card.select_one('img[data-src]')
                vod_pic = ''
                if img:
                    src = img.get('data-src', '')
                    if src and not src.startswith('data:'):
                        vod_pic = src if src.startswith('http') else 'https:' + src
                remark_tag = card.select_one('.text-green-500, .text-yellow-400, span[class*="px-1.5"]')
                vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        return {"class": self.categories, "list": video_list, "filters": self._get_all_filters()}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        params = {"classify": tid}
        if extend:
            for k, v in extend.items():
                if v and k != 'classify':
                    params[k] = v
        if page > 1:
            params['page'] = page
        query = urllib.parse.urlencode(params)
        url = f"{self.site_url}/filter?{query}"

        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('div[data-vod-id]')
        for card in cards:
            a = card.select_one('a.block[href^="/play/"]')
            if not a:
                continue
            vod_id = card.get('data-vod-id', '').strip()
            if not vod_id:
                href = a.get('href', '')
                vod_id = href.replace('/play/', '').strip()
            if not vod_id:
                continue
            title_tag = card.select_one('h3.text-white') or card.select_one('h3')
            vod_name = title_tag.get_text(strip=True) if title_tag else ''
            if not vod_name:
                continue
            img = card.select_one('img[data-src]')
            vod_pic = ''
            if img:
                src = img.get('data-src', '')
                if src and not src.startswith('data:'):
                    vod_pic = src if src.startswith('http') else 'https:' + src
            remark_tag = card.select_one('.text-green-500, .text-yellow-400, span[class*="px-1.5"]')
            vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
            video_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks
            })

        # 分页处理
        pagecount = page
        page_text = soup.find(string=re.compile(r'共\s*\d+\s*页'))
        if page_text:
            nums = re.findall(r'\d+', page_text)
            if nums:
                pagecount = int(nums[-1])
        else:
            page_block = soup.select_one('.flex.justify-center')
            if page_block:
                page_links = page_block.select('a[href*="page="]')
                for a in page_links:
                    text = a.get_text(strip=True)
                    if text.isdigit():
                        pagecount = max(pagecount, int(text))

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/play/{vod_id}"
        resp = self.fetch(url, headers=self.headers)
        if not resp or resp.status_code != 200:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 标题
        title_elem = soup.select_one('h1.text-xl') or soup.select_one('h1') or soup.select_one('h2')
        vod_name = title_elem.get_text(strip=True) if title_elem else vod_id

        # 图片
        vod_pic = ''
        img_elem = soup.select_one('img.w-full') or soup.select_one('img[src]')
        if img_elem:
            src = img_elem.get('src', '') or img_elem.get('data-src', '')
            if src and not src.startswith('data:'):
                vod_pic = src if src.startswith('http') else 'https:' + src

        # 导演、主演、简介
        vod_director = ''
        vod_actor = ''
        vod_content = ''
        info_block = soup.select_one('.rounded-lg div.grid') or soup.select_one('div.grid')
        if info_block:
            text = info_block.get_text(' ', strip=True)
            dir_match = re.search(r'导演\s*([^主\n]+)', text)
            if dir_match:
                vod_director = dir_match.group(1).strip()
            act_match = re.search(r'主演\s*([^剧\n]+)', text)
            if act_match:
                vod_actor = act_match.group(1).strip()
            desc_match = re.search(r'剧情简介\s*(.+)', text, re.DOTALL)
            if desc_match:
                vod_content = desc_match.group(1).strip()
            elif re.search(r'简介\s*(.+)', text, re.DOTALL):
                vod_content = re.search(r'简介\s*(.+)', text, re.DOTALL).group(1).strip()

        # ================= 分集解析 (基于 episodeManager) =================
        play_from_list = []
        play_url_list = []

        episode_manager = soup.select_one('[x-data*="episodeManager"]')
        if episode_manager:
            xdata = episode_manager.get('x-data', '')
            lines_raw = re.findall(r'\{[^}]*lineName\s*:\s*\'([^\']+)\'[^}]*episodeCount\s*:\s*(\d+)[^}]*\}', xdata)
            lines_info = [{'lineName': name, 'episodeCount': int(count)} for name, count in lines_raw]

            episode_links = episode_manager.select('a[data-episode]')
            lines_eps = {}
            for a in episode_links:
                line = a.get('data-line', '1')
                ep = a.get('data-episode', '')
                href = a.get('href', '')
                if not href or not ep:
                    continue
                full_url = href if href.startswith('http') else self.site_url + href
                lines_eps.setdefault(line, []).append((int(ep), full_url))

            for line_key in sorted(lines_eps.keys()):
                eps = sorted(lines_eps[line_key], key=lambda x: x[0])
                line_name = f'线路{line_key}'
                for info in lines_info:
                    line_name = info['lineName']
                    break  # 目前只用第一个线路名
                if not eps:
                    continue
                episode_strs = [f"第{ep[0]}集${ep[1]}" for ep in eps]
                play_from_list.append(line_name)
                play_url_list.append('#'.join(episode_strs))

        # 回退：无分集则直接播放当前页
        if not play_url_list:
            play_from_list.append('播放')
            play_url_list.append(f"播放${vod_id}")

        vod_play_from = '$$$'.join(play_from_list)
        vod_play_url = '$$$'.join(play_url_list)

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": "",
            "vod_year": "",
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        params = {"q": key}
        if page > 1:
            params['page'] = page
        query = urllib.parse.urlencode(params)
        url = f"{self.site_url}/search?{query}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('div[data-vod-id]')
        if not cards:
            # 搜索页可能没有 data-vod-id，降级处理
            for a in soup.select('a.block[href^="/play/"]'):
                href = a.get('href', '')
                vod_id = href.replace('/play/', '').strip()
                if not vod_id:
                    continue
                h3 = a.select_one('h3')
                vod_name = h3.get_text(strip=True) if h3 else href
                if not vod_name:
                    continue
                img = a.select_one('img[data-src]')
                vod_pic = ''
                if img:
                    src = img.get('data-src', '')
                    if src and not src.startswith('data:'):
                        vod_pic = src if src.startswith('http') else 'https:' + src
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": ''
                })
        else:
            for card in cards[:30]:
                a = card.select_one('a.block[href^="/play/"]')
                if not a:
                    continue
                vod_id = card.get('data-vod-id', '').strip()
                if not vod_id:
                    href = a.get('href', '')
                    vod_id = href.replace('/play/', '').strip()
                if not vod_id:
                    continue
                title_tag = card.select_one('h3.text-white') or card.select_one('h3')
                vod_name = title_tag.get_text(strip=True) if title_tag else ''
                if not vod_name:
                    continue
                img = card.select_one('img[data-src]')
                vod_pic = ''
                if img:
                    src = img.get('data-src', '')
                    if src and not src.startswith('data:'):
                        vod_pic = src if src.startswith('http') else 'https:' + src
                remark_tag = card.select_one('.text-green-500, .text-yellow-400, span[class*="px-1.5"]')
                vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        return {"list": video_list, "page": page, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith('http'):
            url = f"{self.site_url}/play/{id}"
        else:
            url = id
        return {"parse": 1, "url": url, "header": self.headers}