# -*- coding: utf-8 -*-
# by @嗷呜
import concurrent.futures
import json
import sys
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.ihost=self.imgsite()
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host='https://ev2089.zxbwv.com'

    headers={
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36;webank/h5face;webank/1.0;netType:NETWORK_WIFI;appVersion:416;packageName:com.jp3.xg3',
        'Accept': 'application/json, text/plain, */*',
        'x-requested-with': 'com.jp3.xg3',
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    def imgsite(self):
        data=self.fetch(f"{self.host}/api/appAuthConfig",headers=self.headers).json()
        host=data['data']['imgDomain']
        return host if host.startswith('http') else f"https://{host}"

    def getfts(self,id):
        data=self.fetch(f"{self.host}/api/crumb/filterOptions",params={'fcate_pid':id},headers=self.headers).json()
        fts=[{
            'key': i['key'],
            'name':i['key'],
            'value': [{
                'n': j['name'],
                'v': j['id']
            } for j in i['data']]
        } for i in data['data']]
        return id,fts

    def build_cl(self,data,tid=''):
        videos=[]
        for i in data:
            text=json.dumps(i.get('res_categories',[]))
            videos.append({
                'vod_id': f"{i.get('id')}@{'67' if json.dumps('短剧') in text and '67' in text else tid}",
                'vod_name': i.get('title'),
                'vod_pic': f"{self.ihost}{i.get('path') or i.get('cover_image') or i.get('thumbnail')}",
                'vod_remarks': i.get('mask'),
                'vod_year': i.get('score'),
            })
        return videos

    def homeContent(self, filter):
        result = {}
        cdata=self.fetch(f"{self.host}/api/term/home_fenlei",headers=self.headers).json()
        hdata=self.fetch(f"{self.host}/api/dyTag/hand_data",params={'category_id':cdata['data'][0]['id']},headers=self.headers).json()
        classes = []
        filters = {}
        for k in cdata['data']:
            if 'abbr' in k:
                classes.append({
                    'type_name': k['name'],
                    'type_id': k['id']
                })
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(classes)) as executor:
            future_to_aid = {
                executor.submit(self.getfts, aid['type_id']): aid['type_id']
                for aid in classes
            }
            for future in concurrent.futures.as_completed(future_to_aid):
                aid = future_to_aid[future]
                try:
                    aid_id, fts = future.result()
                    filters[aid_id] = fts
                except Exception as e:
                    print(f"Error processing aid {aid}: {e}")
        result['class'] = classes
        result['filters'] = filters
        result['list'] = [item for i in hdata['data'].values() for item in self.build_cl(i)]
        return result

    def homeVideoContent(self):
        pass
    def categoryContent(self, tid, pg, filter, extend):
        params={**{'fcate_pid': tid, 'page': pg}, **extend}
        path= '/api/crumb/shortList' if tid=='67' else '/api/crumb/list'
        data=self.fetch(f"{self.host}{path}",params=params,headers=self.headers).json()
        result = {}
        result['list'] = self.build_cl(data['data'],tid)
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        ids=ids[0].split('@')
        path, ikey = ('/api/detail', 'vid') if ids[-1] == '67' else ('/api/video/detailv2', 'id')
        data=self.fetch(f"{self.host}{path}",params={ikey:ids[0]},headers=self.headers).json()
        v=data['data']
        if ids[-1]=='67':
            pdata=v.get('playlist',[])
            n,p=[pdata[0].get('source_config_name')],['#'.join([f"{i.get('title')}${i['url']}" for i in pdata])]
        else:
            n,p=[],[]
            for i in v.get('source_list_source',[]):
                n.append(i.get('name'))
                p.append('#'.join([f"{j.get('source_name') or j.get('weight')}${j['url']}" for j in i.get('source_list',[])]))

        vod = {
            'type_name': '/'.join([i.get('name') for i in v.get('types',[])]),
            'vod_year': v.get('year'),
            'vod_area': v.get('area'),
            'vod_remarks': v.get('update_cycle'),
            'vod_actor': '/'.join([i.get('name') for i in v.get('actors',[])]),
            'vod_content': v.get('description'),
            'vod_play_from': '$$$'.join(n),
            'vod_play_url': '$$$'.join(p)
        }
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.fetch(f"{self.host}/api/v2/search/videoV2",params={'key':key,'page':pg,'pageSize':20},headers=self.headers).json()
        return {'list':self.build_cl(data['data']),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        return  {'parse': 0, 'url': id, 'header': {'User-Agent':self.headers['User-Agent']}}

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass
