import { Crypto, _ } from 'assets://js/lib/cat.js';
 
let siteUrl = '';
let key = '';
let iv = '';
let siteKey = '';
let siteType = 3;
let apiPrefix = 'getappapi.index';
 
const prefixMap = {
    '1': 'getappapi.index',
    '2': 'qijiappapi.index',
    '3': 'appapi'
};
 
let enableVerifyTimeSign = false;
let headers = {
    'User-Agent': 'okhttp/3.10.0',
    'app-user-device-id': '291b226282010337c9443590d6457be15',
    'app-version-code': '112'
};
 
let parseMap = {};
let homeVods = [];
let Searchstatus = false;
let searchApiSuffix = '';
let souParamName = '';
let souSalt = '';
let extraSearchHeaders = {};
let initSuffix = 'init';
let hasCustomInit = false;
let thirdDanmuBaseUrl = '';
let customPlayUa = ''; // 新增：自定义播放链接UA

let request = async (reqUrl, data, header, method) => {
    let finalHeaders = { ...headers };
    if (enableVerifyTimeSign) {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const sign = aesEncode(timestamp, key, iv);
        finalHeaders['app-api-verify-time'] = timestamp;
        finalHeaders['app-api-verify-sign'] = sign;
    }
    if (header) {
        finalHeaders = { ...finalHeaders, ...header };
    }
    let res = await req(reqUrl, {
        method: method || 'get',
        data: data || '',
        headers: finalHeaders,
        postType: method === 'post' ? 'form' : '',
        timeout: 10000,
    });
    return res.content;
};
 
let request_text = async (reqUrl, data, header, method, tobase64) => {
    let finalHeaders = { ...headers };
    if (enableVerifyTimeSign) {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const sign = aesEncode(timestamp, key, iv);
        finalHeaders['app-api-verify-time'] = timestamp;
        finalHeaders['app-api-verify-sign'] = sign;
    }
    if (header) {
        finalHeaders = { ...finalHeaders, ...header };
    }
    let optObj = {
        headers: finalHeaders,
        method: method || 'get',
        data: method === 'post' ? data : undefined,
        postType: method === 'post' ? (data ? 'raw' : 'form') : undefined,
        timeout: 10000,
    };
    if (tobase64) {
        optObj.buffer = 2;
    }
    let res = await req(reqUrl, optObj);
    return res.content;
};
 
async function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    if (!cfg.ext) return;
    let extObj;
    if (typeof cfg.ext === 'string') {
        extObj = JSON.parse(cfg.ext);
    } else if (typeof cfg.ext === 'object' && cfg.ext !== null) {
        extObj = cfg.ext;
    } else {
        return;
    }
    if (extObj.init && typeof extObj.init === 'string' && extObj.init.startsWith('V')) {
        initSuffix = 'init' + extObj.init;
        hasCustomInit = true;
    }
    if (extObj.time !== undefined) {
        const timeVal = String(extObj.time);
        enableVerifyTimeSign = (timeVal === '1' || timeVal === 'true' || timeVal === '1');
    }
    if (extObj.code !== undefined) {
        forceVerifyCode = String(extObj.code).trim();
    }
    // 新增：读取自定义播放UA
    if (extObj.ua2 !== undefined) {
        customPlayUa = String(extObj.ua2).trim();
    }
    if (extObj.head && typeof extObj.head === 'string') {
        const headStr = extObj.head.trim();
        if (headStr) {
            const items = headStr.split(',');
            for (let item of items) {
                const trimmed = item.trim();
                if (!trimmed) continue;
                const colonIndex = trimmed.indexOf(':');
                if (colonIndex > 0) {
                    const hKey = trimmed.substring(0, colonIndex).trim();
                    const hValue = trimmed.substring(colonIndex + 1).trim();
                    if (hKey && hValue) {
                        headers[hKey] = hValue;
                    }
                }
            }
        }
    }
    let host = extObj.host || '';
    if (host) {
        if (host.startsWith('http') && (host.endsWith('.txt') || host.endsWith('.json'))) {
            let response = await request(host, null, headers, 'get');
            let urls = response.split('\n').map(line => line.trim()).filter(line => line && line.startsWith('http'));
            if (urls.length > 0) {
                host = urls[0];
            }
        }
        siteUrl = host.replace(/\/+$/, '');
        if (!siteUrl.includes('php')) {
            siteUrl += '/api.php';
        }
    }
    key = extObj.key || '';
    iv = extObj.iv || key;
    if (extObj.api && prefixMap[extObj.api]) {
        apiPrefix = prefixMap[extObj.api];
    }
    if (extObj.version) {
        headers['app-version-code'] = String(extObj.version);
    }
    if (extObj.id) {
        headers['app-user-device-id'] = extObj.id;
    }
    if (extObj.token) {
        headers['app-user-token'] = extObj.token;
    }
    if (extObj.ua) {
        headers['User-Agent'] = extObj.ua;
    }
}
 
