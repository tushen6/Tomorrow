# -*- coding: utf-8 -*-
"""
================================================================================
 小山影视源 · CatVod / Box  Python Spider
================================================================================
 后端   : http://43.248.128.122:578
 账号   : sukeke / sukeke.1   (已内置,可在 init 参数中覆盖)
 依赖   : requests (无则退回 urllib)

 已完整验证的链路
 ----------------------------------------------------------------------------
  1. 登录       POST /api/v1/user/login      {"Username","Password","device_id"}
  2. 密钥交换   GET  /api/v1/security/challenge  →  POST /api/v1/security/init
                → session_id + sign_key
  3. 列表/搜索  GET  /api/v1/search?wd=*&type=<分类>&page=<页>
                → data.hits[]   (wd=* 为通配,配合 type 即分类全量)
  4. 详情       GET  /api/v1/video/detail?id=<vod_id>
                → data.vod_info.vod_url_with_player[]  每条线路带 tk 票根
  5. 换票       POST /api/v1/vod/ticket       body {"token": "<tk完整值>"}
                → data.ticket  (play_ticket, 内含 parse_api / data.url / 有效期)
  6. 取流       按 parse_api 分三种形态解析:
                 · 相对路径  /api/v1/vod/parse?code=..&t=..&url=
                        → 拼 BASE 后 GET,服务端直接吐播放地址
                 · 外部解析  https://.../json_api.php?key=..&vid={md5}
                        → {md5} 用 data.url 替换,返回 JSON 取 url
                 · 外部解析  https://.../api/?key=..&url=
                        → url= 后拼 data.url,返回 JSON 取 url
  7. 推荐       GET  /api/v1/video/recommend?id=<vod_id>

 注意:device_id 必须与账号已绑定的设备一致(每个新 device_id 占一个设备配额,
      超了会报"设备数量已达上限")。下方已预置可用设备号。
================================================================================
"""
import json
import time
import uuid
import base64
import hashlib
import hmac
import urllib.parse
import os
import random

try:
    import requests
except Exception:
    requests = None


try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

        def getName(self):
            return ""

        def isVideoFormat(self, url):
            return False

        def manualVideoCheck(self):
            return False

        def destroy(self):
            pass

        def localProxy(self, param):
            return None


# 已实测的分类表(type_id -> 名称)。search 接口有严格限流,
# 分类探测会连发数十次请求必然触发风控,因此默认直接使用本表,不做在线探测。
KNOWN_TYPES = [
    (1, "电影"), (2, "连续剧"), (3, "综艺"), (4, "动漫"),
    (20, "短剧"), (21, "少儿"), (22, "漫剧"), (23, "纪录片"),
]

# init 接口的服务端要求字段(只校验存在性,不校验取值)
_INIT_FILLER = {
    "sign": "s", "signature": "s", "app_id": "1", "app_key": "1",
    "app_version": "1.0", "version": "1", "platform": "android",
    "device": "android", "version_code": 1, "uid": "1",
    "source_id": "1", "site_id": "1", "type": "1",
}


