# FC2 Magnet Fetch

批量收集 FC2 编号并检索对应链接。

灵感来自 [fc2_gather](https://github.com/supsupsuperstar/fc2_gather)，在此基础上增加了：

- Cookie 强制校验（未配置不启动）
- 分类筛选 + 指定数量抓取
- 链接获取支持 `Ctrl+C` 中断
- 配置文件自动生成与本地缓存管理

## 参数配置

首次运行前请确认根目录存在 `config.ini`。若不存在，可复制 `config.ini.example` 为 `config.ini`，或直接运行程序自动生成模板。

必须配置：

- `PHPSESSID`
- `fcu`

获取方式：

1. 浏览器登录 https://adult.contents.fc2.com/
2. 打开开发者工具（F12）
3. 在 Cookies 中复制 `CONTENTS_FC2_PHPSESSID` 与 `fcu`

## 运行方式

```bash
python src/fc2_magnet_fetch.py
```

## 菜单说明

程序启动后可用菜单：

- `1` 分类筛选获取（指定数量）
- `2` 分类筛选获取（全部）
- `3` 手动输入页面 URL 获取
- `4` 根据 `list.txt` 获取链接（支持 `Ctrl+C` 中断）
- `5` 预览 `list.txt`
- `6` 临时更新 Cookie（仅当前运行有效）
- `q` 退出

## 分类筛选说明

- 支持输入一个或多个分类编号，空格或逗号分隔（如：`30 42`）
- 支持输入 `all` 或 `0` 一次性全选
- 非法编号会自动忽略并提示
- 选择后会自动生成搜索 URL

说明：分类具体名称仅在程序内显示，文档中不展开列出。

## 缓存文件

程序会在下载目录（默认 `./Downloads/`）写入：

- `list.txt`：收集到的编号
- `magnet.txt`：已获取到的链接
- `no_magnet.txt`：未检索到结果的编号
- `error.txt`：请求失败的编号

## 注意事项

- 数据来源：<https://adult.contents.fc2.com/>、<https://sukebei.nyaa.si/>
- 请合理控制请求频率，避免高并发或长时间连续抓取
- 网络环境受限时请配置代理
- Cookie 过期后需重新填写
- `config.ini` 已加入 `.gitignore`，不会被提交

## 免责声明

本项目仅用于技术交流与学习，不提供任何资源存储或分发服务。请遵守当地法律法规与站点条款。
