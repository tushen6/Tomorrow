var rule = {
    title: '柒豪',
    host: 'https://misoso.cc/',
    headers: {
        'User-Agent': 'MOBILE_UA',
        'Referer': 'https://misoso.cc/'
    },
    编码: 'utf-8',
    timeout: 5000,
    url: '/search?q=fyclass&format=video&page=fypage',
    searchUrl: '/search?q=**&format=video&page=fypage',
    searchable: 2,
    quickSearch: 1,
    filterable: 1,
    play_parse: true,
    lazy: "js:\n        input = 'push://' + input;\n    ",
    limit: 9,
    double: true,

    网盘图标: {
        "百度网盘": "https://yx.aekgame.com/wp-content/uploads/2022/05/e27b-290abe63258be48d86b6676b6b0ba22d.jpg",
        "UC网盘": "https://web.wya6.com/d/wuyi/yxlz/Pictures/uc.jpg",
        "夸克网盘": "https://web.wya6.com/d/wuyi/yxlz/Pictures/quark.jpg",
        "天翼云盘": "https://img1.baidu.com/it/u=1260768763,814251560&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500",
        "默认图标": "https://picsum.photos/50/50"
    },

    获取网盘图标: (remark) => {
        remark = remark || '';
        if (/百度|bdwp|bdpan/i.test(remark)) return rule.网盘图标["百度网盘"];
        if (/夸克|quark/i.test(remark)) return rule.网盘图标["夸克网盘"];
        if (/天翼|电信|189/i.test(remark)) return rule.网盘图标["天翼云盘"];
        if (/UC|优视|阿里巴巴/i.test(remark)) return rule.网盘图标["UC网盘"];
        return rule.网盘图标["默认图标"];
    },

    // 统一屏蔽关键词列表（增强版）
    屏蔽关键词: () => [
        '阿里云盘', '阿里网盘', '115网盘', '115', '二维码', 'qrcode', '迅雷网盘', '迅雷云盘',
        '安装包', '绿色版', '破解版', '软件', '电脑版', '手机版', 'app',
        '扫码', 'apk', 'zip', 'rar', 'exe', '7z', 'tar', 'gz', 'iso', 'dmg',
        '安装教程', '教程', '公众号', '微信', '微博', '推广', '广告',
        'txt', '小说', '文档', '文本', '电子书', 'pdf', 'epub', 'mobi', '.flv'
    ],

    一级: `js:
        let html = fetch(input);
        let list = pdfa(html, "body&&.semi-space-medium-vertical");
        let 屏蔽词 = rule.屏蔽关键词();
        let 屏蔽正则 = new RegExp(屏蔽词.join('|'), 'i');
        
        VODS = list.map(x => {
            let remarks = pdfh(x, "div&&img&&alt") || '';
            let name = pdfh(x, "div&&a&&title") || '';
            let lowerText = (name + ' ' + remarks).toLowerCase();
            
            // 增强屏蔽逻辑：同时检查名称和备注
            if (屏蔽正则.test(lowerText)) {
                return null;
            }
            
            // 特别屏蔽TXT文件扩展名
            let url = pdfh(x, "div&&a&&href") || '';
            if (/\.txt$/.test(url.toLowerCase())) {
                return null;
            }
            
            let panType = "其他网盘";
            if (/百度|bdwp|bdpan/i.test(remarks)) panType = "百度网盘";
            else if (/夸克|quark/i.test(remarks)) panType = "夸克网盘";
            else if (/天翼|电信|189/i.test(remarks)) panType = "天翼云盘";
            else if (/UC|优视|阿里巴巴/i.test(remarks)) panType = "UC网盘";
            
            return {
                vod_name: name,
                vod_pic: rule.获取网盘图标(remarks),
                vod_remarks: remarks || '网盘资源',
                vod_content: remarks || '点击查看详情',
                vod_id: url,
                pan_type: panType
            };
        }).filter(x => x !== null);
    `,

    二级: {
        title: 'h1&&Text',
        img: 'img&&src',
        desc: `js:
            let desc = [];
            let info = pdfa(html, ".info-item");
            info.forEach(item => {
                desc.push(pdfh(item, "span&&Text"));
            });
            return desc.join('\n');
        `,
        content: 'body&&.content&&Text',
        tabs: "js:TABS = ['播放线路']",
        lists: `js:
            LISTS = [];
            let 屏蔽词 = rule.屏蔽关键词();
            let 屏蔽正则 = new RegExp(屏蔽词.join('|'), 'i');
            
            let sources = pdfa(html, "body&&.semi-space-loose-vertical").map(it => {
                let _tt = pdfh(it, "span&&title") || '';
                let _uu = pdfh(it, "a&&href") || '';
                
                // 检查标题和URL
                if (屏蔽正则.test(_tt.toLowerCase()) || /\.txt$/.test(_uu.toLowerCase())) {
                    return null;
                }
                
                let icon = rule.获取网盘图标(_tt);
                return _tt + '$' + _uu + '$' + icon;
            }).filter(x => x);
            
            LISTS.push(sources);
        `,
    },

    搜索: `js:
        let html = fetch(input);
        let list = pdfa(html, "body&&.semi-space-medium-vertical");
        let 屏蔽词 = rule.屏蔽关键词();
        let 屏蔽正则 = new RegExp(屏蔽词.join('|'), 'i');
        
        VODS = list.map(x => {
            let remarks = pdfh(x, "div&&img&&alt") || '';
            let name = pdfh(x, "div&&a&&title") || '';
            let lowerText = (name + ' ' + remarks).toLowerCase();
            
            if (屏蔽正则.test(lowerText)) {
                return null;
            }
            
            // 特别屏蔽TXT文件扩展名
            let url = pdfh(x, "div&&a&&href") || '';
            if (/\.txt$/.test(url.toLowerCase())) {
                return null;
            }
            
            let panType = "其他网盘";
            if (/百度|bdwp|bdpan/i.test(remarks)) panType = "百度网盘";
            else if (/夸克|quark/i.test(remarks)) panType = "夸克网盘";
            else if (/天翼|电信|189/i.test(remarks)) panType = "天翼云盘";
            else if (/UC|优视|阿里巴巴/i.test(remarks)) panType = "UC网盘";
            
            return {
                vod_name: name,
                vod_pic: rule.获取网盘图标(remarks),
                vod_remarks: remarks || '网盘资源',
                vod_content: remarks || '点击查看详情',
                vod_id: url,
                pan_type: panType
            };
        }).filter(x => x !== null);
    `,

    // 其他优化配置
    cate_exclude: '首页|留言|APP|下载|资讯|新闻|动态',
    tab_exclude: '猜你|喜欢|下载|剧情|榜|评论',
    类型: '影视',
    homeUrl: 'https://misoso.cc/',
    filter: {
        "pan_type": {
            "title": "网盘类型",
            "key": "pan_type",
            "value": [{
                    "n": "全部",
                    "v": ""
                },
                {
                    "n": "百度网盘",
                    "v": "百度网盘"
                },
                {
                    "n": "UC网盘",
                    "v": "UC网盘"
                },
                {
                    "n": "夸克网盘",
                    "v": "夸克网盘"
                },
                {
                    "n": "天翼云盘",
                    "v": "天翼云盘"
                },
            ]
        }
    }
};