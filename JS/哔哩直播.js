/**
 * 影视TV 弹幕支持
 * https://t.me/fongmi_offical/
 * https://github.com/FongMi/Release/tree/main/apk
 * 皮皮虾DMBox 弹幕支持
 * 设置 > 窗口预览 > 开启
 * https://t.me/pipixiawerun
 * vod_area:'bililivedanmu'
 * Cookie设置
 * Cookie获取方法 https://ghproxy.net/https://raw.githubusercontent.com/UndCover/PyramidStore/main/list.md
 * Cookie设置方法1: DR-PY 后台管理界面
 * CMS后台管理 > 设置中心 > 环境变量 > {"bili_cookie":"XXXXXXX","vmid":"XXXXXX"} > 保存
 * Cookie设置方法2: 手动替换Cookie
 * 底下代码 headers的
 * "Cookie":"$bili_cookie"
 * 手动替换为
 * "Cookie":"将获取的Cookie黏贴在这"
 */

var rule = {
    title: '哔哩直播',
    host: 'https://api.live.bilibili.com',
    homeUrl: '/xlive/web-interface/v1/second/getUserRecommend?page=1&page_size=30&platform=web',//用于"分类获取"和"推荐获取"
    url: '/xlive/web-interface/v1/second/getList?platform=web&parent_area_id=fyclass&area_id=fyfilter&sort_type=online&page=fypage',
    class_name: '生活&网游&手游&单机游戏&娱乐&电台&虚拟主播&聊天室&知识&赛事&帮我玩&互动玩法&购物',
    class_url: '10&2&3&6&1&5&9&14&11&13&301&15&300',
    filterable: 1,
    filter_url: '{{fl.area}}',
    filter_def: {
        10: {area: '624'},
        2: {area: '86'},
        3: {area: '35'},
        6: {area: '236'},
        1: {area: '21'},
        5: {area: '190'},
        9: {area: '744'},
        14: {area: '818'},
        11: {area: '376'},
        13: {area: '562'},
        301: {area: '301000'},
        15: {area: ''},
        300: {area: '300000'}
    },
    filter: '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',
    detailUrl: 'https://live.bilibili.com/fyid',//二级详情拼接链接(json格式用)
    // detailUrl:'https://api.live.bilibili.com/xlive/web-room/v1/playUrl/playUrl?cid=fyid&platform=h5&otype=json&quality=0',//二级详情拼接链接(json格式用)
    // searchUrl:'/x/web-interface/search/type?__refresh__=true&page=fypage&page_size=42&order=online&platform=pc&highlight=1&single_column=0&keyword=**&search_type=live&dynamic_offset=0&preload=true',
    searchUrl: 'https://api.bilibili.com/x/web-interface/search/type?search_type=live&keyword=**&page=fypage',
    searchable: 2,
    quickSearch: 0,
    headers: {
        "User-Agent": "PC_UA",
        "Referer": "https://www.bilibili.com",
        // "Cookie":"$bili_cookie"
        "Cookie": "http://127.0.0.1:9978/file/TVBox/bilibili.txt"
    },
    timeout: 5000,
    limit: 8,
    play_parse: true,
    // play_json:[{re:'*', json:{jx:0, parse:1,header:JSON.stringify({"user-agent":"Mozilla/5.0 (Linux; U; Android 9; zh-CN; MI 9 Build/PKQ1.181121.001) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.108 UCBrowser/12.5.5.1035 Mobile Safari/537.36"})}}],
    // play_json:[{re:'*', json:{jx:0, parse:1,header:JSON.stringify({"user-agent":"uc_ua"})}}],
    // play_json:0,
    lazy: `js:
        let ids = input.split('_');
        let dan = 'https://api.bilibili.com/x/v1/dm/list.so?oid=' + ids[1];
        let result = {};
        let iurl = 'https://api.live.bilibili.com/room/v1/Room/playUrl?cid=' + ids[1] + '&' + ids[0];
        let html = request(iurl);
        let jRoot = JSON.parse(html);
        let jo = jRoot['data'];
        let ja = jo['durl'];
        let purl = '';
        if (ja.length > 0) {
            purl = ja[0]['url']
        }
        result['parse'] = 0;
        result['playUrl'] = '';
        result['url'] = unescape(purl);
        result['header'] = {
            Referer: 'https://live.bilibili.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
        };
        result['danmaku'] = dan;
        if (/h5/.test(ids[0])) {
            result['contentType'] = '';
            input = result
        } else {
            result['contentType'] = 'video/x-flv';
            input = result
        }
    `,
    double: false,
    推荐: '*',
    // 一级:'json:data.list;title;system_cover;uname;roomid',
    一级: `js:
        var d = [];
        let html = request(input);
        html = JSON.parse(html).data.list;
        html.forEach(it => {
            let pic = it.system_cover;
            if (pic.startsWith('/')) {
                pic = urljoin2(input, pic)
            }
            d.push({
                title: it.title,
                img: pic,
                desc: '👁' + it.watched_show.text_small + '  🆙' + it.uname,
                url: it.roomid
            })
        });
        setResult(d);
    `,
    // 二级:'*',
    二级: "js:let aid=input.match(/\\/(\\d+)/)[1];log(aid);let html=request('https://api.live.bilibili.com/room/v1/Room/get_info?room_id='+aid);let jo=JSON.parse(html).data;let title=jo['title'];let pic=jo['keyframe'];let desc=jo['description'];let dire=jo['uid'];let typeName=jo['area_name'];let remark='在线人数:'+jo['online'];let vod={vod_id:aid,vod_name:title,vod_pic:pic,type_name:typeName,vod_area:'bililivedanmu',vod_remarks:remark,vod_actor:'直播间id-'+aid,vod_director:dire,vod_content:desc};vod['vod_play_from']='B站';vod['vod_play_url']='flv线路原画$platform=web&quality=4_'+aid+'#flv线路高清$platform=web&quality=3_'+aid+'#h5线路原画$platform=h5&quality=4_'+aid+'#h5线路高清$platform=h5&quality=3_'+aid;VOD=vod;",
    // 搜索:'json:data.result.live_room;title;cover;uname;roomid',
    搜索: `js:let html=request(input);let msg=JSON.parse(html).message;if(msg!=="0"){VODS=[{vod_name:KEY+"➢"+msg,vod_id:"no_data",vod_remarks:"别点,缺少bili_cookie",vod_pic:"https://ghproxy.net/https://raw.githubusercontent.com/hjdhnx/dr_py/main/404.jpg"}]}else{let videos=[];let vodList=JSON.parse(html).data.result.live_room;vodList.forEach(function(vod){let aid=vod["roomid"];let title="直播间："+vod["title"].replace(\'<em class="keyword">\',"").replace("</em>","");let img="https:"+vod["user_cover"];let remark=vod["watched_show"]["text_small"]+"  "+vod["uname"];videos.push({vod_id:aid,vod_name:title,vod_pic:img,vod_remarks:remark})});VODS=videos}`,
    // 预处理:'if(rule_fetch_params.headers.Cookie.startsWith("http")){rule_fetch_params.headers.Cookie=fetch(rule_fetch_params.headers.Cookie);setItem(RULE_CK,cookie)};log(rule_fetch_params.headers.Cookie)',
}