function processSignatureValue(sig) {
    if (sig.length < 8) {
        return sig.split('').reverse().join('');
    } else {
        let rear = sig.slice(-8).split('').reverse().join('');
        let front = sig.slice(0, -8).split('').reverse().join('');
        return front + rear;
    }
}
 
async function home(filter) {
    let initUrl = `${siteUrl}/${apiPrefix}/${initSuffix}`;
    let rets = JSON.parse(await request(initUrl)).data;
    let data = JSON.parse(aesDecode(rets, key, iv));
 
    let rawDanmuUrl = data.config?.third_danmu_url || '';
 
    if (Array.isArray(rawDanmuUrl)) {
        rawDanmuUrl = rawDanmuUrl.find(u => u && typeof u === 'string' && u.trim()) || '';
    } else if (typeof rawDanmuUrl !== 'string') {
        rawDanmuUrl = '';
    }
 
    if (rawDanmuUrl) {
        thirdDanmuBaseUrl = rawDanmuUrl.trim();
        let lower = thirdDanmuBaseUrl.toLowerCase();
        if (!lower.match(/[?&]url=$/)) {
            thirdDanmuBaseUrl += thirdDanmuBaseUrl.includes('?') ? '&url=' : '?url=';
        }
    } else {
        thirdDanmuBaseUrl = 'https://dmku.hls.one/?ac=dm&url='; 
    }
 
    if (data.box_config) {
        let originalKey = key;
        let swappedKey = originalKey.split('').reverse().join('');
        let md5Key = md5(swappedKey);
        let dynamicIv = md5Key.substring(0, 16);
        let decrypted = aesDecode(data.box_config, swappedKey, dynamicIv);
        let boxJson = JSON.parse(decrypted);
        if (boxJson.search_name) {
            searchApiSuffix = boxJson.search_name;
        }
        if (boxJson.signature_name && boxJson.signature_value) {
            souParamName = boxJson.signature_name;
            souSalt = processSignatureValue(boxJson.signature_value);
        }
        if (boxJson.api_header && boxJson.api_header.key && boxJson.api_header.value) {
            extraSearchHeaders[boxJson.api_header.key] = boxJson.api_header.value;
        }
    } else {
        searchApiSuffix = 'searchList';
        souParamName = '';
        souSalt = '';
    }
 
    Searchstatus = data.config?.system_search_verify_status || false;
 
    let filters = {};
    let classes = [];
    homeVods = [];
 
    _.forEach(data.type_list, item => {
        if (item.type_id > 0) {
            if (item.recommend_list && Array.isArray(item.recommend_list)) {
                homeVods = homeVods.concat(item.recommend_list);
            }
        }
 
        classes.push({
            type_id: item.type_id,
            type_name: item.type_name,
        });
 
        let filterList = [];
        _.forEach(item.filter_type_list, f => {
            let filter = {};
            if (f.name === 'class') {
                filter['name'] = '分类';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'area') {
                filter['name'] = '区域';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'lang') {
                filter['name'] = '语言';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'year') {
                filter['name'] = '年份';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'sort') {
                filter['name'] = '排序';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (Object.keys(filter).length > 0) {
                filterList.push(filter);
            }
        });
        if (filterList.length > 0) {
            filters[item.type_id] = filterList;
        }
    });
 
    return JSON.stringify({
        'class': classes,
        'filters': filters,
    });
}
 
async function homeVod() {
    return JSON.stringify({
        list: homeVods,
    });
}
 
async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    let url = `${siteUrl}/${apiPrefix}/typeFilterVodList`;
    let params = {
        "area": extend['area'] || "全部",
        "sort": extend['sort'] || "最新",
        "class": extend['class'] || "全部",
        "type_id": tid,
        "year": extend['year'] || "全部",
        "lang": extend['lang'] || '全部',
        "page": pg,
    };
    let encData = JSON.parse(await request(url, params, '', 'post')).data;
    let videos = JSON.parse(aesDecode(encData, key, iv)).recommend_list;
    return JSON.stringify({
        page: pg,
        pagecount: 9999,
        list: videos,
    });
}
 
