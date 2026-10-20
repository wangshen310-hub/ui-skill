# 第3轮移动案例：独立评审问题修复

两项评审均已在修前真实 Flutter widget engine 复现，随后修复。所有 Flutter analyze、编译、运行、截图与打包均在腾讯云 `tencent-opencloudos:/opt/ui-skill-lab-20261020/round-0003-mobile` 进行；控制端只编辑、传输与看图。没有修改技能仓库、其他案例、原 `screenshots-final` 或旧日志，没有推送。

## 修前冻结与复现

`frozen-before/` 保留修前完整 `app/lib`、`app/test`，以及原最终截图、最终测试/分析日志、读点样例和清单。`frozen-before.sha256.json` 记录冻结哈希；`original-evidence-integrity.json` 重新对照旧目录，验证旧证据未改写。`reproduction-test-before.dart` 是实际用于修前复现的独立测试代码。首次测试出现测试API名称错误，仅为测试编译失败，记录在 `logs/reproduce-before-test-api-error.log`；改用 SDK 实际公开API后，产品未改动，复现通过，见 `logs/reproduce-before.log`。

1. 字号漂移：把第3段读到段落中间（19号、段内112.30逻辑像素），独立从 `RenderParagraph` 布局读取视窗顶行，起始字符49、文字“份？我说，先看看。”。改28号后，顶行变成字符22、“海报。老板把晚报分成两”，向前漂移27字符。不是只比较段落编号或存储字段。对应 `screenshots-before/01-*`、`02-*`。
2. 写入失败：在真实 JSON 原子临时文件路径 `failure.json.tmp` 创建目录，使操作系统返回 `EISDIR`；不是 mock。两次点击“书架”都停留阅读页，仅显示“阅读位置未保存，请重试”。磁盘 JSON 与错误前逐字相同。对应 `screenshots-before/03-*`。

## 实现变化

- `app/lib/main.dart` 捕获段落内真实字符位置和行内相对偏移，字号重排后恢复该字符所在行。字号面板打开时固定一个文本锚点，连续滑动经过多个字号不会反复改用上一轮换行的行首而累积漂移。
- `app/lib/storage.dart` 将字符锚点随读点写入版本2 JSON，同时保留旧像素字段，兼容缺少新字段的版本1记录。旧记录首次读取仍只能使用原来保存的精度，后续保存会补充文本锚点。
- 返回先尝试保存，无论结果都能回书架；失败时在书架明确显示“阅读位置未保存，已返回书架”。没有把失败当成持久化成功。当前进程仍可暂存读点，磁盘保留上一次成功记录。
- 重复失败的扩展检查暴露出串行队列保留拒绝 Future 的问题（失败日志完整保留在 `logs/test-system-back-queue-failed.log`）；队列尾现吸收前次拒绝，当前 `save()` 仍把真实失败返回给当前调用者，既保留串行顺序，也避免后续返回再次冒出旧异步异常。
- 新测试从独立布局位置读取可见文本，不调用产品私有捕获/恢复函数。原两组测试只改证据输出路径到本子目录，避免覆盖旧最终证据。

## 修后验收

`logs/analyze-final.log`：No issues found。`logs/test-final.log`：真实引擎全部4组通过，`--concurrency=1`、`nice -n 15`。

| 检查 | 实际结果 |
| --- | --- |
| 段中19→28号，连续滑动经过多个字号并重排 | 原字符49所在行距视窗顶部6.48逻辑像素；顶行字符44，差5字符来自新行宽，原读到的文字仍在顶行附近 |
| 新 Store、重建 Widget 树，从真实 JSON 重新读取 | 字号28；可见顶行仍为字符44；滚动像素差0.0。此项不是进程重启声明 |
| 真实临时文件路径目录冲突，点击返回 | 成功回书架，明确未保存，磁盘 JSON 未改 |
| 保持同一真实失败条件，再次打开并走 Flutter 系统返回路由 | 能回书架；没有未处理异常。不是 Android 真机返回键验收 |
| 原案例流程 | 三本书可打开，正常保存与重读恢复、字号面板通过 |
| 窄屏与系统字号模拟 | 320×640、2倍系统字体的书架、阅读及字号面板无引擎布局异常，主要操作可用 |

实际查看了修前保存失败、修后大字读点与失败返回截图，文字读点和提示与日志一致；新回归截图保存在 `screenshots-regression/`。完整图片参数见 `screenshot-manifest.json`。

## 图像和平台边界

截图均来自真实 `flutter_tester` 引擎 `RepaintBoundary`，不是 HTML、Android 模拟器或真机。普通视窗逻辑390×844、view DPR=1、2倍导出为780×1688；窄屏逻辑320×640、view DPR=1、2倍导出为640×1280。上下各24逻辑像素安全区是测试模拟，没有伪造设备状态栏。导出倍率不是设备DPR。

远端没有 Android SDK，未构建 APK。Android MethodChannel、系统文件权限、真实设备生命周期、硬件手势和无障碍朗读仍未经设备验证。本文只对列出的引擎和真实 Dart File 证据负责。没有重新调用 imagegen，沿用既有参考，本轮仅修案例功能。

## 复现修后检查

在腾讯云案例 `app` 目录执行：

```bash
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
export PUB_HOSTED_URL=https://pub.flutter-io.cn
export PUB_CACHE=/opt/ui-skill-lab-20261020/round-0003-mobile/sdk/pub-cache
export CI=true
nice -n 15 ../sdk/flutter/bin/flutter --no-version-check analyze --no-pub
nice -n 15 ../sdk/flutter/bin/flutter --no-version-check test --concurrency=1 --reporter=expanded
```

原 SDK/字体版本及来源继续以案例 `RUNNING.md`、`SOURCES.md` 为准。`source-repaired.tar.gz` 是此次实际验收源码及字体、Android宿主源文件，不含SDK/缓存/构建产物。`source-before-lib-test.tar.gz` 是修前 lib/test 冻结。`source.diff` 便于审阅。退出检查见 `logs/resources-and-cleanup-final.log`；本轮测试临时目录由 tearDownAll 删除，自有 Flutter 编译/引擎进程已退出。
