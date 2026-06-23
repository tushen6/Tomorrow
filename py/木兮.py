# -*- coding: utf-8 -*-
# by @嗷呜
import base64
import sys
from pprint import pprint

import hmac
import hashlib
import secrets
import time
import uuid
import json
import random
import string
from urllib.parse import quote

import requests
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import pad
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend='{}'):
        self.session = requests.session()
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host='https://film.symx.club'
    RSA_N = "c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74c7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b59706592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
    RSA_E = 65537
    STATIC_BASE = "https://static.geetest.com/"
    VERIFY_HOST = 'https://gcaptcha4.geetest.com'
    ClientId=MD5.new(str(int(time.time())).encode()).hexdigest();Token=''

    def rsa_encrypt(self,random_key):
        pub_key = RSA.construct((int(self.RSA_N, 16), self.RSA_E))
        cipher = PKCS1_v1_5.new(pub_key)
        return cipher.encrypt(random_key.encode('utf-8')).hex()

    def aes_encrypt(self,plaintext, key):
        iv = b"0000000000000000"
        cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv)
        padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
        return cipher.encrypt(padded_data).hex()

    def get_w(self, payload_dict):
        random_key = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        json_str = json.dumps(payload_dict, separators=(',', ':'))
        return self.aes_encrypt(json_str, random_key) + self.rsa_encrypt(random_key)

    def get_dynamic_payload(self,lot_number, set_left, passtime, captcha_id, pow_detail):
        key_name = lot_number[26:30] + lot_number[12:16]
        sub_key = lot_number[16:24]
        val = lot_number[6:10]
        pow_msg = f"1|0|md5|{pow_detail['datetime']}|{captcha_id}|{lot_number}||{secrets.token_hex(8) }"
        pow_sign = hashlib.md5(pow_msg.encode()).hexdigest()
        payload = {
            "setLeft": set_left,
            "passtime": passtime,
            "userresponse": set_left / 1.0059466666666665 +2,
            "device_id": "",
            "lot_number": lot_number,
            "pow_msg": pow_msg,
            "pow_sign": pow_sign,
            "geetest": "captcha",
            "lang": "zh",
            "ep": "123",
            "biht": "1426265548",
            "yDWL": "hZGx",
            key_name: {sub_key: val},
            "em": {"ph": 0, "cp": 0, "ek": "11", "wd": 1, "nt": 0, "si": 0, "sc": 0}
        }
        return payload

    def generate_checksum_timestamp(self):
        r = str(int(time.time() * 1000))
        prefix = r[:-1]
        digit_sum = sum(int(d) for d in prefix)
        check_digit = digit_sum % 10
        return prefix + str(check_digit)

    def get_site_headers(self,path, end=0):
        secret_key = "lslx_sk"
        timestamp = self.generate_checksum_timestamp()
        raw_data = f"{timestamp}symx_{secret_key}{path}"
        arranged = raw_data.replace("1", "i").replace("0", "o").replace("5", "s")
        if end:
            secret_key = ''
            arranged = ''
        signature = hmac.new(
            secret_key.encode('utf-8'),
            arranged.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        header = {
            'User-Agent': 'SYMX_ANDROID',
            'user-agent': 'Mozilla/5.0 (Linux; Android 13; M2012K10C Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/30.545454)',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Platform': 'android',
            'X-Timestamp': timestamp,
            'X-Sign-X': signature,
            'X-Client-Id':self.ClientId,
            'Referer': 'https://film.symx.club/',
        }
        if self.Token: header['X-Verify-Token'] = self.Token
        if end:
            del header['X-Sign-X']
            header['X-Report-Id'] = signature
        return header

    def run_verify(self,i=0):
        if i>3: return
        try:
            config = self.session.get(f'{self.host}/api/auth/verify/config',
                                 headers=self.get_site_headers('/auth/verify/config')).json()
            captcha_id = config['data']['captchaId']
            params = {
                'callback': f'geetest_{int(time.time()* 1000)}',
                'captcha_id': captcha_id,
                'challenge': str(uuid.uuid4()),
                'client_type': 'web',
                'lang': 'zho',
            }
            load_res = self.fetch(f'{self.VERIFY_HOST}/load', params=params).text
            data = json.loads(load_res[len(params['callback']) + 1:-1])['data']
            t=str(int(time.time() * 1000))
            heade={
                'timestamp':t,
                "sign":MD5.new(f'44344434tffrfeeffgdggdg{t}'.encode()).hexdigest()
            }

            body={
                'type':'solve',
                'bg':base64.b64encode(self.fetch(f"{self.STATIC_BASE}{data['bg']}").content).decode(),
                'hb':base64.b64encode(self.fetch(f"{self.STATIC_BASE}{data['slice']}").content).decode(),
            }
            resp=self.post("http://mytv6688.xyz/aowuapp",json=body,headers=heade).json()
            print("验证结果1：", resp)
            pass_time = random.randint(1200, 2200)
            inner_payload = self.get_dynamic_payload(data['lot_number'], resp["result"], pass_time, captcha_id,
                                                                data['pow_detail'])
            verify_params = {
                "callback": f"geetest_{int(time.time() * 1000)}",
                "captcha_id": captcha_id,
                "client_type": "web",
                "lot_number": data['lot_number'],
                "payload": data['payload'],
                "process_token": data['process_token'],
                "payload_protocol": data['payload_protocol'],
                "pt": data['pt'],
                "w": self.get_w(inner_payload)
            }
            verify_res_raw = self.fetch(f'{self.VERIFY_HOST}/verify', params=verify_params).text
            print("验证结果2：", verify_res_raw)
            verify_data = json.loads(verify_res_raw[len(verify_params['callback']) + 1:-1])
            sc = verify_data['data']['seccode']
            json_body = {
                "captchaId": sc['captcha_id'],
                "captchaOutput": sc['captcha_output'],
                "genTime": int(sc['gen_time']),
                "lotNumber": sc['lot_number'],
                "passToken": sc['pass_token']
            }
            final_res = self.session.post(f'{self.host}/api/auth/verify', headers=self.get_site_headers("/auth/verify"),
                                          json=json_body)
            print("验证结果3：", final_res.text)
            self.Token = final_res.json()["data"]["token"]
        except  Exception as e:
            print(e)
            return self.run_verify(i+1)

    def Req(self,path,params,i=0):
        self.session.headers.update(self.get_site_headers(path.split("/api")[-1], i))
        resp=self.session.get(f"{self.host}{path}",params=params)
        if '完成验证' in resp.text:
            self.run_verify()
            self.session.headers.update(self.get_site_headers(path.split("/api")[-1], i))
            resp = self.session.get(f"{self.host}{path}",params=params)
        print(resp.status_code)
        # print(resp.text)
        return resp.json()

    def homeContent(self, filter):
        data=self.Req("/api/category/top",{},1)
        result = {}
        classes = []
        for k in data['data']:
            classes.append({
                'type_name': k['name'],
                'type_id': k['id']
            })
            # fil = []
            # resp=self.Req("/api/film/category/filter",{'categoryId':k['id']},1)
            # for i,v in resp['data'].items():
            #     if not isinstance(v,list) or len(v)==0 or i=='sortOptions':continue
            #     fil.append({
            #         'key': i,
            #         'name': i,
            #         'value': [{'n':x,'v':x} for x in v]
            #     })
            # fil.append(self.ddd)
            # filters[k['id']] = fil
        result['class'] = classes
        result['filters'] = self.fetch("http://mytv6688.xyz/pyplugin/木兮筛选.json").json()
        return result

    def homeVideoContent(self):
        data=self.Req("/api/poster/list",{},1)
        vlist = []
        for k in data['data']:
            vlist.append({
                'vod_id': k.get('filmId'),
                'vod_name': k.get('filmName'),
                'vod_pic': k.get('poster'),
            })
        return {'list':vlist}

    def getList(self,data):
        vlist = []
        for k in data:
            vlist.append({
                'vod_id': k.get('id'),
                'vod_name': k.get('name'),
                'vod_pic': k.get('cover'),
                'vod_remarks': k.get('updateStatus'),
            })
        return vlist

    def categoryContent(self, tid, pg, filter, extend):
        params={
          "area": extend.get('areaOptions', ''),
          "childCategoryId": "",
          "categoryId": tid,
          "language": extend.get('languageOptions', ''),
          "pageNum": pg,
          "pageSize": "10",
          "sort": extend.get('sortOptions', ''),
          "year": extend.get('yearOptions', '')
        }
        resp=self.Req("/api/film/category/list", params)
        result = {}
        result['list'] =self.getList(resp['data']['list'])
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        resp=self.Req("/api/film/detail/play/app",{'id': ids[0]})
        v=resp['data']
        n,p=[],[]
        for i in v.get('playLineList'):
            n.append(i['playerName'])
            m=[f"{j['name']}${j['id']}" for j in i.get('lines')]
            p.append('#'.join(m))
        vod = {
            'type_name': v.get('categoryName'),
            'vod_year': v.get('year'),
            'vod_area': v.get('area'),
            'vod_remarks': v.get('updateStatus'),
            'vod_actor': v.get('actor'),
            'vod_director': '云霄仙子（困困版）',
            'vod_content': v.get('blurb'),
            'vod_play_from': '$$$'.join(n),
            'vod_play_url': '$$$'.join(p)
        }
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        params={
          "pageNum": pg,
          "pageSize": "10",
          "keyword": key
        }
        resp=self.Req('/api/film/search',params=params)
        return {'list':self.getList( resp['data']['list']),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        resp=self.Req("/api/line/play/parse", {"lineId": id})
        return  {'parse': 0, 'url': resp['data'], 'header': ''}

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass


if __name__ == "__main__":
    sp = Spider()
    formatJo = sp.init()
    formatJo = sp.homeContent(False)  # 主页，等于真表示启用筛选
    # formatJo = sp.homeVideoContent()  # 主页视频
    # formatJo = sp.searchContent("斗罗",False,'1') # 搜索{"area":"大陆","by":"hits","class":"国产","lg":"国语"}
    # formatJo = sp.categoryContent('2', '1', False, {})  # 分类
    # formatJo = sp.detailContent(['126634'])  # 详情
    # formatJo = sp.playerContent("","https://www.yingmeng.net/vodplay/140148-2-1.html",{}) # 播放
    # formatJo = sp.localProxy({"":"https://www.yingmeng.net/vodplay/140148-2-1.html"}) # 播放
    pprint(formatJo)
