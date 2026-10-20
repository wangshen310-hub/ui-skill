# 青禾羽毛球馆 · 本地样例

原生微信小程序源码在 `source/`。日期、球场、整小时可用/已满时段、费用、核对、返回改选和本地完成已实现。没有预约后端、支付、登录或外部请求；确认不会锁场或扣款。

## 产物

- `brief.md`：原始简短需求、边界、设计提取及交互约定。
- `evidence/reference.png`：内置 imagegen 生成并实际查看的主屏参考；提示词在 `evidence/imagegen-prompt.txt`。
- `source-initial/`：第一次可运行的原生源码快照，未用后续修正覆盖。
- `source/`：最终原生源码，可在微信开发者工具中导入；项目使用官方本地测试标识 `touristappid`，未使用用户 AppID。
- `evidence/initial/`：初版官方编译产物、模拟 DOM 截图和14项通过的行为记录；最早的宿主点击桥失败另见 `first-click-bridge-failure.*`。
- `evidence/attempt-02-old-host/`：修改文件传输尚未结束时误跑旧宿主的窄屏溢出失败记录。随后已使用传输完成后的宿主重新运行，未将其当作产品失败或通过。
- `evidence/attempt-03-narrow-overlap/`：16项流程检查通过但人工查看发现320px摘要被底栏遮挡的截图。此问题已在最终源码修正。
- `evidence/final/`：18项通过的行为结果、官方 WXML/WXSS 编译结果、390×844和320×720的模拟 DOM 截图。
- `evidence/source-*-sha256.txt`、`version-hashes.txt`、`archive-hashes.txt`：逐文件和归档哈希；源码归档为 `source-initial.tar.gz` 与 `source-final.tar.gz`。
- `evidence/cleanup.json`：独立浏览器 profile、端口18633和进程清理证据。

## 已验证的层次

全部依赖安装、编译、运行和截图在腾讯云 `tencent-opencloudos`、`/opt/ui-skill-lab-20261020/round-0003-miniprogram` 完成；控制端只编辑、传输和查看。运行版本：Node v20.20.2、miniprogram-simulate 1.6.2、miniprogram-compiler 0.2.3、jsdom 24.1.3。截图使用腾讯云已有 Chrome 和独立 profile。

官方 WXML 和 WXSS 编译均通过，编译产物已保存。`miniprogram-simulate` 加载真实组件源码；初次 Node+jsdom 运行得到7个日期、3个球场、4个小时行。随后用该工具官方 `build.js`、文件映射和官方编译 WXML 在 Chrome DOM 中运行同一组件。WXSS 的视觉宿主使用模拟工具自带 PostCSS 渲染，并将工具默认的1rpx=1px适配为视口宽度/750；官方 WXSS 编译另外单独验证。宿主只提供平台标签基本display/scroll和鼠标click转官方tap接口，不另写产品界面或产品样式。

这属于**官方编译 + 组件逻辑/模拟 DOM验证**。不是微信开发者工具、微信模拟器或微信真机验收。模拟器将平台组件映射为DOM，不能证明微信原生组件皮肤、双线程机制、页面栈、原生触控、系统安全区或真实设备行为。工程保留真实 `view/text/button/scroll-view` 等组件，并设置微信原生导航标题；截图未伪造微信导航/胶囊。

## 最终结果与视觉修正

最终18项检查通过：默认上下文和4个整小时行；未选不能继续；已满不能选；19:00–20:00、2号场费用¥80；核对页完整日期/场地/起止时间/费用；返回保留选择；切换日期清空旧时段和费用；切换球场刷新状态；其他上下文重新选择；本地确认披露非真实预约；全满提示；320px无横向页面溢出、主操作可见、日期/球场/确认控件至少44px、摘要不被底栏遮挡、滚动可到第七天；无浏览器脚本异常。具体断言见 `evidence/final/behavior.json`。

已实际查看生成参考、初版截图、最终390px选择/核对页和320px选择页。延续参考的深绿、白底、日期条、球场分段、小时行和固定费用栏。修正了初版未选按钮视觉、窄屏触控区和320px底栏遮挡摘要。界面保留“本地样例”和完整的重要日期、时间、球场、费用。未作审美总分或像素级一致声明。

## 复现

在腾讯云的 `harness/` 运行 `npm ci --no-audit --no-fund`，再运行 `node probe.cjs` 或 `node verify.cjs final`。运行器只监听 `127.0.0.1:18633`，独立启动 Chrome；`finally` 关闭服务器和浏览器。结束后运行 `python3 cleanup.py` 移除该案例的临时 profile。47MB隔离依赖保留以便复现。

最终源码清单SHA-256：`0c15b86f74f0a3a739fd1feff3aa2b448e8f08007cad944178d0de6b5c1cdc13`。

当前没有官方微信开发者工具，未进行开发工具/真机预览。下一层验收需要在官方工具导入 `source/` 并在微信设备上检查平台样式、真实触控与安全区。本地样例不需要真实预约或支付接入。

官方依据：[工具说明与运行环境](https://github.com/wechat-miniprogram/miniprogram-simulate)、[浏览器文件映射与使用指南](https://github.com/wechat-miniprogram/miniprogram-simulate/blob/master/docs/tutorial.md)、[官方编译器选项与事件接口](https://github.com/wechat-miniprogram/miniprogram-simulate/blob/master/docs/api.md)。
