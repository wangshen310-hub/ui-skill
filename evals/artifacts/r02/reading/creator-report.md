# 街巷之间

中文城市漫游随笔阅读器，按 ui-skill 固定版本 `01b2ad2` 独立生成。三篇示例文章完整保留，提供目录、收藏、前后篇、键盘操作与手机适配。收藏仅保存在当前设备浏览器，没有服务器同步。

## 产物位置

控制端：`/tmp/ui-skill-lab-20261020/round-0002-reading/`

腾讯云：`/opt/ui-skill-lab-20261020/round-0002-reading/`，SSH 别名 `tencent-opencloudos`。

- `source/`：最终可运行源码、package-lock、构建与预览脚本。
- `snapshots/initial-runnable-source.tar.gz`：首次可运行、尚未浏览器修正的源码。
- `snapshots/initial-desktop.png`：未修正初版的实际桌面截图。
- `snapshots/final-source.tar.gz`：最终源码包。
- `snapshots/site-dist-final.tar.gz`：最终可静态托管的 dist 包，含本地中文字体与字体许可证。
- `reference/desktop-reference.png`、`reference/prompt.txt`：生成参考与提示词。
- `DESIGN.md`：参考提取、响应式与交互规则。
- `tests/acceptance.py`：实际在腾讯云运行的浏览器验收脚本。
- `evidence/acceptance-results.json`、`evidence/acceptance.log`：最终实际结果。
- `evidence/initial-acceptance*`、`evidence/second-acceptance*`：前两轮原始失败记录。
- `evidence/artifact-sha256.txt`：源码与最终静态包的哈希。

`evidence/desktop.png` 为最终 1440×1000 桌面；`mobile.png` 和 `mobile-full.png` 为 390×844 手机；`mobile-320.png` 为 320×720 窄屏全页；`mobile-directory.png`、`saved-desktop.png`、`empty-saved-desktop.png`、`keyboard-focus.png` 保存目录、收藏和焦点状态。

## 构建与预览

所有实际构建、浏览器运行、截图和行为验收均在腾讯云执行。控制端只编辑、传输和查看产物。Node v20.20.2，npm 10.8.2；仅在本项目安装依赖，单次使用官方 npm registry，没有修改全局配置。

```bash
cd /opt/ui-skill-lab-20261020/round-0002-reading/source
npm ci --registry=https://registry.npmjs.org
npm run build
npm run preview
```

预览只绑定 `127.0.0.1:18865`。本次自行启动的预览已经停止，停止结果在 `evidence/shutdown.json`。需要浏览时可自行启用预览并用 SSH 端口转发。

```bash
cd /opt/ui-skill-lab-20261020/round-0002-reading
/opt/social-auto-upload/.venv/bin/python tests/acceptance.py
```

测试要求预览已运行，使用独立的测试 profile。测试脚本会在每个运行开始清理测试浏览器中的本项目收藏状态。

## 已验证

最后一轮记录 56 条断言通过：三篇完整正文逐字比对；目录选择与 active 状态；首尾禁用；前后篇、左右箭头、B、Space；收藏重载持久化；收藏过滤与空状态；列表重绘后的焦点；Tab、Shift+Tab、Enter、Escape；帮助面板及手机目录焦点循环、返回位置；浏览器历史返回；换篇后焦点与页首；390 与 320 宽度无横向溢出；本地中文字体加载；无页面报错、console error 或 4xx/5xx 资源失败。首次与第二次失败记录保留，没有把失败作为通过。

原脚本 390×844 下正文可能全在首屏，`scrollTo(0,300)` 前没有断言实际产生正滚动；该条只证明换篇后 `scrollY=0`。父代理另在 390×600 从实际 `scrollY=195` 复测到 0，其独立复测不并入本案例的 56 条结果。

桌面、手机、目录和窄屏截图均实际查看。与参考相比保留纸色、文字阅读区、左侧目录及底部分篇导航。初版文字行长偏长，已增大桌面正文；品牌比参考缩小。没有宣称像素级还原或自行打分。

## 未验证与边界

测试基于腾讯云 Linux Chrome 的无头浏览器与手机视口/触控模拟，没有在实体手机、iOS Safari、Firefox 或读屏软件验收。没有验证浏览器禁用 localStorage 的错误分支、跨设备同步、长篇内容或大量文章。示例仅含指定三篇随笔；没有外部发布、登录或后端服务。

## 命令记录

`COMMANDS.md` 记录关键命令与结果；安装、构建、浏览器、停止记录在 `evidence/`。没有修改技能仓库、推送 GitHub 或触及已有业务。