async function detail(id) {
    let url = `${siteUrl}/${apiPrefix}/vodDetail`;
    let resp = await request(url, { vod_id: id }, '', 'post');
    let jsonResp = JSON.parse(resp);
    let encData = jsonResp.data;
    let decoded = aesDecode(encData, key, iv);
    let info = JSON.parse(decoded);
    let videos = {
        vod_id: info.vod.vod_id,
        vod_name: info.vod.vod_name,
        vod_area: info.vod.vod_area,
        vod_director: info.vod.vod_director,
        vod_actor: info.vod.vod_actor,
        vod_pic: info.vod.vod_pic,
        vod_content: info.vod.vod_content,
        type_name: info.vod.vod_class,
        vod_year: info.vod.vod_year 
    };
    let froms = [];
    let urls = [];
    let playSources = _.map(info.vod_play_list, item => {
        const playerInfo = item.player_info || {};
        const parse = playerInfo.parse || '';
        const ua = playerInfo.user_agent || customPlayUa || ''; // 修改：优先使用自定义UA，如果没有则使用原有的
        const nameUrls = _.map(item.urls || [], item2 => {
            const { name = '', url = '', token = '', parse_api_url = '', nid = 1 } = item2;
            return `${name}$${url}@@${parse}@@${token}@@${parse_api_url}@@${ua}@@${info.vod.vod_id}@@${nid}`;
        }).join('#');
        return {
            show: playerInfo.show || 'Unknown',
            urls: nameUrls 
        };
    });
    let showCount = {};
    playSources = _.map(playSources, source => {
        let showName = source.show;
        if (showCount[showName]) {
            showCount[showName]++;
            showName = `${showName}${showCount[showName]}`;
        } else {
            showCount[showName] = 1;
        }
        return {
            show: showName,
            urls: source.urls 
        };
    });
    playSources.sort((a, b) => {
        const aShow = a.show.toLowerCase();
        const bShow = b.show.toLowerCase();
        const getPriority = (show) => {
            if (show.includes('4k')) return 1;
            if (show.includes('K')) return 2;
            if (show.includes('独家')) return 3;
            if (show.includes('秒播')) return 4;
            if (show.includes('自建')) return 5;
            if (show.includes('蓝光')) return 6;
            if (show.includes('专线')) return 7;
            return 8;
        };
        return getPriority(aShow) - getPriority(bShow);
    });
    froms = _.map(playSources, source => source.show);
    urls = _.map(playSources, source => source.urls);
    videos.vod_play_from = froms.join('$$$');
    videos.vod_play_url = urls.join('$$$');
    return JSON.stringify({
        list: [videos],
    });
}
 
