# FC2 Magnet Fetch

批量收集FC2影片番号，获取磁力链接。

灵感来自 [fc2_gather](https://github.com/supsupsuperstar/fc2_gather)，在此基础上加了Cookie强制配置、指定数量获取、磁力获取可中断等功能。

## 参数配置

看 `config.ini`，没有的话把 `config.ini.example` 复制一份改成 `config.ini`。

必须填 `fcu` 和 `PHPSESSID`，不填跑不了。拿法：

1. 浏览器登录 https://adult.contents.fc2.com/
2. F12 → Application → Cookies
3. 复制 `CONTENTS_FC2_PHPSESSID` 和 `fcu` 的值填进去

## 缓存文件

| 文件 | 说明 |
|------|------|
| list.txt | 查找到的番号 |
| magnet.txt | 获取到的磁力链接 |
| no_magnet.txt | 没搜到磁力的番号 |
| error.txt | 网络等原因搜磁力失败的番号 |

## 使用说明

### 1. 获取番号列表

登录 https://adult.contents.fc2.com/ ，用分类标签或搜索功能筛选想要的影片，把页面URL复制到工具里，即可得到该分类下的所有番号。

菜单1可以指定要几个，菜单2是全要。

### 2. 获取磁力

自动从 sukebei 上搜索 list.txt 内所有番号的磁力链接。番号文件可以自己增删改，拿来查非FC2番号也行。

获取时按 Ctrl+C 能停，已拿到的不会丢。

## 注意事项

- 数据来源：https://adult.contents.fc2.com/ 、https://sukebei.nyaa.si/
- 别长时间、大批量、多线程抓，容易给服务器搞崩也容易封IP
- 国内用户需要设代理
- Cookie 会过期，过期了重新拿
- config.ini 在 gitignore 里，不会提交上去

## 免责声明

本应用仅用于爬虫技术交流学习，搜索结果均来自源站，不提供任何资源下载，亦不承担任何责任。
