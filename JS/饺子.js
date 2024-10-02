var rule = {
   模板: '首图',
   title: '饺子影院',
   host: 'https://www.jiaozi.me',
   url: '/mlist/indexfyclass-fypage.html',
   searchUrl: '/search.php?page=fypage&searchword=**&searchtype=',
   class_parse: '.myui-header__menu li;a&&Text;a&&href;index(\\d+)\.html',
   lazy: ``,
}