# 实际执行记录

1. 读取固定快照 SKILL.md、art-direction.md、writing.md、verification.md，以及内置 imagegen 技能。只读相关快照，无其他案例读取。
2. 内置 `image_gen` 生成桌面参考；调用提示词保存在 `reference/prompt.txt`，可见结果实际查看后开始界面实现。
3. `ssh tencent-opencloudos`：确认 Node `v20.20.2`、npm `10.8.2`、Chrome `/usr/bin/google-chrome`，`ss -ltn "sport = :18865"` 初始无监听。
4. `scp -r source tencent-opencloudos:/opt/ui-skill-lab-20261020/round-0002-reading/`。
5. 远端 source 中 `npm install --registry=https://registry.npmjs.org`：仅安装 @fontsource/noto-serif-sc，审计输出 0 vulnerabilities，日志 `evidence/install.log`。
6. 远端 `npm run build`，以及 `node --check app.js`、`node --check server.mjs`、`node --check build.mjs`：退出 0。
7. 远端 tar 保存 `snapshots/initial-runnable-source.tar.gz`，再用 Python subprocess 启动本项目 `node server.mjs`，PID 写入 `evidence/preview.pid`，预览 loopback 18865。
8. 远端 `/opt/social-auto-upload/.venv/bin/python tests/acceptance.py`：首次失败为帮助面板单一按钮 Tab 焦点落到 BODY，原始结果保留于 `evidence/initial-acceptance*`。
9. 对实际焦点状态读取，修复帮助面板 Tab；第二次测试出现手机目录 visibility 过渡导致 focus 无效，结果保留于 `evidence/second-acceptance*`。
10. 实际查看初版桌面与手机截图；放大桌面正文为 26px，保留移动正文 18px；手机目录移除 visibility 过渡。构建并重跑浏览器，56 条断言通过。
11. 构建器只复制 400 / 600 CSS 实际引用的字体，dist 从 86M 降为 15M。远端再次 `npm run build` 和相同完整浏览器验收：56 条断言通过，日志 `evidence/final-build.log`、`evidence/acceptance.log`。
12. 保存最终源码和 dist 包，远端 `sha256sum` 写入 `evidence/artifact-sha256.txt`；最终桌面、手机和目录截图回传控制端实际查看。
13. 远端按自有 PID 和 /proc/PID/cwd 核对后停止预览，连接探测确认 18865 不再监听。结果 `evidence/shutdown.json`。

没有在控制端执行 npm 构建或浏览器；没有修改全局 npm 配置。所有预览、测试 profile、依赖与产物均位于约定远端任务目录。
