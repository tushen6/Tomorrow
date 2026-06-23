# -*- coding: utf-8 -*-
import sys,requests,base64,json,time,re
sys.path.append('..')
from base.spider import Spider as BaseSpider
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.site="https://pinglian.lol"
        self.api_list=self.site+"/api/get_videos.php"
        self.api_pan=self.site+"/api/search_pan_links.php"
        self.username=""
        self.password=""
        self.cookie=""
        self.check_api=""
        self.enable_check=False
        self.ua="Mozilla/5.0 (Linux; Android 16; Pixel 9 Pro Build/BP1A.250305.019) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7743.101 Mobile Safari/537.36"
        self.channels={"1":"电影","2":"电视剧","3":"综艺","4":"动漫"}
        self.session=requests.Session()
        self.session.verify=False
        self.session.headers.update({"User-Agent":self.ua,"X-Requested-With":"XMLHttpRequest","Accept":"*/*","Referer":self.site+"/all-videos.php","Accept-Language":"zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"})
    def getName(self):return "盘链"
    def init(self,extend=""):
        if extend:
            try:
                cfg=json.loads(extend)
                if isinstance(cfg,dict):
                    self.username=cfg.get("username",self.username)
                    self.password=cfg.get("password",self.password)
                    self.cookie=cfg.get("cookie",self.cookie)
                    self.check_api=cfg.get("check_api",self.check_api)
                    self.enable_check=bool(cfg.get("enable_check",self.enable_check)) and bool(self.check_api)
            except Exception:0
        self.session.cookies.set("announcement_dismissed","true",domain="pinglian.lol",path="/")
        if self.cookie:self.session.headers.update({"Cookie":self.cookie})
        elif self.username and self.password:self._login()
        return self
    def destroy(self):self.session.close()
    def _login(self):
        try:
            self.session.get(self.site+"/pages/login.php",timeout=12)
            return bool(self.session.post(self.site+"/api/login.php",data={"username":self.username,"password":self.password,"remember":"on"},timeout=12).json().get("success"))
        except Exception:return False
    def _b64e(self,obj):
        text=obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,separators=(",",":"))
        return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    def _b64d(self,s):
        try:
            text=base64.urlsafe_b64decode((s+"="*(-len(s)%4)).encode()).decode()
            try:return json.loads(text)
            except Exception:return text
        except Exception:return s
    def _safe(self,t):return str(t or "").replace("#","＃").replace("$","￥")
    def _fetch_list(self,t=None,wd=None,page=1):
        p={"pg":page}
        if wd:p["wd"]=wd
        elif t:p["t"]=t
        else:return {"list":[],"page":page,"pagecount":0,"total":0}
        try:
            d=self.session.get(self.api_list,params=p,timeout=15).json()
            if d.get("code")==1:return {"list":d.get("list",[]),"page":d.get("page",page),"pagecount":d.get("pagecount",1),"total":d.get("total",0)}
        except Exception:0
        return {"list":[],"page":page,"pagecount":0,"total":0}
    def _check_links(self,links,disk_type,batch_size=30):
        if not links or not self.check_api:return links
        ok=[]
        for i in range(0,len(links),batch_size):
            b=links[i:i+batch_size]
            try:
                d=requests.post(self.check_api,json={"items":[{"disk_type":disk_type,"url":u} for u in b]},headers={"User-Agent":self.ua,"Accept":"application/json, text/plain, */*"},timeout=15,verify=False).json()
                ok.extend([x.get("url","") for x in d.get("results",[]) if x.get("state")=="ok" and x.get("url")])
            except Exception:ok.extend(b)
        return ok
    def _pan_url(self,x):return x.get("url","") or (self.site+"/api/go.php?t="+x.get("token","") if x.get("token") else "")
    def _process_disk(self,k,v):
        links=v.get("links",[]) if isinstance(v,dict) else []
        raw,seen=[],set()
        for x in links:
            u=self._pan_url(x)
            if u and u not in seen:raw.append(u);seen.add(u)
        if not raw:return None,None
        valid=raw if not self.enable_check or k in {"others","guangya"} else self._check_links(raw,k)
        if not valid:return None,None
        s=set(valid);eps=[]
        for x in links:
            u=self._pan_url(x)
            if u not in s:continue
            pwd=x.get("password","")
            if pwd and "pwd=" not in u and "password=" not in u:u+=("&" if "?" in u else "?")+"pwd="+str(pwd)
            eps.append(self._safe(x.get("title") or v.get("name") or k)+"$"+self._b64e(u))
        if not eps:return None,None
        eps.insert(0,"点击选择$noop")
        return v.get("name",k),"#".join(eps)
    def _fetch_pan_links(self,name,vid):
        try:
            d=self.session.get(self.api_pan,params={"keyword":name,"vod_id":vid,"_t":int(time.time()*1000)},timeout=20).json()
            if not d.get("success"):return "",""
            pan=d.get("data",{})
            order=["quark","uc","xunlei","aliyun","baidu","115","123","tianyi","others"]
            items=[]
            for k in order:
                if k in pan:items.append((k,pan.pop(k)))
            items.extend(pan.items())
            fs,us=[],[]
            for k,v in items:
                f,u=self._process_disk(k,v)
                if f and u:fs.append(f);us.append(u)
            return "$$$".join(fs),"$$$".join(us)
        except Exception:return "",""
    def _vod(self,x):return {"vod_id":self._b64e(x),"vod_name":x.get("vod_name",""),"vod_pic":x.get("vod_pic",""),"vod_remarks":x.get("vod_remarks","") or x.get("type_name","")}
    def homeContent(self,filter):return {"class":[{"type_name":v,"type_id":k} for k,v in self.channels.items()],"list":[],"filters":{}}
    def homeVideoContent(self):
        r=self._fetch_list(t="1",page=1)
        return {"list":[self._vod(x) for x in r.get("list",[])[:12]]}
    def categoryContent(self,tid,pg,filter,extend):
        if tid not in self.channels:return {"list":[],"page":1,"pagecount":0,"limit":30,"total":0}
        page=int(pg) if str(pg).isdigit() else 1
        r=self._fetch_list(t=tid,page=page)
        return {"list":[self._vod(x) for x in r.get("list",[])],"page":page,"pagecount":r.get("pagecount",0),"limit":30,"total":r.get("total",0)}
    def searchContent(self,key,quick,pg="1"):
        page=int(pg) if str(pg).isdigit() else 1
        if not key:return {"list":[],"page":page,"pagecount":0,"limit":30,"total":0}
        r=self._fetch_list(wd=key,page=page)
        return {"list":[self._vod(x) for x in r.get("list",[])],"page":page,"pagecount":r.get("pagecount",0),"limit":30,"total":r.get("total",0)}
    def detailContent(self,ids):
        x=self._b64d(ids[0])
        if not isinstance(x,dict):return {"list":[]}
        name=x.get("vod_name","")
        fs,us=[],[]
        pf=x.get("vod_play_from","");pu=x.get("vod_play_url","")
        if pf and pu:fs.append(pf);us.append(pu)
        pan_f,pan_u=self._fetch_pan_links(name,x.get("vod_id")) if name and x.get("vod_id") is not None else ("","")
        if pan_f and pan_u:fs.append(pan_f);us.append(pan_u)
        if not fs:fs,us=["提示"],["需要有效登录或暂无资源$noop"]
        return {"list":[{"vod_id":ids[0],"vod_name":name,"vod_pic":x.get("vod_pic",""),"vod_year":x.get("vod_year",""),"vod_area":x.get("vod_area",""),"vod_actor":x.get("vod_actor",""),"vod_director":x.get("vod_director",""),"vod_content":x.get("vod_content",""),"vod_remarks":(str(x.get("vod_remarks",""))+" "+str(x.get("vod_score",""))).strip(),"vod_play_from":"$$$".join(fs),"vod_play_url":"$$$".join(us)}]}
    def _real_pan_url(self,u):
        if not isinstance(u,str) or "api/go.php" not in u:return u
        try:
            r=self.session.get(u,timeout=12,allow_redirects=True)
            m=re.search("https?://(?:pan\\.quark\\.cn|drive\\.uc\\.cn|pan\\.baidu\\.com|www\\.aliyundrive\\.com|www\\.alipan\\.com|alipan\\.com|cloud\\.189\\.cn|www\\.123pan\\.com|123pan\\.com|pan\\.xunlei\\.com|115\\.com)[^\\s\"\'<>]+",r.text)
            return m.group(0).replace("&amp;","&") if m else u
        except Exception:return u
    def playerContent(self,flag,id,vipFlags):
        if not id or id=="noop":return {"parse":0,"jx":0,"url":""}
        u=self._b64d(id)
        if isinstance(u,dict):u=u.get("url","")
        if not isinstance(u,str):return {"parse":0,"jx":0,"url":""}
        u=self._real_pan_url(u)
        pans=["pan.quark.cn","drive.uc.cn","pan.baidu.com","aliyundrive.com","alipan.com","cloud.189.cn","123pan.com","pan.xunlei.com","115.com"]
        if any(x in u for x in pans):return {"parse":0,"jx":0,"url":"push://"+u,"header":{"User-Agent":self.ua,"Referer":self.site+"/"}}
        if u.startswith("magnet:"):return {"parse":0,"jx":0,"url":u}
        if ".m3u8" in u or ".mp4" in u:return {"parse":0,"jx":0,"url":u,"header":{"User-Agent":self.ua}}
        if u.startswith("http"):return {"parse":0,"jx":0,"url":"push://"+u,"header":{"User-Agent":self.ua,"Referer":self.site+"/"}}
        return {"parse":0,"jx":0,"url":""}
