# FC2 Magnet Fetch

一个本地运行的小工具，用于按分类收集 FC2 编号，并检索对应链接。项目提供 CLI 和 Tkinter GUI 两种入口。

## 相关鸣谢
灵感来源https://github.com/supsupsuperstar/fc2_gather
感谢提供

## 功能

- GUI 标签点选：点一下选择，再点一下取消
- 支持指定采集数量，`0` 表示不限制
- 支持运行中停止任务
- 支持浅色、深色、跟随系统主题
- 本地配置与运行输出默认不进入 Git
- <img width="1182" height="852" alt="image" src="https://github.com/user-attachments/assets/b01a743d-6cad-4f63-8140-730f0ffe0948" />


## 快速开始

1. 安装依赖：

```bash
pip install requests
```

2. 准备配置：

```bash
copy config.ini.example config.ini
```

3. 在 `config.ini` 填入站点登录后的会话字段。

4. 启动 GUI：

```bash
python src/run_gui.py
```

CLI 入口仍然保留：

```bash
python src/fc2_magnet_fetch.py
```

## GUI 用法

1. 填写会话字段，点击 `应用 Cookie`
2. 在标签区点选分类，或切换到 `手动 URL`
3. 填写数量，点击 `采集编号`
4. 采集完成后点击 `检索链接`
5. 在底部结果区查看日志和输出文件

## 目录结构

```text
fc2_magnet/
├─ Downloads/                 # 运行输出，已忽略
├─ src/
│  ├─ fc2_magnet_fetch.py     # CLI 入口
│  ├─ run_gui.py              # GUI 入口
│  └─ fc2_gui/
│     ├─ config.py            # 配置加载/保存
│     ├─ constants.py         # 常量
│     ├─ service.py           # 请求、解析、文件写入
│     └─ gui.py               # Tkinter 界面
├─ config.ini.example         # 配置模板
└─ README.md
```

## 输出文件

默认输出到 `Downloads/`：

- `list.txt`：采集到的编号
- `magnet.txt`：检索到的链接
- `no_magnet.txt`：未检索到结果的编号
c

## 最后磁力链接下载
- 可以使用https://github.com/qbittorrent/qBittorrent

## 隐私与提交注意

以下内容不要提交到仓库：

- `config.ini`
- Cookie、会话字段、账号信息
- `Downloads/` 下的运行结果
- `.env`、日志、临时缓存、`__pycache__`

项目已经在 `.gitignore` 中默认忽略这些文件。推送前建议执行：

```bash
git status --short
```

确认没有本地配置、个人路径或运行结果进入待提交列表。

## 免责声明

本项目仅用于技术交流与学习。请遵守当地法律法规与目标站点条款，合理控制请求频率。