async function play(flag, id, flags) {
    let parts = id.split('@@');
    let playUrl = parts[0];
    let parse = parts[1] || '';
    let token = parts[2] || '';
    let parse_api_url = parts[3] || '';
    let ua = parts[4] || ''; // 新增：获取UA
    let vodId = parts[5] || '';
    let nidStr = parts[6] || '1';
    
    let danmakuUrl = '';
    if (thirdDanmuBaseUrl && vodId) {
        let nid = parseInt(nidStr, 10);
        if (isNaN(nid) || nid < 1) nid = 1;
        let urlPosition = nid - 1;
        let danmuParams = {
            url_position: urlPosition.toString(),
            vod_id: vodId 
        };
        let danmuRet = await request(`${siteUrl}/${apiPrefix}/danmuList`, danmuParams, '', 'post');
        let danmuResponse = JSON.parse(danmuRet);
        if (danmuResponse.data) {
            let decryptedDanmu = JSON.parse(aesDecode(danmuResponse.data, key, iv));
            if (decryptedDanmu && decryptedDanmu.official_url) {
                let realDanmuUrl = thirdDanmuBaseUrl + decryptedDanmu.official_url;
                let EncodedUrl = encodeURIComponent(realDanmuUrl);
                let headerJson = JSON.stringify(headers);
                danmakuUrl = js2Proxy(
                    false,
                    siteType,
                    siteKey || '',
                    EncodedUrl,
                    headers
                );
            }
        }
    }
 
    // 修改：如果存在自定义UA，添加到返回参数中
    if (
        (playUrl.includes('http://') || playUrl.includes('https://')) &&
        (playUrl.includes('m3u8') || playUrl.includes('mp4') || playUrl.includes('mkv')) &&
    !parse_api_url
    ) {
        let result = {
            parse: 0,
            url: playUrl,
            danmaku: danmakuUrl
        };
        // 如果存在自定义UA，添加到返回结果中
        if (ua) {
            result.header = { 'User-Agent': ua };
        }
        return JSON.stringify(result);
    }
    if (parse.startsWith("http")) {
        let parseUrl = parse + playUrl;
        if (token) {
            parseUrl += '&token=' + token;
        }
        // 如果存在自定义UA，在请求解析接口时使用
        let requestHeaders = {};
        if (ua) {
            requestHeaders['User-Agent'] = ua;
        }
        let rets = await request(parseUrl, null, requestHeaders, 'get');
        if (rets.indexOf('DOCTYPE html') > -1) {
            let result = {
                parse: 1,
                url: parseUrl,
                danmaku: danmakuUrl
            };
            if (ua) {
                result.header = { 'User-Agent': ua };
            }
            return JSON.stringify(result);
        }
        let parseJson = JSON.parse(rets);
        let result = {
            parse: 0,
            url: parseJson['url'] || parseJson['data']['url'] || '',
            danmaku: danmakuUrl
        };
        // 如果存在自定义UA，添加到返回结果中
        if (ua) {
            result.header = { 'User-Agent': ua };
        }
        return JSON.stringify(result);
    }
    let params = {
        'parse_api': parse,
        'url': aesEncode(playUrl, key, iv),
        'token': token,
    };
    // 如果存在自定义UA，在请求时使用
    let requestHeaders = {};
    if (ua) {
        requestHeaders['User-Agent'] = ua;
    }
    let rets = await request(`${siteUrl}/${apiPrefix}/vodParse`, params, requestHeaders, 'post');
    let urlDecoded = aesDecode(JSON.parse(rets).data, key, iv);
    let finalPlayUrl = '';
    let parsed = JSON.parse(urlDecoded);
    finalPlayUrl = JSON.parse(parsed.json).url || '';
    let result = {
        parse: 0,
        url: finalPlayUrl,
        danmaku: danmakuUrl 
    };
    // 如果存在自定义UA，添加到返回结果中
    if (ua) {
        result.header = { 'User-Agent': ua };
    }
    return JSON.stringify(result);
}
 
