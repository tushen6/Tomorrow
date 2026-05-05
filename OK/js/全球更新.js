// 全球追更 - peekpili JS 源版（目录模式，仅列表 + goSearch）
const TMDB_API_KEY = "aea23464c667a5f4c17382d4fd21dfc2";
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36";
const DATA_SOURCES = {
  tmdbImage: "https://images.tmdb.org/t/p/w500",
  tmdbApis: [
    "https://api.tmdb.org/3",
    "https://api.themoviedb.org/3"
  ]
};
// 简单 log（peekpili 一般有自己的 log，你也可以直接用 print/log）
const log = {
  info: (msg) => { try { print("[INFO] " + msg); } catch (e) {} },
  warn: (msg) => { try { print("[WARN] " + msg); } catch (e) {} },
  error: (msg) => { try { print("[ERROR] " + msg); } catch (e) {} }
};
// ===================== HTTP 封装（用 req 代替 axios） =====================
async function httpGet(url, params) {
  let query = "";
  if (params && Object.keys(params).length > 0) {
    const qs = Object.keys(params)
      .map(k => encodeURIComponent(k) + "=" + encodeURIComponent(params[k]))
      .join("&");
    query = url.indexOf("?") > -1 ? "&" + qs : "?" + qs;
  }
  const u = url + query;
  const r = await req(u, {
    headers: {
      "User-Agent": UA
    }
  });
  return JSON.parse(r.content);
}
// TMDB 多域名回退
async function fetchTmdb(endpoint, params) {
  let lastError;
  for (let i = 0; i < DATA_SOURCES.tmdbApis.length; i++) {
    const baseUrl = DATA_SOURCES.tmdbApis[i];
    try {
      const url = baseUrl + endpoint;
      const allParams = Object.assign({ api_key: TMDB_API_KEY }, params || {});
      const json = await httpGet(url, allParams);
      return json;
    } catch (e) {
      lastError = e;
      log.warn("[TMDB] " + baseUrl + " 访问异常: " + e);
    }
  }
  throw lastError || new Error("TMDB 全部域名访问失败");
}
// ===================== 简单日期处理 =====================
function formatDate(dateStr) {
  if (!dateStr) return "";
  return dateStr;
}
function getToday() {
  const d = new Date();
  const y = d.getFullYear();
  const m = (d.getMonth() + 1).toString().padStart(2, "0");
  const day = d.getDate().toString().padStart(2, "0");
  return y + "-" + m + "-" + day;
}
// ===================== 平台与筛选配置 =====================
const PLATFORM_CONFIG = [
  { id: "tencent",  name: "腾讯视频",      network: "2007" },
  { id: "youku",    name: "优酷",          network: "1419" },
  { id: "iqiyi",    name: "爱奇艺",        network: "1330" },
  { id: "bilibili", name: "哔哩哔哩",      network: "1605" },
  { id: "mgtv",     name: "芒果TV",        network: "1631" },
  { id: "netflix",  name: "Netflix",      network: "213"  },
  { id: "hbo",      name: "HBO Max",      network: "49"   },
  { id: "disney",   name: "Disney+",      network: "2739" },
  { id: "appletv",  name: "Apple TV+",    network: "2552" },
  { id: "amazon",   name: "Amazon Prime", network: "1024" },
  { id: "hulu",     name: "Hulu",         network: "453"  },
  { id: "paramount",name: "Paramount+",   network: "4330" }
];
const SUB_FILTERS = {
  "sort": {
    "key": "sort",
    "name": "🔥 动态追踪",
    "value": [
      { "n": "📅 追更模式", "v": "next_episode" },
      { "n": "📆 今日播出", "v": "daily_airing" },
      { "n": "🆕 最新上线", "v": "first_air_date.desc" },
      { "n": "⭐ 综合热度", "v": "popularity.desc" }
    ]
  },
  "type": {
    "key": "type",
    "name": "📺 内容类型",
    "value": [
      { "n": "🎥 电视剧集", "v": "tv" },
      { "n": "🎬 电影作品", "v": "movie" },
      { "n": "🌸 动漫动画", "v": "anime" },
      { "n": "🎤 综艺节目", "v": "variety" }
    ]
  }
};
function generateClassAndFilters() {
  const classList = PLATFORM_CONFIG.map(p => ({ type_id: p.id, type_name: p.name }));
  const filters = {};
  PLATFORM_CONFIG.forEach(p => {
    filters[p.id] = [SUB_FILTERS.sort, SUB_FILTERS.type];
  });
  return { class: classList, filters };
}
// ===================== 简单缓存（内存） =====================
const cache = {};
const CACHE_TTL = 10 * 60 * 1000;
const MAX_CACHE_SIZE = 800;
function getCachedData(key) {
  const data = cache[key];
  if (!data) return null;
  if (Date.now() - data.time > CACHE_TTL) {
    delete cache[key];
    return null;
  }
  return data.value;
}
function setCachedData(key, value) {
  const keys = Object.keys(cache);
  if (keys.length >= MAX_CACHE_SIZE) {
    delete cache[keys[0]];
  }
  cache[key] = { value: value, time: Date.now() };
}
// ===================== JS 源标准接口 =====================
async function init(cfg) {}
// 首页：返回分类 + 筛选配置
async function home(filter) {
  const { class: classList, filters } = generateClassAndFilters();
  return JSON.stringify({
    class: classList,
    filters: filters
  });
}
// 分类列表：支持筛选（sort/type）
async function category(tid, pg, filter, extend) {
  const page = parseInt(pg || "1");
  const platform = PLATFORM_CONFIG.find(p => p.id === tid);
  if (!platform) {
    return JSON.stringify({
      page: page,
      pagecount: 1,
      limit: 20,
      total: 0,
      list: []
    });
  }
  let sort = "popularity.desc";
  let type = "tv";
  try {
    if (extend) {
      if (extend.sort) sort = extend.sort;
      if (extend.type) type = extend.type;
    } else if (filter) {
      if (filter.sort) sort = filter.sort;
      if (filter.type) type = extend.type;
    }
  } catch (e) {}
  const today = getToday();
  let endpoint = type === "movie" ? "/discover/movie" : "/discover/tv";
  let queryParams = {
    with_networks: platform.network,
    language: "zh-CN",
    page: page,
    sort_by: (sort === "daily_airing" || sort === "next_episode") ? "popularity.desc" : sort
  };
  if (type === "anime") {
    queryParams.with_genres = "16";
  }
  if (type === "variety") {
    queryParams.with_genres = "10764|10767";
  }
  if (sort === "daily_airing") {
    queryParams["air_date.gte"] = today;
    queryParams["air_date.lte"] = today;
  }
  let items = [];
  try {
    const res = await fetchTmdb(endpoint, queryParams);
    items = res && res.results ? res.results : [];
  } catch (e) {
    log.error("基础列表请求失败: " + e);
    return JSON.stringify({
      page: page,
      pagecount: 1,
      limit: 20,
      total: 0,
      list: []
    });
  }
  const processedItems = [];
  const BATCH_SIZE = 5;
  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    for (let j = 0; j < batch.length; j++) {
      const item = batch[j];
      const cacheKey = "info_" + type + "_" + item.id + "_" + sort;
      const cached = getCachedData(cacheKey);
      if (cached) {
        processedItems.push(cached);
        continue;
      }
      let finalTitle = item.name || item.title || "";
      let remark = "⭐" + (item.vote_average ? item.vote_average.toFixed(1) : "0.0");
      let sortDate = item.first_air_date || item.release_date || "1900-01-01";
      const hasNoChinese = !/[\u4e00-\u9fa5]/.test(finalTitle);
      try {
        const detailEndpoint = "/" + (type === "movie" ? "movie" : "tv") + "/" + item.id;
        const detail = await fetchTmdb(detailEndpoint, {
          language: "zh-CN",
          append_to_response: "alternative_titles,external_ids"
        });
        const showEpisodeTag =
          type !== "movie" &&
          (sort === "next_episode" || sort === "daily_airing" || sort === "first_air_date.desc");
        if (showEpisodeTag) {
          const targetEp = (detail && (detail.next_episode_to_air || detail.last_episode_to_air)) || null;
          if (targetEp) {
            sortDate = targetEp.air_date || sortDate;
            const s = (targetEp.season_number || 0).toString().padStart(2, "0");
            const eNum = (targetEp.episode_number || 0).toString().padStart(2, "0");
            const icon = detail.next_episode_to_air ? "🕒" : "✅";
            remark = icon + (formatDate(sortDate).slice(5)) + " S" + s + "E" + eNum;
          }
        } else {
          const releaseYear = (detail && (detail.release_date || detail.first_air_date) || "").substr(0, 4);
          if (releaseYear) {
            remark += " | " + releaseYear;
          }
        }
        if (hasNoChinese && detail && detail.alternative_titles) {
          const alt = detail.alternative_titles.titles || detail.alternative_titles.results || [];
          for (let k = 0; k < alt.length; k++) {
            const t = alt[k];
            if (t && t.iso_3166_1 === "CN" && t.title) {
              finalTitle = t.title;
              break;
            }
          }
        }
      } catch (e2) {
        log.warn("详情请求失败 [ID: " + item.id + "]: " + e2);
      }
      const vod = {
        vod_id: item.id.toString(),
        vod_name: finalTitle,
        vod_pic: item.poster_path ? (DATA_SOURCES.tmdbImage + item.poster_path) : "",
        vod_remarks: remark,
        goSearch: true,
        _date: sortDate
      };
      setCachedData(cacheKey, vod);
      processedItems.push(vod);
    }
  }
  return JSON.stringify({
    page: page,
    pagecount: 100,
    limit: 20,
    total: 2000,
    list: processedItems
  });
}
async function detail(id) {
  return JSON.stringify({ list: [] });
}
async function search(wd, quick, pg) {
  return JSON.stringify({ list: [] });
}
async function play(flag, id, flags) {
  return JSON.stringify({
    parse: 1,
    url: id
  });
}
export default {
  init,
  home,
  category,
  detail,
  search,
  play
};
