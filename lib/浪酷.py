# -*- coding: utf-8 -*-
# by @嗷呜
import json
import sys
import time
import requests
from base64 import b64decode, b64encode
from Crypto.Hash import MD5
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host='http://v.lkuys.cn'

    headers = {
        'User-Agent': 'okhttp-okgo/jeasonlzy',
        'Accept-Language': 'zh-CN,zh;q=0.8'
    }

    def homeContent(self, filter):
        data=requests.post(f'{self.host}/v3/type/top_type',headers=self.headers,files=self.getfiles({'': (None, '')})).json()
        result = {}
        classes = []
        filters = {}
        for k in data['data']['list']:
            classes.append({
                'type_name': k['type_name'],
                'type_id': k['type_id']
            })
            fts = []
            for i,x in k.items():
                if isinstance(x, list) and len(x)>2:
                    fts.append({
                        'name': i,
                        'key': i,
                        'value': [{'n': j, 'v': j} for j in x if j and j!= '全部']
                    })
            if len(fts):filters[k['type_id']] = fts
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data=requests.post(f'{self.host}/v3/type/tj_vod',headers=self.headers,files=self.getfiles({'': (None, '')})).json()
        return {'list':self.getv(data['data']['cai']+data['data']['loop'])}

    def categoryContent(self, tid, pg, filter, extend):
        files = {
            'type_id': (None, tid),
            'limit': (None, '12'),
            'page': (None, pg)
        }
        for k,v in extend.items():
            if k=='extend':k='class'
            files[k] = (None, v)
        data=requests.post(f'{self.host}/v3/home/type_search',headers=self.headers,files=self.getfiles(files)).json()
        result = {}
        result['list'] = self.getv(data['data']['list'])
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data=requests.post(f'{self.host}/v3/home/vod_details',headers=self.headers,files=self.getfiles({'vod_id': (None, ids[0])})).json()
        v=data['data']
        vod = {
            'vod_name': v.get('vod_name'),
            'type_name': v.get('type_name'),
            'vod_year': v.get('vod_year'),
            'vod_area': v.get('vod_area'),
            'vod_remarks': v.get('vod_remarks'),
            'vod_actor': v.get('vod_actor'),
            'vod_director': v.get('vod_director'),
            'vod_content': pq(pq(v.get('vod_content','无') or '无').text()).text()
        }
        n,p=[],[]
        for o,i in enumerate(v['vod_play_list']):
            n.append(f"线路{o+1}({i.get('flag')})")
            c=[]
            for j in i.get('urls'):
                d={'url':j.get('url'),'p':i.get('parse_urls'),'r':i.get('referer'),'u':i.get('ua')}
                c.append(f"{j.get('name')}${self.e64(json.dumps(d))}")
            p.append('#'.join(c))
        vod.update({'vod_play_from':'$$$'.join(n),'vod_play_url':'$$$'.join(p)})
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        files = {
            'limit': (None, '12'),
            'page': (None, pg),
            'keyword': (None, key),
        }
        data=requests.post(f'{self.host}/v3/home/search',headers=self.headers,files=self.getfiles(files)).json()
        return {'list':self.getv(data['data']['list']),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        ids=json.loads(self.d64(id))
        url=ids['url']
        if isinstance(ids['p'],list) and len(ids['p']):
            url=[]
            for i,x in enumerate(ids['p']):
                up={'url':ids['url'],'p':x,'r':ids['r'],'u':ids['u']}
                url.extend([f"解析{i+1}",f"{self.getProxyUrl()}&data={self.e64(json.dumps(up))}"])
        h={}
        if ids.get('r'):
            h['Referer'] = ids['r']
        if ids.get('u'):
            h['User-Agent'] = ids['u']
        return  {'parse': 0, 'url': url, 'header': h}

    def localProxy(self, param):
        data=json.loads(self.d64(param['data']))
        h = {}
        if data.get('r'):
            h['Referer'] = data['r']
        if data.get('u'):
            h['User-Agent'] = data['u']
        res=self.fetch(f"{data['p']}{data['url']}",headers=h).json()
        url=res.get('url') or res['data'].get('url')
        return [302,'video/MP2T',None,{'Location':url}]

    def liveContent(self, url):
        pass

    def getfiles(self, p=None):
        if p is None:p = {}
        t=str(int(time.time()))
        h = MD5.new()
        h.update(f"7gp0bnd2sr85ydii2j32pcypscoc4w6c7g5spl{t}".encode('utf-8'))
        s = h.hexdigest()
        files = {
            'sign': (None, s),
            'timestamp': (None, t)
        }
        p.update(files)
        return p

    def getv(self,data):
        videos = []
        for i in data:
            if i.get('vod_id') and str(i['vod_id']) != '0':
                videos.append({
                    'vod_id': i['vod_id'],
                    'vod_name': i.get('vod_name'),
                    'vod_pic': i.get('vod_pic') or i.get('vod_pic_thumb'),
                    'vod_year': i.get('tag'),
                    'vod_remarks': i.get('vod_remarks')
                })
        return videos

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            return ""

    def d64(self,encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            return ""