async function search(wd, quick, pg) {
    if (hasCustomInit) {
        await home({});
    }
    let searchPath = searchApiSuffix || 'searchList';
    let url = `${siteUrl}/${apiPrefix}/${searchPath}`;
    let retryCount = 0;
    const maxRetries = 1;
    let videos = [];
    let attemptedCaptcha = false;
    let attemptedSlider = false;
    let sliderVerified = false;
    let sliderId = '';
    
    let params = {
        'page': '1',
        'type_id': '0',
        'keywords': wd,
    };
    
    if (souParamName && souSalt) {
        const currentTimestamp = Math.floor(Date.now() / 1000).toString();
        const souString = `/${souParamName}-${currentTimestamp}-sb-0-${souSalt}`;
        const md5Value = md5(souString);
        const finalValue = `${currentTimestamp}-sb-0-${md5Value}`;
        params[souParamName] = finalValue;
    }
    
    let searchHeaders = { ...headers, ...extraSearchHeaders };
    
    if (forceVerifyCode) {
        params['code'] = forceVerifyCode;
        const random_uuid = generateUUID();
        params['key'] = random_uuid;
    }
    
    const maxWaitRetries = 2;
    let waitRetryCount = 0;
    
    while (true) {
        let encData = await request(url, params, searchHeaders, 'post');
        let response = JSON.parse(encData);
        
        if (response.code === 1001 && response.need_slider === true && !attemptedSlider) {
            attemptedSlider = true;
            
            let getSliderUrl = `${siteUrl}/${apiPrefix}/getSlider`;
            let sliderResponse = await request(getSliderUrl, {}, searchHeaders, 'post');
            let sliderJson = JSON.parse(sliderResponse);
            
            if (sliderJson.code === 1 && sliderJson.data) {
                let sliderDecrypted = aesDecode(sliderJson.data, key, iv);
                let sliderData = JSON.parse(sliderDecrypted);
                
                sliderId = sliderData.slider_id || '';
                let targetX = parseInt(sliderData.target_x) || 0;
                let targetY = parseInt(sliderData.target_y) || 0;
                
                if (sliderId && targetX > 0) {
                    let posX = targetX;
                    if (targetX > 0) {
                        let randomOffset = Math.floor(Math.random() * 3) - 1;
                        posX = targetX + randomOffset;
                        if (posX < 1) posX = 1;
                        if (posX > (sliderData.bg_width || 280)) posX = sliderData.bg_width || 280;
                    }
                    
                    let timestamp = Date.now();
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    let verifyParams = {
                        pos_x: posX.toString(),
                        slider_id: sliderId,
                        timestamp: timestamp.toString()
                    };
                    
                    let verifySliderUrl = `${siteUrl}/${apiPrefix}/verifySlider`;
                    let verifyResponse = await request(verifySliderUrl, verifyParams, searchHeaders, 'post');
                    let verifyJson = JSON.parse(verifyResponse);
                    
                    if (verifyJson.code === 1 && verifyJson.data) {
                        let verifyDecrypted = aesDecode(verifyJson.data, key, iv);
                        let verifyResult = JSON.parse(verifyDecrypted);
                        
                        if (verifyResult.verified === true) {
                            sliderVerified = true;
                            continue;
                        }
                    }
                }
            }
            
            if (!sliderVerified) {
                if (!forceVerifyCode && (Searchstatus || (response.code === 0 && response.msg && response.msg.includes('验证码')))) {
                    if (attemptedCaptcha) break;
                    attemptedCaptcha = true;
                    const random_uuid = generateUUID();
                    let modifiedApiPrefix = apiPrefix.replace('.index', '');
                    let verifyUrl = `${siteUrl}/${modifiedApiPrefix}.verify/create?key=${random_uuid}`;
                    let base64Img = await request_text(verifyUrl, null, headers, 'get', true);
                    base64Img = base64Img.replace(/\n/g, '');
                    let ocrResult = await request_text('https://api.nn.ci/ocr/b64/text',   base64Img, { 'User-Agent': 'okhttp/3.10.0' }, 'post');
                    params['code'] = ocrResult.trim();
                    params['key'] = random_uuid;
                    retryCount++;
                    continue;
                } else {
                    break;
                }
            }
        }
        
        if (response.code === 0 &&
            (!response.data || response.data.length === 0) &&
            response.msg &&
            /等.*秒|等待.*秒|等|搜|请等待|稍等|稍候/i.test(response.msg)) {
            if (waitRetryCount >= maxWaitRetries) break;
            let waitSeconds = extractWaitTime(response.msg);
            if (waitSeconds < 1) waitSeconds = 2;
            if (waitSeconds > 30) waitSeconds = 30;
            const actualWait = waitSeconds + 1;
            await new Promise(resolve => setTimeout(resolve, actualWait * 1000));
            waitRetryCount++;
            continue;
        }
        
        if (response.data && response.data.length > 0) {
            let decodedData = JSON.parse(aesDecode(response.data, key, iv));
            videos = decodedData.search_list || [];
            break;
        } else if (!forceVerifyCode && (Searchstatus || (response.code === 0 && response.msg && response.msg.includes('验证码')))) {
            if (attemptedCaptcha) break;
            attemptedCaptcha = true;
            const random_uuid = generateUUID();
            let modifiedApiPrefix = apiPrefix.replace('.index', '');
            let verifyUrl = `${siteUrl}/${modifiedApiPrefix}.verify/create?key=${random_uuid}`;
            let base64Img = await request_text(verifyUrl, null, headers, 'get', true);
            base64Img = base64Img.replace(/\n/g, '');
            let ocrResult = await request_text('https://api.nn.ci/ocr/b64/text',   base64Img, { 'User-Agent': 'okhttp/3.10.0' }, 'post');
            params['code'] = ocrResult.trim();
            params['key'] = random_uuid;
            retryCount++;
            continue;
        } else {
            break;
        }
    }
    
    return JSON.stringify({
        list: videos,
    });
}
 
