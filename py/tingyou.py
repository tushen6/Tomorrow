# -*- coding: utf-8 -*-
# ============ 71us 模板 v7.5 / tingyou.fm (听友听书 有声小说) ============
# 站点: https://tingyou.fm  (SPA Nuxt, H5 未加密 API)
# API 基址: https://appp.fdhtbz.cn/api/h5/listening/
#   分类列表 GET  /category?sort={popular|updated|newest}&page=N[&cat=有声小说|评书][&status=0|1]
#   专辑详情 GET  /album/{id}
#   章节列表 GET  /chapters/{id}   (一次返回全部章节)
#   播放地址 POST /play  body={"album_id":"..","chapter_idx":N}  -> {"play_url":"https://...mp4"}
#   搜索     POST /search body={"keyword":"..","page":N}
# 代理回退: https://tingyou.fm/listening-api/{path}
# 定版: 71us模板v7.5 | 2026-10-09
# ★版本兼容铁律: 全文件禁3.9+API; 分隔符 $=名称/地址 | #=选集 | $$$=线路
import sys, re, json, time
from urllib.parse import quote, urlencode
import requests

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

# ============ ★ CONFIG ============
TEMPLATE_MODE = 'normal'
HOSTS = ['https://tingyou.fm']
API_HOSTS = [
    'https://appp.fdhtbz.cn/api/h5/listening',
    'https://tingyou.fm/listening-api',
]
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
# 一级分类: type_id 用 cat 参数; 空=全部
CATEGORIES = {
    '': '全部',
    '有声小说': '有声小说',
    '评书': '评书',
}
# 筛选: 排序 + 状态
FILTERS_RAW = {
    '': [
        {'key': 'sort', 'name': '排序', 'value': [
            {'n': '播放最多', 'v': 'popular'},
            {'n': '最近更新', 'v': 'updated'},
            {'n': '最新发布', 'v': 'newest'},
        ]},
        {'key': 'status', 'name': '状态', 'value': [
            {'n': '全部状态', 'v': ''},
            {'n': '连载中', 'v': '1'},
            {'n': '已完结', 'v': '0'},
        ]},
    ],
}
FILTER_YEARS = []
PK = ''
REFERER = 'https://tingyou.fm/'
PIC_REFERER = ''
IMG_PROXY = ''
IMG_HOST = ''
FD_ZONE = 0
PROBE = 0
PAGE_MINLEN = 100
SITE_KEY = 'tingyou'
VIDEO_EXTS = 'm3u8|mp4|flv|mkv|avi|ts|m4a|mp3|aac'

# 脱敏
BLOCK_KW = [
    '幼女', '幼齿', '萝莉', '未成年', '小学生', '中学生', '儿童色情',
    '强奸', '轮奸', '迷奸', '兽交', '人兽',
]
BLOCK_VAR = []
BLOCK_CIDS = set()


def _blocked(text):
    if not text:
        return False
    t = str(text).lower()
    for k in BLOCK_KW:
        if k in t:
            return True
    return False


