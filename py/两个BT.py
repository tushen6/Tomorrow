#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bttwo.life（两个BT影视）TVBox 蜘蛛
站点：https://www.bttwo.life
结构：服务端渲染；列表走 /filter?classify=N&areas=&types=&years=&tags=&sort_by=&order=&page=；
     详情播放合一 /play/{code}，每集独立 URL；真实 m3u8 藏于 JS 取流接口，静态 HTML 拿不到，
     playerContent 做多路尝试，拿不到则返回播放页由上层嗅探/解析。
作者：海豚🐬
"""

import re
import json
import base64
import html as _html

try:
    import requests as _requests
except Exception:
    _requests = None


class Spider:
    def __init__(self):
        self.site = "https://www.bttwo.life"
        self.name = "两个BT影视"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _requests.Session() if _requests else None
        self._extend = {}

    # ---------------- 框架契约 ----------------
    def getDependence(self):
        return []

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi")) or "m3u8" in u

    def destroy(self):
        pass

    def action(self, action):
        return {}

    def init(self, extend=""):
        self._extend = {}
        if isinstance(extend, dict):
            self._extend = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                e = json.loads(extend)
                if isinstance(e, dict):
                    self._extend = e
            except Exception:
                pass

    # ---------------- 基础工具 ----------------
    def _get(self, url, referer=None):
        h = dict(self.header)
        if referer:
            h["Referer"] = referer
        if self.s is not None:
            try:
                r = self.s.get(url, headers=h, timeout=12, allow_redirects=True)
                if r.status_code < 400:
                    return r.text
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            return ""

    def _u(self, u):
        if not u:
            return u
        u = u.strip().replace("&amp;", "&")
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        if u.startswith("/"):
            m = re.match(r"(https?://[^/]+)", self.site)
            return (m.group(1) if m else self.site) + u
        return self.site.rstrip("/") + "/" + u.lstrip("/")

    def _un(self, s):
        return _html.unescape(s) if s else ""

    # ---------------- 分类与筛选 ----------------
    # classify: 1=电影 2=电视剧 3=动漫 4=综艺
    _CLASSIFY = [
        ("1", "电影"),
        ("2", "电视剧"),
        ("3", "动漫"),
        ("4", "综艺"),
    ]

    def _filters(self):
        # 二级分类：地区 / 类型 / 年份 / 标签 / 排序
        areas = [
            ("", "全部地区"), ("7", "中国"), ("5", "美国"), ("12", "韩国"),
            ("11", "日本"), ("6", "法国"),
        ]
        types = [
            ("", "全部类型"), ("1", "剧情"), ("5", "喜剧"), ("10", "动作"),
            ("14", "科幻"), ("2", "悬疑"), ("3", "恐怖"),
        ]
        years = [
            ("", "全部年份"), ("1", "2026"), ("3", "2025"), ("4", "2024"),
        ]
        tags = [
            ("", "全部标签"), ("1", "4K"), ("37", "HD"), ("36", "院线"), ("38", "TC"),
        ]
        sorts = [
            ("update_time", "最新上映"), ("hits", "最受欢迎"), ("score", "评分最高"),
        ]
        flt = []
        for key, name, opts in (
            ("areas", "地区", areas),
            ("types", "类型", types),
            ("years", "年份", years),
            ("tags", "标签", tags),
            ("sort_by", "排序", sorts),
        ):
            flt.append({
                "key": key,
                "name": name,
                "value": [{"n": n, "v": v} for v, n in opts],
            })
        return flt

    def homeContent(self, filter=None):
        cats = [{"type_id": cid, "type_name": cname} for cid, cname in self._CLASSIFY]
        filters = {}
        flt = self._filters()
        for cid, _ in self._CLASSIFY:
            filters[cid] = flt
        # 首页推荐：取电影分类第一页一部分
        vod_list = []
        try:
            html = self._get(self.site + "/filter?classify=1")
            vod_list = self._items(html)[:24]
        except Exception:
            pass
        return {"class": cats, "filters": filters, "list": vod_list}

    def homeVideoContent(self):
        try:
            html = self._get(self.site + "/filter?classify=1")
            return {"list": self._items(html)[:24]}
        except Exception:
            return {"list": []}

    # ---------------- 列表解析 ----------------
    def _items(self, html, base=None):
        """解析 /filter 列表卡片：a[href=/play/xxx] + img + 标题。"""
        out = []
        seen = set()
        if not html:
            return out
        # 卡片：<a href="/play/xxxx">...<img src=...>...标题...</a>
        for m in re.finditer(
            r'<a[^>]+href="(/play/[A-Za-z0-9]+)"[^>]*>([\s\S]{20,2000}?)</a>',
            html,
        ):
            href, block = m.group(1), m.group(2)
            if href in seen:
                continue
            seen.add(href)
            # 海报：优先 data-src（懒加载真实地址），src 可能是占位图
            im = re.search(r'<img[^>]+?data-src="([^"]+)"', block)
            if not im:
                im = re.search(r'<img[^>]+?data-original="([^"]+)"', block)
            if not im:
                im = re.search(r'<img[^>]+?src="((?!/static/images/placeholder)[^"]+)"', block)
            pic = self._u(im.group(1)) if im else ""
            if "placeholder" in pic.lower():
                pic = ""
            # 标题：优先 h3 标签（卡片无 title 属性，h3 才是真实片名）
            hm = re.search(r"<h3[^>]*>([^<]{2,60})</h3>", block)
            if hm:
                name = self._un(hm.group(1)).strip()
            else:
                tm = re.search(r'title="([^"]{2,60})"', block)
                if tm:
                    name = tm.group(1)
                else:
                    txt = re.sub(r"<[^>]+>", "|", block)
                    parts = [p.strip() for p in txt.split("|") if p.strip()]
                    name = ""
                    for p in parts:
                        p = self._un(p)
                        # 排除纯标签词（4k/HD/VIP/TC/院线等）和集数信息
                        if p.lower() in ("4k", "hd", "tc", "vip", "院线"):
                            continue
                        if 2 <= len(p) <= 40 and not re.match(r"^[\d.\s分集全更新至]+$", p):
                            name = p
                            break
            # 备注：先去掉 img 标签（防 app=2001 这类 URL 误匹配），再从文本找集数/年份
            block_noimg = re.sub(r"<img[^>]*>", "", block)
            rm = re.search(r"(更新至\d+集|全\d+集)", block_noimg)
            remark = rm.group(1) if rm else ""
            if not remark:
                ym = re.search(r"<[^>]*>(20\d{2}|19\d{2})<", block_noimg)
                remark = ym.group(1) if ym else ""
            out.append({
                "vod_id": href,  # 详情即 /play/{code}
                "vod_name": self._un(name).strip(),
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return out

    def _cat_url(self, tid, pg, extend=None):
        """拼 /filter 列表 URL。tid 为 classify id；extend 含 areas/types/years/tags/sort_by。"""
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        q = {"classify": str(tid), "page": str(pg), "order": "desc"}
        ext = extend or {}
        for k in ("areas", "types", "years", "tags"):
            v = str(ext.get(k, "") or "").strip()
            if v:
                q[k] = v
        sb = str(ext.get("sort_by", "") or "").strip()
        q["sort_by"] = sb if sb else "update_time"
        from urllib.parse import urlencode
        return self.site + "/filter?" + urlencode(q)

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        ext = {}
        if isinstance(extend, dict):
            ext = extend
        elif isinstance(filter, dict):
            ext = filter
        url = self._cat_url(tid, pg, ext)
        html = self._get(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}
        vod_list = self._items(html)
        pagecount = pg
        # 从“共 X 页”或末页链接推断
        m = re.search(r"共\s*(\d+)\s*页", html)
        if m:
            pagecount = int(m.group(1))
        else:
            pages = re.findall(r"[?&]page=(\d+)", html)
            if pages:
                pagecount = max(pagecount, max(int(p) for p in pages))
        # 有下一页链接则至少 pg+1
        if re.search(r"[?&]page=%d\b" % (pg + 1), html):
            pagecount = max(pagecount, pg + 1)
        return {
            "list": vod_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        vid = str(vid or "").strip()
        url = self._u(vid)
        html = self._get(url)
        if not html:
            return {"list": []}
        # 标题：<title>xxx - 第N集 -两个BT影视</title> 或 h1
        title = ""
        tm = re.search(r"<title[^>]*>([^<]+)</title>", html)
        if tm:
            title = self._un(tm.group(1)).strip()
            title = re.sub(r"\s*-\s*第\d+集.*$", "", title)
            title = re.sub(r"\s*-\s*两个BT影视\s*$", "", title)
        if not title:
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
            if h1:
                title = self._un(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        # 海报：多路尝试（og:image / data-poster / 详情区 img）
        pic = ""
        for pat in (
            r'property="og:image"\s+content="([^"]+)"',
            r'data-poster="([^"]+)"',
            r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*(?:poster|thumb|cover)[^"]*"',
            r'class="[^"]*(?:poster|thumb|cover)[^"]*"[^>]*>[\s\S]{0,500}?<img[^>]+src="([^"]+)"',
        ):
            im = re.search(pat, html, re.I)
            if im:
                pic = self._u(im.group(1))
                if pic and "placeholder" not in pic.lower() and "loading" not in pic.lower():
                    break
        else:
            pic = ""
        # 简介：meta description / og:description
        desc = ""
        dm = re.search(r'property="og:description"\s+content="([^"]+)"', html)
        if not dm:
            dm = re.search(r'name="description"\s+content="([^"]+)"', html)
        if dm:
            desc = self._un(dm.group(1)).strip()
        # 详细信息：导演/主演/类型/地区/年份
        info = {}
        for label, value in re.findall(
            r'<div class="col-span-1 text-gray-500">([^<]+)</div>\s*<div[^>]*>([^<]+)</div>', html
        ):
            info[label.strip()] = self._un(value).strip()
        director = info.get("导演", "")
        actors = info.get("主演", "")
        genre = info.get("类型", "")
        area = info.get("地区", "")
        year = ""
        ym = re.search(r"(19|20)\d{2}", info.get("上映", ""))
        if ym:
            year = ym.group(0)
        # 拼简介头
        info_lines = []
        if director:
            info_lines.append("导演：%s" % director)
        if actors:
            info_lines.append("主演：%s" % actors)
        meta = []
        if genre:
            meta.append("类型：%s" % genre)
        if area:
            meta.append("地区：%s" % area)
        if year:
            meta.append("年份：%s" % year)
        if meta:
            info_lines.append(" | ".join(meta))
        full_desc = "\n".join(info_lines)
        if desc:
            full_desc += ("\n\n" if full_desc else "") + desc
        # 选集：Alpine.js 组件写法，a 标签内嵌复杂属性，直接从 data-episode 属性提取
        # （旧写法按 </a> 配对，在此站匹配数为 0）
        eps = []
        seen = set()
        cur_code = re.search(r"/play/([A-Za-z0-9]+)", url)
        cur_code = cur_code.group(1) if cur_code else ""
        for m in re.finditer(r'<a[^>]*?href="(/play/[A-Za-z0-9]+)"[^>]*?data-episode="(\d+)"', html):
            href, num = m.group(1), int(m.group(2))
            code = href.split("/")[-1]
            if code in seen or code == cur_code:
                continue
            seen.add(code)
            eps.append((num, "第%d集$%s" % (num, self._u(href))))
        # 当前页本身作为第1个（从标题取集数）
        cm = re.search(r"第(\d+)集", self._un(tm.group(1)) if tm else "")
        cur_num = int(cm.group(1)) if cm else 1
        eps.append((cur_num, "第%d集$%s" % (cur_num, url)))
        eps.sort(key=lambda x: x[0])
        play_url = "#".join(e for _, e in eps)
        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_actor": actors,
            "vod_director": director,
            "vod_year": year,
            "vod_area": area,
            "vod_content": full_desc,
            "vod_play_from": "两个BT",
            "vod_play_url": play_url,
        }]}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick=False, pg="1"):
        from urllib.parse import quote
        url = self.site + "/search?q=" + quote(str(key))
        html = self._get(url)
        if not html:
            return {"list": []}
        return {"list": self._items(html)}

    # ---------------- 播放 ----------------
    def _extract_m3u8(self, html, page_url):
        """多路尝试从播放页提取直链。"""
        if not html:
            return ""
        # 1) 裸 m3u8
        m = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html)
        if m:
            return m.group(1)
        # 2) 常见 JS 变量
        for var in ("videoUrl", "playUrl", "source", "src", "url", "m3u8", "now"):
            m = re.search(
                r'var\s+%s\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']' % re.escape(var), html
            )
            if m:
                return self._u(m.group(1))
        # 3) JSON 里的 m3u8
        m = re.search(r'"(https?://[^"]+\.m3u8[^"]*)"', html)
        if m:
            return m.group(1).replace("\\/", "/")
        # 4) dataid → 尝试站内取流接口（模式探测）
        dataid = re.search(r'dataid="(\d+)"', html)
        code = re.search(r"/play/([A-Za-z0-9]+)", page_url or "")
        for tpl in (
            "/api/play/{code}",
            "/api/video/{dataid}",
            "/api/episode/{dataid}",
            "/api/url/{code}",
        ):
            api = self.site + tpl.format(
                code=code.group(1) if code else "",
                dataid=dataid.group(1) if dataid else "",
            )
            try:
                txt = self._get(api, referer=page_url)
                if not txt:
                    continue
                m2 = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', txt)
                if m2:
                    return m2.group(1)
                try:
                    j = json.loads(txt)
                    s = json.dumps(j)
                    m2 = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', s)
                    if m2:
                        return m2.group(1)
                except Exception:
                    pass
            except Exception:
                pass
        return ""

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        url = str(url or "").strip()
        if not url:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        if not url.startswith("http"):
            url = self._u(url)
        u = url.lower()
        if u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi")) or "m3u8" in u:
            return {"parse": 0, "url": url, "header": dict(self.header)}
        html = self._get(url, referer=self.site + "/")
        found = self._extract_m3u8(html, url)
        if found:
            if found.startswith("//"):
                found = "https:" + found
            elif not found.startswith("http"):
                found = self._u(found)
            return {"parse": 0, "url": found, "header": dict(self.header)}
        # 拿不到直链：交由上层嗅探/解析（TVBox 解析或外部播放器处理）
        return {"parse": 1, "url": url, "header": dict(self.header)}

    def localProxy(self, param):
        u = param.get("url", "") if isinstance(param, dict) else ""
        if not u:
            return [403, "text/plain", b"", None]
        h = dict(self.header)
        if self.s is not None:
            try:
                r = self.s.get(u, headers=h, timeout=15)
                return [200, r.headers.get("Content-Type", "application/octet-stream"), r.content, None]
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(u, headers=h)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return [200, resp.headers.get("Content-Type", "application/octet-stream"), resp.read(), None]
        except Exception:
            return [403, "text/plain", b"", None]
