# 移动读书 App 实测记录

交付真实 Flutter/Dart 工程与 Android 宿主源码。书架有《小城来信》《山间手记》《日常观察》三本原创示例短篇；可以打开、继续阅读、调字号和返回，阅读锚点与字号保存到本机 JSON。没有书城、社区、社交数字或多余导航。

## 本轮证据

全部依赖安装、工具编译、静态检查、widget engine 测试与截图均在腾讯云 `tencent-opencloudos:/opt/ui-skill-lab-20261020/round-0003-mobile` 执行。控制端只编辑、传输、查看图片。本轮没有 Android SDK、模拟器、真机或 APK 构建；以下通过项均属于 Flutter widget engine，不能称为 Android 真机验收。

- `evidence/analyze-final.log`：`No issues found!`，11.8秒。
- `evidence/test-final.log`：2条测试通过，17秒；`--concurrency=1`、`nice -n 15`。
- 第一条测试实际执行三本书打开/返回、正文拖动、字号面板与调整；用腾讯云真实临时文件保存，销毁原 App/store 后新建对象读取，再次打开时滚动位置误差小于2逻辑像素；最终字号和三书状态再次从 JSON 读取。
- 第二条测试在320×640逻辑画布、系统字体2倍下打开三书、调整面板和返回；检查触控按钮高度≥48、无 Flutter 布局异常。点击/拖动为测试引擎合成输入，书架长列表通过 ensureVisible 定位后点击，没有宣称硬件触摸通过。
- `evidence/persisted-state-sample.json` 是测试实际写出的状态样本；`evidence/source-sha256.txt` 是44个源码/工程/字体文件哈希；`evidence/screenshot-manifest.json` 逐图记录实际 PNG 头尺寸与 SHA256。

## 截图与查看

`evidence/screenshots-final/` 是最终7张引擎截图。390×844逻辑画布的5张导出为780×1688；320×640、字体2倍的2张导出为640×1280。测试 view DPR=1，RepaintBoundary 导出倍率=2；顶部/底部24逻辑像素安全区是测试注入，不是设备测得。每图都有尺寸断言和实际逻辑画布日志。

已实际查看生成参考、默认书架/阅读页、字号面板与窄屏大字截图，按相同内容关系对照。保留暖纸白、三色竖封面、横排书目、细分隔和无卡片正文；生成图无来源的作者删除，封面纹理简化为真实 Flutter 色块/细线，阅读底部用实际段落数替换无依据进度。窄屏大字模式将装饰封面从92×132缩为64×92，间距从22缩为16，让正文标题获得宽度。

## 失败与修正保留

1. 官方源码归档没有 git 元数据，初次工具报 `fatal: Not a valid object name HEAD`；engine.version 被 ignore 后又报 `origin/master`。专用 SDK 内初始化本地快照提交、显式跟踪归档内 engine.version，工作树分支设 stable，禁用版本联网检查。master 下工具曾阻塞于 GitHub tags fetch，已停止本案例该进程。输出的 framework commit `6bc6e436eafec3511c41d03450abec28cf161bec` 是本地快照，不能当作官方 commit 验证；原始官方 tar 哈希另存。
2. 初次 analyze/test 的 Semantics const 编译错误保存在 `analyze-initial.log`、`test-initial.log`；已修正。
3. 自动 widget fake-async 与真实异步文件 I/O 混用导致首轮等待，停止后改 LiveTestWidgetsFlutterBinding；初始截图保存在 `screenshots-initial-engine/`，说明见 `test-binding-note.txt`。
4. LiveTest 首次流程虽通过，实际截图仍是默认800×600逻辑画布。查看后发现该问题，错误画幅7图与原始结果独立保存在 `attempt-before-surface-fix/`；增加 setSurfaceSize 与 PNG 尺寸断言后重新通过。该错误组不计为窄屏证据。
5. 正确画幅首组在200%字下书名出现3+1字换行，保存在 `attempt-before-large-type-fix/`；缩小装饰封面后重新 analyze/test 并重新截图。

`evidence/initial-source.tar.gz` 保留最初工程（含首次编译问题）；`evidence/initial-runnable-source.tar.gz` 保留可运行首版；最终源码另打包。不改动技能仓库，没有读取其他案例、评审或 evals。

## 运行限制与资源

已验证 Flutter framework/widget engine、真实 Dart File 持久化、同尺寸重建后的阅读恢复、模拟字体缩放和指定逻辑画布。未验证 Android MethodChannel 的设备执行、APK 构建、系统返回键、设备实际安全区、系统后台回收、TalkBack 或真机性能。工程的 Android `filesDir` 桥接代码已保留，未以源码检查冒充设备通过。

开始时腾讯云内存可用约1.59GiB、磁盘可用9.5GiB；测试单并发，未修改生产服务、全局配置或现有工具。收尾时案例目录占用1,175,410,900字节（约1.09GiB，打包前），低于3GB新增上限，内存可用约1.80GiB；已确认本案例无残留 Flutter/Dart/curl 运行进程，并清理已知被停止测试的临时编译目录。SDK隔离保留，未安装到系统 PATH。

参考与字体来源、官方归档 URL/哈希见 `SOURCES.md`；视觉规范与响应式调整见 `DESIGN.md`；运行命令与验收边界见 `RUNNING.md`。
