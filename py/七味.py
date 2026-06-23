# -*- coding: utf-8 -*-
import re
import ssl
import json
import html
import base64
import urllib3
import threading
import time
import sys
from urllib.parse import quote, unquote, urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from pyquery import PyQuery as pq

sys.path.append("..")
from base.spider import Spider as BaseSpider

urllib3.disable_warnings()


class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(connections, maxsize, block=block, **kwargs)

    def proxy_manager_for(self, proxy, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx
        return super().proxy_manager_for(proxy, **kwargs)


class Spider(BaseSpider):
    hosts = [
        "https://www.qwmkv.com",
        "https://www.qwnull.com",
        "https://www.qwfilm.com",
        "https://www.qnmp4.com",
        "https://www.qn63.com"
    ]
    host = hosts[0]

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; M2012K11AC) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    CATEGORY_IDS = {"电影": 1, "剧集": 2, "综艺": 3, "动漫": 4, "短剧": 30}
    KEYWORDS = ["杜比", "dolby", "原盘", "高码", "remux", "蓝光", "hdr10+", "hdr10", "hdr", "4k", "2160p", "uhd"]

    QUARK_CHECK_LIMIT = 100
    CHECK_TIME_BUDGET = 12.0  # 检测最多12秒

    def getName(self):
        return "七味-最终稳定版(含大屏分组排序+防串位修复)"

    def init(self, extend=""):
        self.session = requests.Session()
        adapter = SSLAdapter(max_retries=2)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.verify = False
        self.session.headers.update(dict(self.headers))

        self.last_vod_pic = ""
        self.vod_pic_cache = {}

        self.pan_115_cookie = ""
        self.ack_mp4 = "https://vd2.bdstatic.com/mda-nj5kxa8kr7wgq6ie/sc/cae_h264_nowatermark/1653272065989267185/mda-nj5kxa8kr7wgq6ie.mp4"

        if extend:
            try:
                ext = json.loads(extend)
                self.pan_115_cookie = ext.get("pan_115_cookie", "")
                self.ack_mp4 = ext.get("ack_mp4", self.ack_mp4)
            except Exception as e:
                print(f"init extend error: {e}")

        self._probe_host()

    def destroy(self):
        try:
            self.session.close()
        except:
            pass

    # ---------------- utils ----------------
    def _probe_host(self):
        for h in self.hosts:
            try:
                r = self.session.get(h + "/", timeout=6, headers=self.headers, verify=False)
                if r.status_code == 200:
                    self.host = h
                    return
            except:
                pass

    def _full_url(self, path):
        if not path:
            return ""
        path = html.unescape(str(path)).strip()
        if path.startswith("//"):
            return "https:" + path
        if path.startswith(("http://", "https://", "magnet:?")):
            return path
        return urljoin(self.host + "/", path)

    def _full_url_by_host(self, host, path):
        if not path:
            return ""
        path = html.unescape(str(path)).strip()
        if path.startswith("//"):
            return "https:" + path
        if path.startswith(("http://", "https://", "magnet:?")):
            return path
        return urljoin(host.rstrip("/") + "/", path.lstrip("/"))

    def _fetch(self, url, timeout=10):
        tries = [self._full_url(url)]
        if isinstance(url, str) and not url.startswith(("http://", "https://", "magnet:?")):
            for h in self.hosts:
                u = urljoin(h + "/", url)
                if u not in tries:
                    tries.append(u)

        for u in tries:
            try:
                h = dict(self.headers)
                h["Referer"] = self.host + "/"
                r = self.session.get(u, timeout=timeout, headers=h, verify=False)
                r.encoding = r.apparent_encoding or "utf-8"
                if r.status_code == 200 and len(r.text or "") > 30:
                    for hh in self.hosts:
                        if u.startswith(hh):
                            self.host = hh
                            break
                    return r
            except:
                continue
        return None

    def _pq(self, url, timeout=10):
        r = self._fetch(url, timeout=timeout)
        return pq(r.text if r else "")

    def _clean_text(self, s):
        return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

    def _clean_name(self, s, max_len=120):
        s = html.unescape(s or "").replace("#", "＃").replace("$", "＄")
        s = re.sub(r"\s+", " ", s).strip()
        return s[:max_len]

    def _img_src(self, img):
        return img.attr("data-src") or img.attr("data-original") or img.attr("src") or ""

    def _is_pan(self, u):
        u = (u or "").lower()
        return any(k in u for k in [
            "pan.quark.cn/s/", "pan.baidu.com/s/", "drive.uc.cn/s/",
            "pan.xunlei.com/s/", "aliyundrive.com/s/", "alipan.com/s/",
            "cloud.189.cn/", "caiyun.139.com/", "123pan.com/s/",
            "115.com/s/", "lanzou", "lanzoui", "lanzoux", "lanzoub"
        ])

    def _b64e(self, obj):
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        return base64.urlsafe_b64encode(txt.encode()).decode().rstrip("=")

    def _b64d(self, s):
        try:
            s += "=" * (-len(s) % 4)
            return json.loads(base64.urlsafe_b64decode(s.encode()).decode())
        except:
            return {}

    def _get_mid(self, tid):
        if str(tid).isdigit():
            return int(tid)
        m = re.search(r"/vt/(\d+)", str(tid))
        if m:
            return int(m.group(1))
        return 1

    def _score_name(self, name):
        n = (name or "").lower()
        score = 0
        for i, kw in enumerate(self.KEYWORDS):
            if kw.lower() in n:
                score += (len(self.KEYWORDS) - i)
        return score

    def _extract_video_list(self, doc):
        videos, seen = [], set()
        selectors = ["ul.pic-list li", "ul.content-list li", ".pic-list li", ".content-list li"]
        nodes = []
        for sel in selectors:
            n = list(doc(sel).items())
            if n:
                nodes = n
                break

        for li in nodes:
            a = li("a[href]").eq(0)
            href = a.attr("href")
            if not href:
                continue
            vid = self._full_url(href)
            if vid in seen:
                continue
            seen.add(vid)

            img = li("img").eq(0)
            pic = self._full_url(self._img_src(img))
            title = a.attr("title") or img.attr("alt") or li("h3 b").text() or li("h3").text() or ""
            remark = self._clean_text(li("span.s1").text() or li("span.s2").text() or li("p").text() or li(".tag").text())

            if pic:
                self.vod_pic_cache[vid] = pic

            videos.append({
                "vod_id": vid,
                "vod_name": self._clean_name(title, 80),
                "vod_pic": pic,
                "vod_remarks": remark
            })
        return videos

    def _is_bad_cover(self, u):
        if not u:
            return True
        s = u.lower()
        return ("logo.png" in s) or ("loading" in s) or ("/template/piankuwap/image/logo" in s)

    def _normalize_magnet(self, href):
        try:
            if not href:
                return ""
            href = str(href).strip().replace("&amp;", "&")
            if href.startswith("push://"):
                href = href.replace("push://", "", 1).replace("#0agent", "")
            if "%3A" in href or "%3F" in href or "%26" in href:
                href = unquote(href)
            href = re.sub(r"\s+", "", href)
            if not href.startswith("magnet:") or "urn:btih:" not in href:
                return ""
            return href
        except:
            return ""

    def _magnet_btih(self, magnet):
        m = self._normalize_magnet(magnet)
        if not m:
            return ""
        g = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", m, re.I)
        return g.group(1).lower() if g else ""

    def _is_verify_page(self, text):
        t = (text or "").lower()
        return (
            ("系统安全验证" in t) or
            ("verify_check" in t) or
            ("mac_verify_img" in t) or
            ("请输入验证码" in t)
        )

    def _mk_vod_id(self, h, raw_id, raw_url=""):
        if raw_url:
            u = self._full_url_by_host(h, raw_url)
            if "/mv/" in u and u.endswith(".html"):
                return u
            if str(raw_id).isdigit():
                return f"{h}/mv/{raw_id}.html"
            m = re.search(r"/mv/(\d+)\.html", u)
            if m:
                return f"{h}/mv/{m.group(1)}.html"
            return u

        rid = str(raw_id or "").strip()
        if rid.isdigit():
            return f"{h}/mv/{rid}.html"
        if rid.startswith(("http://", "https://", "/")):
            return self._full_url_by_host(h, rid)
        return f"{h}/mv/{rid}.html" if rid else ""

    # ---------------- only check quark/115 ----------------
    def _check_pan_valid(self, url, provider, timeout=3):
        if not url:
            return False
        if provider not in ("quark", "115"):
            return True
        try:
            h = dict(self.headers)
            h["Referer"] = self.host + "/"
            r = requests.get(url, headers=h, timeout=timeout, verify=False, allow_redirects=True)
            if r.status_code >= 400:
                return False
            text = (r.text or "").lower()
            if provider == "quark":
                keys = ["分享已失效", "不存在", "已被取消", "取消", "删除", "已被删除", "来晚了", "违规", "无法访问"]
            else:
                keys = ["分享已失效", "不存在", "404", "已取消", "链接错误"]
            return not any(k in text for k in keys)
        except:
            return False

    # ---------------- home ----------------
    def homeContent(self, filter):
        classes = [
            {"type_name": "大陆电影", "type_id": "https://www.qwmkv.com/ms/1-大陆-time---------.html"},
            {"type_name": "大陆剧集", "type_id": "https://www.qwmkv.com/ms/2-大陆-time---------.html"},
            {"type_name": "大陆综艺", "type_id": "https://www.qwmkv.com/ms/3-大陆-time---------.html"},
            {"type_name": "大陆动漫", "type_id": "https://www.qwmkv.com/ms/4-大陆-time---------.html"},
            {"type_name": "电影", "type_id": "/vt/1.html"},
            {"type_name": "综艺", "type_id": "/vt/3.html"},
            {"type_name": "剧集", "type_id": "/vt/2.html"},
            {"type_name": "动漫", "type_id": "/vt/4.html"},
            {"type_name": "短剧", "type_id": "/vt/30.html"},
        ]
        return {"class": classes}

    def homeVideoContent(self):
        doc = self._pq(self.host + "/")
        videos = self._extract_video_list(doc)
        return {"list": videos, "page": 1, "pagecount": 1, "limit": len(videos), "total": len(videos)}

    # ---------------- category ----------------
    def _build_category_url(self, tid, pg, fdict):
        if isinstance(tid, str) and tid.startswith(("http://", "https://")):
            if pg <= 1:
                return tid
            if "---------.html" in tid:
                return tid.replace("---------.html", f"------{pg}---.html")
            return tid.replace(".html", f"-{pg}.html")

        mid = self._get_mid(tid)
        if not fdict:
            return f"{self.host}/vt/{mid}.html" if pg <= 1 else f"{self.host}/vt/{mid}-{pg}.html"

        area = quote(fdict.get("地区", ""), safe="")
        sort = ""
        sv = fdict.get("排序", "")
        if sv == "按时间":
            sort = "time"
        elif sv == "按人气":
            sort = "hits"
        elif sv == "按评分":
            sort = "score"

        typ = quote(fdict.get("类型", ""), safe="")
        lang = quote(fdict.get("语言", ""), safe="")
        year = fdict.get("年代", "")
        fields = [area, sort, typ, lang, "", "", "", "", year]
        base = f"{self.host}/ms/{mid}-" + "-".join(fields)
        return base + ".html" if pg <= 1 else base + f"-{pg}.html"

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        fdict = extend if isinstance(extend, dict) else {}
        url = self._build_category_url(tid, pg, fdict)
        doc = self._pq(url)

        if len(doc("ul.pic-list li")) == 0 and len(doc("ul.content-list li")) == 0 and pg > 1:
            doc = self._pq(url.replace(".html", f".html?page={pg}"))

        videos = self._extract_video_list(doc)
        page_count = pg
        for a in doc(".pages a").items():
            t = (a.text() or "").strip()
            href = a.attr("href") or ""
            if t.isdigit():
                page_count = max(page_count, int(t))
            else:
                m = re.search(r"-(\d+)\.html", href)
                if m:
                    page_count = max(page_count, int(m.group(1)))

        return {
            "list": videos,
            "page": pg,
            "pagecount": max(page_count, pg),
            "limit": 30,
            "total": max(page_count, pg) * 30
        }

    # ---------------- detail ----------------
    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) and ids else ids
            vod_id = self._full_url(vod_id)

            doc = self._pq(vod_id)
            raw = doc.html() or ""

            # 1. 抓取基本影视信息
            title = self._clean_text(doc("h1").eq(0).text())
            if not title:
                tt = self._clean_text(doc("title").text())
                title = tt.split("在线观看")[0] if tt else "七味资源"

            cover = ""
            og = self._full_url(doc('meta[property="og:image"]').attr("content") or "")
            if og and not self._is_bad_cover(og):
                cover = og
            if not cover:
                c1 = self._full_url(self._img_src(doc(".main-left .img img").eq(0)))
                if c1 and not self._is_bad_cover(c1):
                    cover = c1
            if not cover:
                for im in doc("img").items():
                    src = self._full_url(self._img_src(im))
                    if src and not self._is_bad_cover(src):
                        cover = src
                        break
            if not cover:
                cover = self.vod_pic_cache.get(vod_id, "")
            if not cover:
                cover = self._full_url("/template/piankuwap/image/logo.png")
            self.last_vod_pic = cover

            content = self._clean_text(
                doc(".movie-introduce .sqjj_a").text() or
                doc(".movie-introduce .zkjj_a").text() or
                doc(".content").text()
            )

            # =====【优化修复】2. 多线路合并遍历抓取在线资源（彻底杜绝选择器冲突覆盖） =====
            online_routes = {}  # 格式: {"在线线路1": ["第1集$payload", "第2集$payload"]}
            player_uls = doc("div#url .bd ul.player, ul.player")
            line_no = 1
            for ul_node in player_uls.items():
                links = list(ul_node("a[href]").items())
                if not links:
                    continue
                
                route_name = f"📺在线播放-线路{line_no}"
                episodes = []
                for a in links:
                    href = a.attr("href")
                    if not href:
                        continue
                    src_name = self._clean_name(self._clean_text(a.text()) or "播放", 50)
                    payload = self._b64e({"type": "py", "url": self._full_url(href), "pic": cover})
                    episodes.append(f"{src_name}${payload}")
                
                if episodes:
                    online_routes[route_name] = episodes
                    line_no += 1

            # ===== 3. 规整网盘与磁力资源链接 =====
            pan_resources = []
            magnet_raw = []
            seen_pan = set()

            for a in doc("a[href]").items():
                u = html.unescape(a.attr("href") or "").strip()
                if not u:
                    continue
                txt = self._clean_text(a.text())

                if u.lower().startswith("magnet:?"):
                    magnet_raw.append((u, self._clean_name(txt or "磁力资源", 60)))
                    continue

                if self._is_pan(u):
                    low = u.lower()
                    pv = "other"
                    if "pan.quark" in low: pv = "quark"
                    elif "115.com" in low: pv = "115"
                    elif "pan.baidu" in low: pv = "baidu"
                    elif "drive.uc.cn" in low: pv = "uc"
                    elif "pan.xunlei" in low: pv = "xunlei"
                    elif "aliyundrive" in low or "alipan" in low: pv = "ali"
                    elif "cloud.189" in low: pv = "189"
                    elif "123pan" in low: pv = "pan123"

                    if u not in seen_pan:
                        seen_pan.add(u)
                        pan_resources.append({
                            "provider": pv,
                            "url": u,
                            "name": txt or "网盘资源",
                            "checked_valid": False
                        })

            for m in re.finditer(r"magnet:\?[^\s\"'<>]+", raw, re.I):
                magnet_raw.append((html.unescape(m.group(0)), "磁力资源"))

            # 磁力资源精简去重并打分排序
            magnet_unified = []
            btih_seen = set()
            for u, n in magnet_raw:
                mu = self._normalize_magnet(u)
                if not mu:
                    continue
                btih = self._magnet_btih(mu)
                key = btih if btih else mu.lower()
                if key in btih_seen:
                    continue
                btih_seen.add(key)
                magnet_unified.append({
                    "url": mu,
                    "name": self._clean_name(n or "磁力资源", 60)
                })
            magnet_unified.sort(key=lambda x: -self._score_name(x.get("name", "")))

            # ===== 4. 网盘有效性探针（保持原有超时/计数策略） =====
            check_begin = time.monotonic()
            quark_checked = 0
            valid_pan = []

            for p in pan_resources:
                if time.monotonic() - check_begin >= self.CHECK_TIME_BUDGET:
                    valid_pan.append(p)
                    continue

                pv = p["provider"]
                if pv == "quark":
                    if quark_checked >= self.QUARK_CHECK_LIMIT:
                        valid_pan.append(p)
                        continue
                    quark_checked += 1
                    if self._check_pan_valid(p["url"], "quark"):
                        p["checked_valid"] = True
                        valid_pan.append(p)
                elif pv == "115":
                    if self._check_pan_valid(p["url"], "115"):
                        p["checked_valid"] = True
                        valid_pan.append(p)
                else:
                    valid_pan.append(p)

            # =====【功能修复】5. 网盘资源渠道完全独立隔离，防止错乱混杂 =====
            pan_routes = {
                "quark": {"name": "🟢夸克网盘", "list": []},
                "ali": {"name": "☁️阿里云盘", "list": []},
                "115": {"name": "固定115网盘", "list": []},
                "baidu": {"name": "📘百度网盘", "list": []},
                "uc": {"name": "📱UC网盘", "list": []},
                "xunlei": {"name": "⚡迅雷网盘", "list": []},
                "189": {"name": "☎️天翼云盘", "list": []},
                "pan123": {"name": "📦123网盘", "list": []},
                "other": {"name": "📦其它网盘", "list": []}
            }

            for r in valid_pan:
                prov = r["provider"]
                if prov not in pan_routes:
                    prov = "other"
                
                ep_name = self._clean_name(r.get('name', '网盘提取资源'), 60)
                payload = self._b64e({"type": "pan", "url": r["url"], "pic": cover})
                pan_routes[prov]["list"].append(f"{ep_name}${payload}")

            # =====【核心修复】6. 按标准大屏壳子1:1规则完美有序组装，防串位 =====
            play_from = []
            play_url = []

            # 分支 A：写入网盘分类线路（依照预设的网盘体验优先级高低呈现）
            drive_order = ["quark", "ali", "115", "baidu", "uc", "xunlei", "189", "pan123", "other"]
            for d_key in drive_order:
                route_info = pan_routes[d_key]
                if route_info["list"]:
                    play_from.append(route_info["name"])
                    play_url.append("#".join(route_info["list"]))

            # 分支 B：写入磁力解析相关线路（保持互相隔离）
            if magnet_unified:
                lines_115 = []
                lines_play = []
                for i, m in enumerate(magnet_unified, start=1):
                    nm = self._clean_name(f"磁力源-{i:02d} {m['name']}", 60)
                    encoded_mag = base64.urlsafe_b64encode(m['url'].encode()).decode().rstrip("=")
                    p_payload = self._b64e({"type": "magnet", "url": m['url'], "pic": cover})
                    
                    lines_115.append(f"{nm}${encoded_mag}")
                    lines_play.append(f"{nm}${p_payload}")

                # 独立线路一：115离线专用线
                play_from.append("📥115云下载")
                play_url.append("#".join(lines_115))
                
                # 独立一条空白ACK确认交互线
                play_from.append("0")
                play_url.append("已提交请到115离线任务查看$__ACK__")
                
                # 独立线路二：自带流播或通过本地壳嗅探弹磁力
                play_from.append("🧲磁力播放")
                play_url.append("#".join(lines_play))

            # 分支 C：写入在线直连/网页采集线路
            for r_name, r_eps in online_routes.items():
                play_from.append(r_name)
                play_url.append("#".join(r_eps))

            # ===== 当前站搜索入口 =====
            try:
                search_payload = self._b64e({
                    "type": "search",
                    "wd": title,
                    "pic": cover
                })

                play_from.insert(0, "🔍点击选择")
                play_url.insert(0, f"当前站搜索${search_payload}")
            except Exception as e:
                print(f"search line add error: {e}")

            # 兜底处理
            if not play_from:
                play_from.append("🌐原网页查看")
                play_url.append(f"点击跳转原详情页${self._b64e({'type': 'web', 'url': vod_id, 'pic': cover})}")

            # 7. 构建标准影视输出字典
            vod = {
                "vod_id": vod_id,
                "vod_name": self._clean_name(title, 100),
                "vod_pic": cover,
                "vod_content": content,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
            }
            return {"list": [vod]}
        except Exception as e:
            print(f"detailContent error: {e}")
            return {"list": []}

    # ---------------- player ----------------
    def _parse_py_page(self, py_url):
        r = self._fetch(py_url, timeout=10)
        if not r:
            return ""
        txt = r.text or ""

        m = re.search(r"player_aaaa\s*=\s*(\{.*?\})\s*<", txt, re.S)
        if not m:
            m = re.search(r"player_aaaa\s*=\s*(\{.*?\})\s*;", txt, re.S)
        if not m:
            return ""

        js = m.group(1)
        try:
            js2 = re.sub(r"(\w+)\s*:", r'"\1":', js)
            obj = json.loads(js2)
        except:
            try:
                obj = json.loads(js)
            except:
                return ""

        u = obj.get("url", "") or ""
        enc = str(obj.get("encrypt", "0"))
        if enc == "1":
            u = unquote(u)
        elif enc == "2":
            try:
                u = unquote(base64.b64decode(u).decode("utf-8", "ignore"))
            except:
                pass

        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = self._full_url(u)
        return u

    def _return_ack_video(self):
        ret = {
            "parse": 0,
            "playUrl": "",
            "url": self.ack_mp4,
            "header": {
                "User-Agent": self.headers.get("User-Agent", ""),
                "Referer": self.host + "/"
            }
        }
        if self.last_vod_pic:
            ret["pic"] = self.last_vod_pic
            ret["poster"] = self.last_vod_pic
        return ret

    def _add_to_115(self, magnet):
        if not self.pan_115_cookie:
            print("115添加失败: 未配置 pan_115_cookie")
            return

        magnet = self._normalize_magnet(magnet)
        if not magnet:
            print("115添加失败: 非法磁力")
            return

        headers = {
            "User-Agent": self.headers.get("User-Agent", ""),
            "Cookie": self.pan_115_cookie,
            "Origin": "https://115.com",
            "Referer": "https://115.com/web/lixian/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }

        try:
            pan_sess = requests.Session()
            pan_sess.verify = False
            pan_sess.mount("http://", SSLAdapter(max_retries=2))
            pan_sess.mount("https://", SSLAdapter(max_retries=2))

            space_resp = pan_sess.get("https://115.com/?ct=offline&ac=space", headers=headers, timeout=10)
            try:
                space_json = space_resp.json()
            except:
                print(f"115获取签名失败(非JSON): {space_resp.text[:200]}")
                return

            if not space_json.get("state"):
                print(f"115获取签名失败(可能Cookie过期): {space_json}")
                return

            sign = space_json.get("sign", "")
            req_time = space_json.get("time", "")
            if not sign or not req_time:
                print(f"115签名数据异常: {space_json}")
                return

            uid_match = re.search(r'UID=(\d+)', self.pan_115_cookie)
            uid = uid_match.group(1) if uid_match else ""

            add_url = "https://115.com/web/lixian/?ct=lixian&ac=add_task_url"
            post_data = {"url": magnet, "uid": uid, "sign": sign, "time": req_time}
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

            add_resp = pan_sess.post(add_url, data=post_data, headers=headers, timeout=10)
            try:
                add_json = add_resp.json()
            except:
                print(f"115添加失败(非JSON): {add_resp.text[:200]}")
                return

            if add_json.get("state") or add_json.get("errcode") == 0:
                print(f"115离线添加成功: {magnet[:100]}...")
            else:
                err = add_json.get("error_msg") or add_json.get("msg") or add_json.get("error") or str(add_json)
                print(f"115添加失败: {err}")
        except Exception as e:
            print(f"115离线网络异常: {e}")

    def playerContent(self, flag, id, vipFlags):
        if flag == "0" or id == "__ACK__":
            return self._return_ack_video()

        if flag == "📥115云下载":
            try:
                decoded = base64.urlsafe_b64decode(id.encode() + b"==").decode()
                magnet = self._normalize_magnet(decoded)
                if not magnet:
                    return self._return_ack_video()
                if not self.pan_115_cookie:
                    print("115未配置Cookie")
                    return self._return_ack_video()

                threading.Thread(target=self._add_to_115, args=(magnet,), daemon=True).start()
                return self._return_ack_video()
            except Exception as e:
                print(f"115云下载处理异常: {e}")
                return self._return_ack_video()

        if flag == "🧲磁力播放":
            data = self._b64d(id)
            if data and data.get("type") == "magnet":
                mu = self._normalize_magnet(data.get("url", ""))
                if mu:
                    pic = data.get("pic") or self.last_vod_pic
                    return {"parse": 0, "url": "push://" + mu, "pic": pic, "poster": pic}

            if isinstance(id, str) and id.startswith("push://"):
                return {"parse": 0, "url": id, "pic": self.last_vod_pic, "poster": self.last_vod_pic}

            mu = self._normalize_magnet(id)
            if mu:
                return {"parse": 0, "url": "push://" + mu, "pic": self.last_vod_pic, "poster": self.last_vod_pic}

            return {"parse": 1, "url": id, "pic": self.last_vod_pic, "poster": self.last_vod_pic}

        data = self._b64d(id)
        if not data:
            if isinstance(id, str) and id.startswith("push://"):
                return {"parse": 0, "url": id, "pic": self.last_vod_pic, "poster": self.last_vod_pic}
            return {"parse": 1, "url": id, "pic": self.last_vod_pic, "poster": self.last_vod_pic}

        typ = data.get("type", "")
        url = data.get("url", "")
        pic = data.get("pic") or self.last_vod_pic

        if not url:
            return {"parse": 1, "url": id, "pic": pic, "poster": pic}

        if typ == "search":

            wd = data.get("wd", "").strip()

            if not wd:
                return {
                    "parse": 1,
                    "url": self.host,
                    "pic": pic,
                    "poster": pic
                }

            search_url = f"{self.host}/vodsearch/{quote(wd)}----------1---.html"

            return {
                "parse": 0,
                "url": "push://" + search_url,
                "pic": pic,
                "poster": pic
            }

        if typ == "pan":
            return {"parse": 0, "url": "push://" + url, "pic": pic, "poster": pic}
        if typ == "magnet":
            mu = self._normalize_magnet(url)
            if mu:
                return {"parse": 0, "url": "push://" + mu, "pic": pic, "poster": pic}
            return {"parse": 1, "url": url, "pic": pic, "poster": pic}
        if typ == "py":
            real = self._parse_py_page(url)
            if real:
                return {"parse": 0, "url": real, "pic": pic, "poster": pic}
            return {"parse": 1, "url": url, "pic": pic, "poster": pic}
        if typ == "web":
            return {"parse": 1, "url": url, "pic": pic, "poster": pic}

        return {"parse": 1, "url": url, "pic": pic, "poster": pic}

    # ---------------- search ----------------
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1
        wd = quote(key)

        for h in self.hosts:
            suggest_api = f"{h}/index.php/ajax/suggest?mid=1&limit=20&wd={wd}"
            try:
                r = self.session.get(suggest_api, timeout=8, headers=self.headers, verify=False)
                txt = r.text or ""
                if not self._is_verify_page(txt) and r.status_code == 200:
                    data = r.json()
                    lst = data.get("list") or []
                    videos = []

                    for it in lst:
                        vid = it.get("id") or it.get("vod_id")
                        name = it.get("name") or it.get("vod_name") or ""
                        pic = self._full_url_by_host(h, it.get("pic") or it.get("vod_pic") or "")
                        remarks = self._clean_text(it.get("en") or it.get("remark") or "")
                        jump_url = it.get("url") or it.get("link") or ""

                        vid_url = self._mk_vod_id(h, vid, jump_url)
                        if not vid_url:
                            continue

                        if pic:
                            self.vod_pic_cache[vid_url] = pic

                        videos.append({
                            "vod_id": vid_url,
                            "vod_name": self._clean_name(name, 80),
                            "vod_pic": pic,
                            "vod_remarks": remarks
                        })

                    if videos:
                        self.host = h
                        return {
                            "list": videos,
                            "page": pg,
                            "pagecount": pg + 1 if len(videos) >= 20 else pg,
                            "limit": len(videos),
                            "total": len(videos)
                        }
            except:
                pass

            api_list = [
                f"{h}/api.php/provide/vod/?ac=detail&wd={wd}&pg={pg}",
                f"{h}/api.php/provide/vod?ac=detail&wd={wd}&pg={pg}",
            ]
            for api in api_list:
                try:
                    r = self.session.get(api, timeout=8, headers=self.headers, verify=False)
                    txt = r.text or ""
                    if self._is_verify_page(txt):
                        continue
                    if r.status_code != 200:
                        continue

                    data = r.json()
                    lst = data.get("list") or data.get("data") or []
                    videos = []

                    for it in lst:
                        vid = it.get("vod_id") or it.get("id")
                        name = it.get("vod_name") or it.get("name") or ""
                        pic = self._full_url_by_host(h, it.get("vod_pic") or it.get("pic") or "")
                        remarks = self._clean_text(it.get("vod_remarks") or it.get("remarks") or "")
                        jump_url = it.get("vod_play_url") or it.get("url") or it.get("link") or ""

                        vid_url = self._mk_vod_id(h, vid, jump_url)
                        if not vid_url:
                            continue

                        if pic:
                            self.vod_pic_cache[vid_url] = pic

                        videos.append({
                            "vod_id": vid_url,
                            "vod_name": self._clean_name(name, 80),
                            "vod_pic": pic,
                            "vod_remarks": remarks
                        })

                    if videos:
                        self.host = h
                        return {
                            "list": videos,
                            "page": int(data.get("page", pg) or pg),
                            "pagecount": int(data.get("pagecount", 1) or 1),
                            "limit": len(videos),
                            "total": int(data.get("total", len(videos)) or len(videos))
                        }
                except:
                    pass

        return {
            "list": [],
            "page": pg,
            "pagecount": pg,
            "limit": 0,
            "total": 0
        }