class Spider(Spider):
    def init(self, extend=''):
        self.base = HOSTS[0].rstrip('/')
        self.api_hosts = list(API_HOSTS)
        self.ua = UA
        self.pk = PK
        self.ref = REFERER or self.base
        self.types = dict(CATEGORIES)
        self.filters = {}
        self._pcm = {}
        self._session = None
        self._build_filters()

    def _sess(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': self.ua,
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base,
                'Referer': self.ref,
            })
        return self._session

    def _build_filters(self):
        # 每个一级分类共用同一套筛选
        for tid in self.types:
            self.filters[tid] = list(FILTERS_RAW.get('', []))

    def getName(self):
        return '听友听书'

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.search(r'\.(' + VIDEO_EXTS + r')(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter=True):
        classes = [{'type_id': k, 'type_name': v} for k, v in self.types.items()]
        result = {'class': classes}
        if filter and self.filters:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        # 首页推荐: 播放最多
        return self._list_page(cat='', sort='popular', page=1)

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        sort = (extend or {}).get('sort') or 'popular'
        status = (extend or {}).get('status') or ''
        cat = tid if tid else ''
        return self._list_page(cat=cat, sort=sort, page=pg, status=status)

    def _list_page(self, cat='', sort='popular', page=1, status=''):
        params = {'sort': sort or 'popular', 'page': str(page)}
        if cat:
            params['cat'] = cat
        if status != '' and status is not None:
            params['status'] = str(status)
        qs = urlencode(params)
        data = self._api_get('category?' + qs)
        items = []
        pagecount = 1
        if isinstance(data, dict):
            pagecount = int(data.get('pages') or 1) or 1
            for it in (data.get('data') or []):
                if not isinstance(it, dict):
                    continue
                name = str(it.get('title') or '').strip()
                if not name or _blocked(name):
                    continue
                vid = str(it.get('id') or '')
                if not vid:
                    continue
                pic = str(it.get('cover_url') or '')
                st = it.get('status')
                cnt = it.get('count') or 0
                remarks = ''
                if st == 1:
                    remarks = '连载中'
                elif st == 0:
                    remarks = '已完结'
                if cnt:
                    remarks = (remarks + ' · ' if remarks else '') + '%s集' % cnt
                items.append({
                    'vod_id': vid,
                    'vod_name': name[:80],
                    'vod_pic': self._pic(pic),
                    'vod_remarks': remarks[:40],
                })
        return {
            'list': items,
            'page': page,
            'pagecount': max(pagecount, 1),
            'limit': 20,
            'total': pagecount * 20,
        }

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ''
        if not vid:
            return {'list': []}
        album = self._api_get('album/' + vid)
        if not isinstance(album, dict) or not album.get('id'):
            # 代理回退
            album = self._api_get('album/' + vid, prefer_proxy=True)
        if not isinstance(album, dict) or not album.get('id'):
            return {'list': []}

        title = str(album.get('title') or '').strip()
        if _blocked(title):
            return {'list': []}
        author = str(album.get('author') or '').strip()
        teller = str(album.get('teller') or '').strip()
        pic = str(album.get('cover_url') or '')
        synopsis = str(album.get('synopsis') or '').strip()
        typ = str(album.get('type') or '')
        cat = str(album.get('cat') or '')
        cnt = album.get('count') or 0
        st = album.get('status')
        status_txt = '连载中' if st == 1 else ('已完结' if st == 0 else '')
        type_name = '/'.join([x for x in [typ, cat] if x])

        # 章节
        chapters = self._fetch_chapters(vid)
        play_from = '听友听书'
        play_urls = []
        for ch in chapters:
            idx = ch.get('index') or 0
            ctitle = str(ch.get('title') or ('第%s集' % idx)).strip()
            # vod_play_url: 名称$albumId_chapterIdx
            play_urls.append('%s$%s_%s' % (ctitle, vid, idx))
        play_url = '#'.join(play_urls) if play_urls else ''

        actor = teller
        if author and author != teller:
            actor = '%s / %s' % (author, teller) if teller else author
        # 清理污染
        for sep in ['_免费听书', '|免费', '免费收听']:
            if sep in actor:
                actor = actor.split(sep)[0].strip()

        vod = {
            'vod_id': vid,
            'vod_name': title[:100],
            'vod_pic': self._pic(pic),
            'type_name': type_name[:40],
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': (status_txt + (' · %s集' % cnt if cnt else '')).strip(' ·'),
            'vod_actor': actor[:60],
            'vod_director': author[:40],
            'vod_content': synopsis[:500] if synopsis else '',
            'vod_play_from': play_from,
            'vod_play_url': play_url,
        }
        return {'list': [vod]}

    def _fetch_chapters(self, album_id):
        data = self._api_get('chapters/' + str(album_id))
        if not isinstance(data, dict) or not data.get('chapters'):
            data = self._api_get('chapters/' + str(album_id), prefer_proxy=True)
        chs = []
        if isinstance(data, dict):
            for c in (data.get('chapters') or []):
                if not isinstance(c, dict):
                    continue
                idx = c.get('index')
                if idx is None:
                    continue
                chs.append({
                    'id': c.get('id'),
                    'index': int(idx),
                    'title': str(c.get('title') or ('第%s集' % idx)),
                    'duration': c.get('duration') or 0,
                })
        chs.sort(key=lambda x: x['index'])
        return chs

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg='1'):
        pg = int(pg) if pg else 1
        if not key or _blocked(key):
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 20, 'total': 0}
        body = {'keyword': key, 'page': pg}
        data = self._api_post('search', body)
        items = []
        has_more = False
        if isinstance(data, dict):
            has_more = bool(data.get('has_more'))
            for it in (data.get('results') or data.get('data') or []):
                if not isinstance(it, dict):
                    continue
                name = str(it.get('title') or '').strip()
                if not name or _blocked(name):
                    continue
                vid = str(it.get('id') or '')
                if not vid:
                    continue
                pic = str(it.get('cover_url') or '')
                st = it.get('status')
                cnt = it.get('count') or 0
                remarks = ''
                if st == 1:
                    remarks = '连载中'
                elif st == 0:
                    remarks = '已完结'
                if cnt:
                    remarks = (remarks + ' · ' if remarks else '') + '%s集' % cnt
                items.append({
                    'vod_id': vid,
                    'vod_name': name[:80],
                    'vod_pic': self._pic(pic),
                    'vod_remarks': remarks[:40],
                })
        pagecount = pg + 1 if has_more else pg
        return {
            'list': items,
            'page': pg,
            'pagecount': max(pagecount, 1),
            'limit': 20,
            'total': pagecount * 20,
        }

    def playerContent(self, flag, id, vipFlags):
        # id = albumId_chapterIdx
        parse, url = 0, ''
        try:
            parts = str(id).rsplit('_', 1)
            if len(parts) == 2:
                album_id, chapter_idx = parts[0], int(parts[1])
            else:
                album_id, chapter_idx = str(id), 1
            body = {'album_id': str(album_id), 'chapter_idx': int(chapter_idx)}
            data = self._api_post('play', body)
            if isinstance(data, dict):
                play_url = str(data.get('play_url') or '').strip()
                if play_url.startswith('http'):
                    url = play_url
                    parse = 0
        except Exception:
            pass
        if not url:
            # 回退: 用站点页解析
            parse = 1
            url = '%s/listening/album/%s' % (self.base, str(id).split('_')[0])
        headers = {
            'User-Agent': self.ua,
            'Referer': self.ref,
            'Origin': self.base,
        }
        return {
            'parse': parse,
            'url': url,
            'header': headers,
        }

    # ========== HTTP ==========
    def _api_get(self, path, prefer_proxy=False):
        hosts = list(self.api_hosts)
        if prefer_proxy:
            hosts = hosts[::-1]
        last_err = None
        for host in hosts:
            url = host.rstrip('/') + '/' + path.lstrip('/')
            try:
                r = self._sess().get(url, timeout=15)
                if r.status_code != 200:
                    last_err = 'HTTP %s' % r.status_code
                    continue
                text = r.text.strip()
                if not text or text[0] not in '{[':
                    last_err = 'not json'
                    continue
                return json.loads(text)
            except Exception as e:
                last_err = str(e)
                continue
        return {}

    def _api_post(self, path, body):
        hosts = list(self.api_hosts)
        last_err = None
        for host in hosts:
            url = host.rstrip('/') + '/' + path.lstrip('/')
            try:
                r = self._sess().post(url, json=body, timeout=15, headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Origin': self.base,
                    'Referer': self.ref,
                })
                if r.status_code != 200:
                    last_err = 'HTTP %s' % r.status_code
                    continue
                text = r.text.strip()
                if not text or text[0] not in '{[':
                    last_err = 'not json'
                    continue
                return json.loads(text)
            except Exception as e:
                last_err = str(e)
                continue
        return {}

    def _pic(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            url = 'https:' + url
        return url

    def localProxy(self, param):
        return ''

    def destroy(self):
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