function generateUUID() {
    const chars = '0123456789abcdef';
    const uuidTemplate = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return uuidTemplate.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return chars[v];
    });
}
 
function aesDecode(str, keyStr, ivStr, type) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    if (type === 'hex') {
        str = Crypto.enc.Hex.parse(str);
        return Crypto.AES.decrypt({
            ciphertext: str
        }, key, {
            iv: Crypto.enc.Utf8.parse(ivStr),
            mode: Crypto.mode.CBC,
            padding: Crypto.pad.Pkcs7 
        }).toString(Crypto.enc.Utf8);
    } else {
        return Crypto.AES.decrypt(str, key, {
            iv: Crypto.enc.Utf8.parse(ivStr),
            mode: Crypto.mode.CBC,
            padding: Crypto.pad.Pkcs7
        }).toString(Crypto.enc.Utf8);
    }
}
 
function aesEncode(str, keyStr, ivStr, type) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    let encData = Crypto.AES.encrypt(str, key, {
        iv: Crypto.enc.Utf8.parse(ivStr),
        mode: Crypto.mode.CBC,
        padding: Crypto.pad.Pkcs7 
    });
    if (type === 'hex') return encData.ciphertext.toString(Crypto.enc.Hex);
    return encData.toString();
}
 
function md5(text) {
    return Crypto.MD5(text).toString();
}
 
function chineseToNumber(chineseStr) {
    const chineseNumMap = {
        '零': 0, '〇': 0, '一': 1, '壹': 1, '二': 2, '贰': 2, '两': 2,
        '三': 3, '叁': 3, '四': 4, '肆': 4, '五': 5, '伍': 5,
        '六': 6, '陆': 6, '七': 7, '柒': 7, '八': 8, '捌': 8,
        '九': 9, '玖': 9, '十': 10, '拾': 10 
    };
   
    if (chineseStr.length === 1) {
        return chineseNumMap[chineseStr] || 2;
    }
   
    if (chineseStr.startsWith('十') && chineseStr.length === 2) {
        const units = chineseNumMap[chineseStr[1]];
        return units ? 10 + units : 10;
    }
   
    if (chineseStr.endsWith('十') && chineseStr.length === 2) {
        const tens = chineseNumMap[chineseStr[0]];
        return tens ? tens * 10 : 10;
    }
   
    if (chineseStr.length === 3 && chineseStr.includes('十')) {
        const tens = chineseNumMap[chineseStr[0]];
        const units = chineseNumMap[chineseStr[2]];
        return tens && units ? tens * 10 + units : (tens ? tens * 10 : 10);
    }
   
    return 2;
}
 