class Spider(BaseSpider):
    CONFIG = {
        "base": "http://43.248.128.122:578",
        "username": "sukeke",
        "password": "sukeke.1",
        # 账号 sukeke 已绑定的设备号,换账号请改成自己的
        "device_id": "de94cd65-a825-4972-adf9-7dbece13e9f1",
        "timeout": 30,
        "user_agent": "Mozilla/5.0 (Linux; Android 12) okhttp/3.12.1",
        "page_size": 20,
        "auto_fallback": 1,   # 当前线路解析失败时自动降级到其它可用线路
    }

    def __init__(self):
        super().__init__()
        self.cfg = dict(self.CONFIG)
        self.base = self.CONFIG["base"].rstrip("/")
        self.device_id = ""
        self.jwt = ""
        self.session_id = ""
        self.sign_key = ""
        self._types = []
        self._http = None
        self._lines = []          # 上次详情里的线路顺序(用于降级)
        self._tkmap = {}          # tk -> {"name","code","ep"} 索引

    # ================================================================= 基础
    def getName(self):
        return "小山"

    def init(self, extend=""):
        self.cfg = dict(self.CONFIG)
        if isinstance(extend, dict):
            self.cfg.update(extend)
        elif isinstance(extend, str) and extend.strip():
            try:
                self.cfg.update(json.loads(extend))
            except Exception:
                for kv in str(extend).split(","):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        self.cfg[k.strip()] = v.strip()

        self.base = str(self.cfg["base"]).rstrip("/")
        self.device_id = str(self.cfg.get("device_id") or "").strip()
        if not self.device_id:
            self.device_id = uuid.uuid4().hex.upper()
            self._save_device_id(self.device_id)

        self._http = requests.Session() if requests else None
        if self._http:
            self._http.headers.update({"User-Agent": self.cfg.get("user_agent", "okhttp/3.12.1")})

        try:
            self._ensure_session()
        except Exception:
            pass

    def _save_device_id(self, did):
        for p in ("/sdcard/.xiaoshan_did", "/storage/emulated/0/.xiaoshan_did"):
            try:
                with open(p, "w") as f:
                    f.write(did)
                return
            except Exception:
                continue

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv", ".ts", "cmecloud", "apdcdn"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if self._http:
                self._http.close()
        except Exception:
            pass

    def localProxy(self, param):
        return [404, "text/plain", "", None]

    # ================================================================= HTTP
    def _headers(self, extra=None):
        h = {"User-Agent": self.cfg.get("user_agent", "okhttp/3.12.1")}
        if self.jwt:
            h["Authorization"] = "Bearer " + self.jwt
        if self.session_id:
            h["X-Session-Id"] = self.session_id
        if extra:
            h.update(extra)
        return h

    def _get(self, path, params=None, headers=None, timeout=None):
        url = path if path.startswith("http") else self.base + path
        t = timeout or self.cfg.get("timeout", 20)
        try:
            if self._http:
                r = self._http.get(url, headers=self._headers(headers), params=params, timeout=t)
            else:
                q = ("?" + urllib.parse.urlencode(params)) if params else ""
                req = urllib.request.Request(url + q, headers=self._headers(headers))
                r = urllib.request.urlopen(req, timeout=t)
                body = r.read().decode("utf-8", "replace")
                return json.loads(body)
            return r.json()
        except Exception as e:
            return {"code": 0, "msg": "请求失败: %s" % e}

    def _post(self, path, payload, headers=None, timeout=None):
        url = path if path.startswith("http") else self.base + path
        t = timeout or self.cfg.get("timeout", 20)
        hh = self._headers(headers)
        hh["Content-Type"] = "application/json"
        try:
            if self._http:
                r = self._http.post(url, json=payload, headers=hh, timeout=t)
            else:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers=hh)
                r = urllib.request.urlopen(req, timeout=t)
                body = r.read().decode("utf-8", "replace")
                return json.loads(body)
            return r.json()
        except Exception as e:
            return {"code": 0, "msg": "请求失败: %s" % e}

    def _get_text(self, url, headers=None, timeout=None, retry=2):
        """带 Referer + 重试的 GET(外部解析接口冷启动较慢)"""
        t = timeout or self.cfg.get("timeout", 30)
        hh = self._headers(headers)
        hh.setdefault("Referer", "https://www.google.com/")
        last = ""
        for i in range(max(1, retry)):
            try:
                if self._http:
                    r = self._http.get(url, headers=hh, timeout=t)
                    return r.status_code, r.text
                req = urllib.request.Request(url, headers=hh)
                resp = urllib.request.urlopen(req, timeout=t)
                return resp.getcode(), resp.read().decode("utf-8", "replace")
            except Exception as e:
                last = str(e)
                if i < retry - 1:
                    time.sleep(1.2)
        return 0, last

    # ================================================================= 会话
    def _login(self):
        r = self._post("/api/v1/user/login", {
            "Username": self.cfg.get("username"),
            "Password": self.cfg.get("password"),
            "device_id": self.device_id,
        })
        if r.get("code") == 1 and isinstance(r.get("data"), dict):
            t = r["data"].get("token")
            if t:
                self.jwt = t
                return True
        return False

    def _handshake(self):
        ch = self._get("/api/v1/security/challenge")
        if ch.get("code") != 1 or not isinstance(ch.get("data"), dict):
            return False
        challenge = ch["data"].get("challenge")
        cid = ch["data"].get("challenge_id")
        if not challenge or not cid:
            return False

        payload = {
            "challenge": challenge,
            "challenge_id": cid,
            "device_id": self.device_id,
            "token": self.jwt,
            "client_token": "",
            "timestamp": int(time.time()),
            "nonce": uuid.uuid4().hex,
            "username": self.cfg.get("username"),
            "password": self.cfg.get("password"),
        }
        payload.update(_INIT_FILLER)

        r = self._post("/api/v1/security/init", payload)
        if r.get("code") == 1 and isinstance(r.get("data"), dict):
            self.session_id = r["data"].get("session_id") or ""
            self.sign_key = r["data"].get("sign_key") or ""
            return bool(self.session_id)
        return False

    def _ensure_session(self):
        if not self.jwt and not self._login():
            return False
        if not self.session_id and not self._handshake():
            return False
        return True

    def _sign_headers(self, path, body=""):
        """基于 sign_key 的设备签名(服务端 sign_policy=observe,属扩展用途)"""
        if not self.sign_key:
            return {}
        try:
            key = bytes.fromhex(self.sign_key)
        except Exception:
            return {}
        ts = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        msg = (ts + nonce + path + (body or "")).encode("utf-8")
        sg = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return {"X-Timestamp": ts, "X-Nonce": nonce, "X-Sign": sg,
                "X-Device-Sign": sg, "X-Device-Id": self.device_id}

    # ================================================================= 分类
    def _detect_types(self):
        """遍历 type 自动发现分类表"""
        found = []
        for tid in list(range(1, 31)) + [40, 50, 60, 99]:
            try:
                r = self._get("/api/v1/search", params={"wd": "*", "type": tid, "page": 1})
            except Exception:
                continue
            if r.get("code") != 1:
                continue
            hits = ((r.get("data") or {}).get("hits")) or []
            if not hits:
                continue
            h0 = hits[0]
            if h0.get("type_id") and h0.get("type_name"):
                found.append((int(h0["type_id"]), str(h0["type_name"])))
        if found:
            self._types = sorted(set(found))
        return self._types

    def homeContent(self, filter):
        self._ensure_session()
        if not self._types:
            self._types = list(KNOWN_TYPES)
        classes = [{"type_id": str(t), "type_name": n} for t, n in self._types]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        try:
            return self.categoryContent(self._types[0][0] if self._types else "1", 1, False, {})
        except Exception:
            return {"list": []}

    # ================================================================= 列表
    def _search(self, wd, page=1, type_id=None):
        """search 接口限流较严,遇"请求过于频繁"自动退避重试"""
        params = {"wd": wd, "page": page}
        if type_id:
            params["type"] = type_id
        delays = [0, 2.5, 5, 9, 15]
        r = {"code": 0}
        for i, d in enumerate(delays):
            if d:
                time.sleep(d)
            r = self._get("/api/v1/search", params=params)
            if r.get("code") == 1:
                break
            msg = str(r.get("msg") or "")
            if "频繁" not in msg and "rate" not in msg.lower():
                break
        if r.get("code") != 1:
            return [], 1, 0
        data = r.get("data") or {}
        hits = data.get("hits") or []
        total = int(data.get("total") or 0)
        pages = int(data.get("total_pages") or 1)
        return hits, pages, total

    @staticmethod
    def _item(it):
        return {
            "vod_id": str(it.get("vod_id") or ""),
            "vod_name": str(it.get("vod_name") or ""),
            "vod_pic": str(it.get("vod_pic") or ""),
            "vod_remarks": str(it.get("vod_remarks") or ""),
            "vod_year": str(it.get("vod_year") or ""),
            "vod_area": str(it.get("vod_area") or ""),
            "vod_class": str(it.get("vod_class") or ""),
            "vod_actor": str(it.get("vod_actor") or ""),
            "vod_director": str(it.get("vod_director") or ""),
            "vod_content": str(it.get("vod_blurb") or it.get("vod_content") or ""),
        }

    def categoryContent(self, tid, pg, filter, extend):
        self._ensure_session()
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        hits, pages, total = self._search("*", pg, str(tid))
        lst = [self._item(it) for it in hits]
        return {"list": lst, "page": pg, "pagecount": pages,
                "limit": self.cfg.get("page_size", 20), "total": total}

    def searchContent(self, key, quick, pg="1"):
        self._ensure_session()
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        hits, pages, total = self._search(str(key), pg)
        lst = [self._item(it) for it in hits]
        return {"list": lst, "page": pg, "pagecount": pages, "total": total}

    # ================================================================= 详情
    def detailContent(self, ids):
        self._ensure_session()
        if not ids:
            return {"list": []}
        vid = str(ids[0]).split(",")[0]
        path = "/api/v1/video/detail"
        r = self._get(path, headers=self._sign_headers(path), params={"id": vid})
        if r.get("code") != 1 or not isinstance(r.get("data"), dict):
            return {"list": []}
        vi = r["data"].get("vod_info") or {}

        play_from, play_url, self._lines = [], [], []
        self._tkmap = {}
        for idx, line in enumerate(vi.get("vod_url_with_player") or []):
            name = str(line.get("name") or "")
            code = str(line.get("code") or "")
            eps, tks = [], []
            for ep_i, seg in enumerate(str(line.get("url") or "").split("#")):
                if not seg:
                    continue
                if "$" in seg:
                    ep_name, tk = seg.split("$", 1)
                else:
                    ep_name, tk = seg, ""
                if not ep_name:
                    continue
                # 播放 id: 线路码|tk票根
                eps.append(ep_name + "$" + code + "|" + tk)
                tks.append(tk)
                self._tkmap[tk] = {"name": name, "code": code, "ep": ep_i}
            if not eps:
                continue
            self._lines.append({"index": idx, "name": name, "code": code, "tks": tks})
            play_from.append(name or code)
            play_url.append("#".join(eps))

        if not play_url and vi.get("vod_play_url"):
            play_from = [vi.get("vod_play_from") or "线路"]
            play_url = [vi.get("vod_play_url")]

        return {"list": [{
            "vod_id": vid,
            "vod_name": str(vi.get("vod_name") or ""),
            "vod_pic": str(vi.get("vod_pic") or ""),
            "vod_actor": str(vi.get("vod_actor") or ""),
            "vod_director": str(vi.get("vod_director") or ""),
            "vod_year": str(vi.get("vod_year") or ""),
            "vod_area": str(vi.get("vod_area") or ""),
            "vod_lang": str(vi.get("vod_lang") or ""),
            "vod_class": str(vi.get("vod_class") or ""),
            "vod_state": str(vi.get("vod_state") or ""),
            "vod_total": str(vi.get("vod_total") or ""),
            "vod_serial": str(vi.get("vod_serial") or ""),
            "vod_remarks": str(vi.get("vod_remarks") or ""),
            "vod_content": str(vi.get("vod_content") or vi.get("vod_blurb") or ""),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]}

    # ================================================================= 播放
    def _decode_ticket(self, ticket):
        """play_ticket 第一段是 base64url 明文 JSON"""
        try:
            seg = ticket.split(".")[0]
            seg += "=" * (-len(seg) % 4)
            return json.loads(base64.urlsafe_b64decode(seg).decode("utf-8", "replace"))
        except Exception:
            return None

    def _ticket(self, tk):
        """tk -> play_ticket"""
        r = self._post("/api/v1/vod/ticket", {"token": tk},
                       headers=self._sign_headers("/api/v1/vod/ticket"))
        if r.get("code") == 1 and isinstance(r.get("data"), dict):
            return r["data"].get("ticket")
        return None

    def _resolve(self, tk):
        """play_ticket -> 真实播放地址"""
        ticket = self._ticket(tk)
        if not ticket:
            return None, "换票失败"
        pl = self._decode_ticket(ticket)
        if not pl:
            return None, "票据解析失败"
        d = pl.get("data") or {}
        api = str(d.get("parse_api") or "").replace("\\u00026", "&")
        du = str(d.get("url") or "")
        if not api or not du:
            return None, "无解析配置"

        # ① 服务端本地解析(相对路径)
        if api.startswith("/"):
            full = self.base + api + urllib.parse.quote(du, safe="")
            code, text = self._get_text(full)
            j = self._try_json(text)
            if isinstance(j, dict):
                if j.get("url"):
                    return j["url"], ""
                msg = str(j.get("system") or j.get("msg") or "解析失败")
                return None, msg
            if code == 200 and text.startswith("http"):
                return text.strip(), ""
            return None, "解析失败(%s)" % code

        # ② 外部解析接口
        if "{md5}" in api:
            target = api.replace("{md5}", du)
        elif "url=" in api:
            target = api + urllib.parse.quote(du, safe="")
        else:
            target = api + du
        code, text = self._get_text(target)
        j = self._try_json(text)
        if isinstance(j, dict):
            if j.get("url"):
                return j["url"], ""
            return None, str(j.get("msg") or "外部解析失败")
        if code == 200 and text.startswith("http"):
            return text.strip(), ""
        return None, "外部解析失败(%s)" % code

    @staticmethod
    def _try_json(text):
        try:
            t = (text or "").strip()
            if t.startswith("{") or t.startswith("["):
                return json.loads(t)
        except Exception:
            return None
        return None

    def playerContent(self, flag, id, vipFlags=None):
        self._ensure_session()
        if not id:
            return {"parse": 0, "url": "", "header": {}}
        code, tk = "", id
        if "|" in id:
            code, tk = id.split("|", 1)

        # 1) 优先按当前线路解析
        url, err = self._resolve(tk)

        # 2) 当前线路失败(付费/失效/超时)→ 自动降级到其它线路的同一集
        if not url and self.cfg.get("auto_fallback", 1):
            cur = self._tkmap.get(tk) or {}
            ep = cur.get("ep", 0)
            for ln in self._lines:
                if ln.get("code") == code:
                    continue
                tks = ln.get("tks") or []
                if ep >= len(tks):
                    continue
                u2, _e2 = self._resolve(tks[ep])
                if u2:
                    url = u2
                    err = ""
                    break

        if url:
            return {"parse": 0, "url": url, "header": {
                "User-Agent": self.cfg.get("user_agent", "okhttp/3.12.1"),
                "Referer": "https://www.google.com/",
            }}
        return {"parse": 0, "url": "", "header": {}, "msg": err or "播放失败"}


if __name__ == "__main__":
    s = Spider()
    s.init("")
    print("name    :", s.getName())
    print("device  :", s.device_id)
    print("jwt     :", (s.jwt or "")[:36], "...")
    print("session :", s.session_id)

    h = s.homeContent(False)
    print("\n分类    :", [(c["type_id"], c["type_name"]) for c in h.get("class", [])])

    c = s.categoryContent("2", 1, False, {})
    print("连续剧  :", len(c.get("list", [])), "条 / 共", c.get("total"))
    if c.get("list"):
        print("  首条  :", c["list"][0]["vod_name"])

    s2 = s.searchContent("交锋", False)
    print("搜索交锋:", len(s2.get("list", [])), "条")

    vid = (s2.get("list") or c.get("list") or [{}])[0].get("vod_id")
    if vid:
        d = s.detailContent([vid])
        if d.get("list"):
            dd = d["list"][0]
            names = dd["vod_play_from"].split("$$$")
            eps = dd["vod_play_url"].split("$$$")
            print("\n详情    :", dd["vod_name"], "| 线路:", names)
            for i, nm in enumerate(names):
                ep = eps[i].split("#")[0]
                p = s.playerContent(nm, ep)
                u = p.get("url") or ""
                print("  [%s] → %s" % (nm, (u[:96] + "...") if len(u) > 96 else (u or p.get("msg", ""))))
