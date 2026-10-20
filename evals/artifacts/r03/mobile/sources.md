# 来源与版本

- 固定技能快照：`/tmp/ui-skill-lab-20261020/baselines/01b2ad2/ui-skill/SKILL.md`。本案例没有读取其他案例/评审/evals，也不改动技能仓库。
- Flutter 源码：[官方 3.35.5 tag 源码归档](https://codeload.github.com/flutter/flutter/tar.gz/refs/tags/3.35.5)，SHA256 `014aa880c36e41f56774d03d7851f11be1264b16b8950be33b41f29d12aec824`。固定测试版本，不宣称最新；本地初始化元数据不等于官方 commit 验证。
- 安装方案依据：[Flutter 官方手动安装](https://docs.flutter.dev/install/manual)、[Flutter 官方中国网络说明](https://docs.flutter.dev/community/china)。Google releases_linux.json 的既往404没有重试；本轮用源码归档和官方文档列出的 CFUG 镜像下载 Dart/引擎/pub 依赖。没有安装 Android SDK。
- 配套引擎修订来自归档：`d3d45dcf251823c1769909cd43698d126db38deb`；Dart 工具输出为3.9.2。
- Noto Serif CJK SC：[官方字体文件](https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Regular.otf)。Noto Sans CJK SC 从腾讯云已有 `/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf` 复制。授权文本 `app/assets/fonts/OFL.txt` 取自系统 Noto 字体包，字体文件哈希另见清单。
- 参考图：内置 imagegen 真实生成并实际查看，标识 `01a15b6b-6479-7b61-a104-0c6aca8a968d`。完整生成提示见 `reference/prompt.txt`；图只用于设计参考，没有用作点击界面。
- 示例短篇为本案例原创示例内容；没有引用真实作者/出版信息，也没有社交指标或营销数字。