function extractWaitTime(message) {
    const digitMatch = message.match(/(\d+)\s*秒/);
    if (digitMatch && digitMatch[1]) {
        return parseInt(digitMatch[1], 10);
    }
   
    const chineseMatch = message.match(/([零一二三四五六七八九十两壹贰叁肆伍陆柒捌玖拾〇]+)\s*秒/);
    if (chineseMatch && chineseMatch[1]) {
        return chineseToNumber(chineseMatch[1]);
    }
   
    if (/几秒|数秒|若干秒/i.test(message)) {
        return 3;
    }
   
    return 2;
}
 
function hexToDec(hex) {
    hex = (hex || '#FFFFFF').replace(/^#/, '').toUpperCase();
    if (hex.length !== 6) {
        while (hex.length < 6) hex += '0';
        hex = hex.slice(0, 6);
    }
    return parseInt(hex, 16);
}
 
function escapeXml(str) {
    if (typeof str !== 'string') return '';
    return str 
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}
 
function jsonDanmakuToXml(json) {
    if (!json || !json.danmuku || !Array.isArray(json.danmuku)) {
        return '<?xml version="1.0" encoding="utf-8"?><i><code>0</code><id>error_no_danmaku</id></i>';
    }
    let lines = [];
    lines.push('<?xml version="1.0" encoding="utf-8"?>');
    lines.push('<i>');
    lines.push(` <code>${json.code || 0}</code>`);
    lines.push(` <id>${escapeXml(json.name || '12345')}</id>`);
    const positionMap = {
        'top': 5,
        'right': 1,
        'bottom': 4,
        'left': 6,
        'scroll': 1 
    };
    json.danmuku.forEach(danmu => {
        if (!Array.isArray(danmu) || danmu.length < 5) return;
        let [
            time = 0,
            mode = 'scroll',
            colorHex = '#FFFFFF',
            ,
            text = '',
            , ,
            fontSize = "24px"
        ] = danmu;
        colorHex = '#' + Array(6).fill(0).map(() => '0123456789ABCDEF'[Math.floor(Math.random() * 16)]).join('');
        
        let pos = positionMap[mode] || 1;
        let colorDec = hexToDec(colorHex);
        let fs = parseInt(String(fontSize).replace(/px/gi, '')) || 24;
        let p = `${Number(time).toFixed(3)},${pos},${fs},${colorDec},,,,,`;
        let safeText = escapeXml(text);
        lines.push(` <d p="${p}">${safeText}</d>`);
    });
    lines.push('</i>');
    return lines.join('\n');
}
 
async function proxy(params) {
    let jsonUrl = decodeURIComponent(
        params.url || params[0] || params.danmaku || '' || ''
    );
    if (!jsonUrl || !jsonUrl.startsWith('http')) {
        return JSON.stringify({
            code: 400,
            content: "缺少有效的弹幕 URL",
            headers: { "Content-Type": "text/plain" }
        });
    }
    let jsonContent = await request_text(jsonUrl, null, headers, 'get');
    let jsonObj = JSON.parse(jsonContent);
    let xmlContent = jsonDanmakuToXml(jsonObj);
    return JSON.stringify({
        code: 200,
        content: xmlContent,
        headers: {
            "Content-Type": "text/xml; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    });
}
 
let forceVerifyCode = null;
 
export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search,
        proxy: proxy 
    };
}