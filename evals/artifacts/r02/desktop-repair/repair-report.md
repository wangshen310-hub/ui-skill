# 独立评审问题的复现与案例修复

这是桌面案例代码的修复，不能作为 ui-skill 已改进的证明。本轮没有修改技能仓库，没有重新生成图，没有重做布局，也没有推送 GitHub。原归档 `/opt/ui-skill-lab-20261020/evidence/r02-desktop` 未改动；本例旧 REPORT、旧截图、旧 JSON 和初始快照保留。

## 修前证据

改应用代码之前，将原源码保存在 `snapshots/pre-review-fix/src/`，启动脚本保存在 `snapshots/pre-review-fix/run.sh`。修前 `app.py` SHA256：`011df53cf0c2e778690b05826435b5d0229e1fabffc70aec641b18a4b8996287`。

腾讯云实际原生 xcb 窗口执行：4张有效图片全部导出到A，A有4个真实可重新解码的JPEG；切换到B，仅勾选1张并导出，B实际只有1个JPEG，但反馈仍是“已导出 4 张，文件已保存到输出目录。”。另外3个队列项目的 output 路径仍指向A，说明反馈误用了历史 done 行总数。

4张均勾选时，“移除”按钮只移除当前行，其他3行保留，源文件均保留。行为本身是行操作，标签没有说明该范围。

- 原始 JSON：`before-fix-results.json`。
- B误报截图：`before-fix-B-one-exported-miscount.png`。
- 操作范围截图：`before-fix-remove-label.png`、`before-fix-remove-one-row.png`。
- 实际输出：`reproduction-data/A/`（4张）、`reproduction-data/B/`（1张）。

复现结果先通过协作消息报告，再修改应用源码。

## 代码变更

`src/app.py` 增加当前任务的 `batch_results` 与固定的 `batch_directory`。每次开始导出或重试时清空当前任务结果，只统计该任务实际回调的成功和失败项目，反馈写明本次数量和实际目标目录。

未参与本次导出的行保留原来的成功/失败状态与输出路径。切换目录不会把整队列改成“已导出到新目录”，也不会把历史失败塞进另一任务的成功反馈。

按钮改为“移除此行”，仍只移除当前行；原文件不删除。补丁在 `app-review.patch`。

## 修后实测

`after-fix-results.json` 记录7组检查，均通过：

1. 整批A输出4张，提示“本次已导出 4 张。输出目录：…/A”。
2. B只选1张，B有1张，提示“本次已导出 1 张。输出目录：…/B”。A输出哈希不变，未参与行仍指向A。
3. 新增一个真实损坏JPEG并只导出它，C没有输出，反馈为本次0成功、1失败；历史4个 done 不计入。
4. 保留该历史失败，另选一个有效项目到B，提示本次1张成功，不把未参与的旧失败计入；队列仍保留失败项目供重试。
5. 修复损坏源文件，Ctrl+R仅重试该项，C新增1个可解码JPEG，提示本次1张到C；A、B已有输出哈希不变。
6. 5张均勾选时按钮显示“移除此行”，点击只移除当前行，全部原文件保留。
7. 680×500窗口下，新标签和带目录的反馈没有遮住主要控件，样例标识保留。

每个输出均用 Pillow 实际重新加载，验证为1600×1000 JPEG。修后真实文件保存在 `verification-data/A/`（4张）、`verification-data/B/`（2张）、`verification-data/C/`（1张）。没有计时器模拟完成。

截图：`after-fix-B-one-exported.png`、`after-fix-C-failed-one.png`、`after-fix-B-success-with-old-failure.png`、`after-fix-C-retry-success.png`、`after-fix-remove-label.png`、`after-fix-minimum-680x500.png`。下载后实际查看相关截图，沿用原参考构图，没有新增视觉方向。

## 环境、命令与范围

构建检查、运行和截图均通过 `tencent-opencloudos` 在 `/opt/ui-skill-lab-20261020/round-0002-desktop/` 完成。控制端只编辑源码、传输和查看截图。复用原隔离 venv：Python3.11.6、PySide6-Essentials6.12.0、Pillow13.0.0；真实 Qt Widgets/xcb。

为本轮新建 `src/run_review_x11.py`，使用私有1280×900×24 Xvfb，自动分配显示，日志只写入 `evidence/review-fix/`。一次只运行一个测试程序和一个图片导出线程；两轮Xvfb均在 finally 中停止并 wait，日志记录 returncode0，没有驻留GUI进程。

实际命令：

```sh
.venv/bin/python src/run_review_x11.py src/reproduce_review.py > evidence/review-fix/reproduction-run.log 2>&1
.venv/bin/python -m py_compile src/app.py src/verify_review_fix.py src/run_review_x11.py
.venv/bin/python src/run_review_x11.py src/verify_review_fix.py > evidence/review-fix/verification-run.log 2>&1
```

本轮只复测列出的回归路径和最小窗口，未重跑整个原平台矩阵。仍无窗口管理器；快捷键测试前显式设定X11焦点，未验证OS的模态焦点恢复。未验证Windows/macOS或Wayland。本轮源码ZIP只含代码、运行说明和依赖版本清单，不含venv、库文件、照片、截图或输出数据。
