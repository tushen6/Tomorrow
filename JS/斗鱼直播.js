var rule = {
    title: '斗鱼直播',
    host: 'https://m.douyu.com',
    homeUrl: '/api/home/mix',//网站的首页链接,用于分类获取和推荐获取
    url: '/api/room/list?page=fypage&type=fyfilter',
    filterable: 1,//是否启用分类筛选,
    filter_url: '{{fl.cateId}}',
    filter: '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',
    filter_def: {
        yl: {cateId: 'yqk'},
        PCgame: {cateId: 'LOL'},
        djry: {cateId: 'TVgame'},
        syxx: {cateId: 'wzry'},
        yz: {cateId: 'yz'},
        kjwh: {cateId: 'smkj'},
        yp: {cateId: 'yiqiwan'},
        voice: {cateId: 'yyzs'},
        znl: {cateId: 'znl'}
    },
    class_name: '娱乐天地&网游竞技&单机热游&手游休闲&颜值&科技文化&语音互动&语音直播&正能量',// /api/cate/list
    class_url: 'yl&PCgame&djry&syxx&yz&kjwh&yp&voice&znl',
    detailUrl: 'http://live.yj1211.work/api/live/getRoomInfo?uid=&platform=douyu&roomId=fyid',// JustLive
    searchUrl: '/api/search/liveRoom?#did=10000000000000000000000000001501&limit=20&offset=0&sk=**;post',
    searchable: 2,
    quickSearch: 0,
    headers: {
        'User-Agent': 'MOBILE_UA'
    },
    timeout: 5000,
    limit: 8,
    play_parse: true,
    lazy: '',
    推荐: `js:
        let d = [];
        let jo = JSON.parse(request(input)).data;
        jo.forEach((it,idex) => {
            let slist = jo[idex].list ;
            slist.forEach(it => {
                d.push({
                    url: it.rid,
                    title: it.roomName,
                    img: it.roomSrc,
                    desc: '👁' + it.hn + '  🆙' + it.nickname,
                })
            });
        });
        setResult(d);
    `,
    一级: `js:
        let d = [];
        let jo = JSON.parse(request(input)).data.list;
        jo.forEach(it => {
            d.push({
                url: it.rid,
                title: it.roomName,
                img: it.roomSrc,
                desc: '👁' + it.hn + '  🆙' + it.nickname,
            })
        });
        setResult(d);
    `,
    二级: `js:
    try {
        if (typeof play_url === "undefined") {
            var play_url = ""
        }
        var jo = JSON.parse(request(input)).data;
        VOD = {
            vod_id: jo.roomId,
            vod_name: jo.roomName,
            vod_pic: jo.roomPic,
            type_name: "斗鱼." + jo.categoryName,
            vod_director: '🆙 ' + jo.ownerName,
            vod_content: "🏷分区：斗鱼" + "·" + jo.categoryName + " 🏷UP主：" + jo.ownerName + " 🏷人气：" + jo.online + (jo.isLive === 1 ? " 🏷状态：正在直播" : "状态：未开播")
        };
        let episodes = JSON.parse(request("http://live.yj1211.work/api/live/getRealUrlMultiSource?platform=" + jo.platForm + "&roomId=" + jo.roomId)).data; //多线路
        if (Object.keys(episodes).length !== 0) {
            let playFrom = [];
            let playList = [];
            let kplayList = [];
            Object.keys(episodes).forEach(function(key) {
                playFrom.append(key);
                kplayList = episodes[key].map(function(it) {
                    let title = it.qualityName;
                    let playUrl = it.playUrl
                    return title + "$" + play_url + urlencode(playUrl)
                }).join("#")
                playList.append(kplayList);
            });
            let vod_play_from = playFrom.join("$$$");
            let vod_play_url = playList.join("$$$");
            VOD["vod_play_from"] = vod_play_from;
            VOD["vod_play_url"] = vod_play_url;
        } else {
            var d = [];
            episodes = JSON.parse(request("http://live.yj1211.work/api/live/getRealUrl?platform=" + jo.platForm + "&roomId=" + jo.roomId)).data; //单线路
            var name = {
                "OD": "原画",
                "FD": "流畅",
                "LD": "标清",
                "SD": "高清",
                "HD": "超清",
                "2K": "2K",
                "4K": "4K",
                "FHD": "全高清",
                "XLD": "极速",
                "SQ": "普通音质",
                "HQ": "高音质"
            };
            Object.keys(episodes).forEach(function(key) {
                if (!/ayyuid|to/.test(key)) {
                    d.push({
                        title: name[key],
                        url: episodes[key]
                    })
                }
            });
            d.push(
                {
                    title: "解析1",
                    url: "http://epg.112114.xyz/huya/" + jo.roomId
                },
                {
                    title: "解析2",
                    url: "https://www.aois.eu.org/live/huya/" + jo.roomId
                },
                {
                    title: "解析3",
                    url: "https://www.goodiptv.club/huya/" + jo.roomId
                },
                {
                    title: "解析4",
                    url: "http://maomao.kandiantv.cn/huya1.php?id=" + jo.roomId
                },
                {
                    title: "解析5",
                    url: "http://43.138.170.29:35455/huya/" + jo.roomId
                },
                {
                    title: "解析6",
                    url: "http://8.210.232.168/php/huya.php?id=" + jo.roomId
                },
            );
            VOD["vod_play_from"] = "播放源";
            VOD["vod_play_url"] = d.map(function(it) {
                return it.title + "$" + it.url
            }).join("#");
            setResult(d);
        }
    } catch (e) {
        log("获取二级详情页发生错误:" + e.message);
    }
    `,
    // 搜索:'json:data.list;roomName;roomSrc;nickname;roomId',
    搜索: `js:
        var d = [];
        let rurls = input.split(';')[0].split('#');
        let rurl = rurls[0];
        let params = rurls.length > 1 ?rurls[1]:'';
        let _fetch_params = JSON.parse(JSON.stringify(rule_fetch_params));
        let postData = {body:params};
        Object.assign(_fetch_params,postData);
        let jo = JSON.parse(post(rurl,_fetch_params)).data.list;
        jo.forEach(it => {
            d.push({
                url: it.roomId,
                title: it.roomName,
                img: it.roomSrc,
                desc: '👁' + it.hn + '  🆙' + it.nickname,
            })
        });
        setResult(d);
    `,

    //是否启用辅助嗅探: 1,0
    sniffer: 1,
    // 辅助嗅探规则js写法
    isVideo: `js:
        log(input);
        if(/\\/huya/.test(input)) {
            input = true
        } else if(/\\.flv?|\\.m3u8?|\\.mp4?/.test(input)){
            input = true
        }else{
            input = false
        }
    `,
}
