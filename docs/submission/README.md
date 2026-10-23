# 参赛介绍材料审阅稿

2026-10-23已重新生成[介绍PDF审阅稿](../../output/pdf/LeaseRadar_Competition_Intro_Draft.pdf)，修正视频状态并加入[最新合成演示与材料复核](DEMO_MATERIALS_20261023.md)。历史工程证据仍标2026-10-21/ccd5a1c，不把本轮彩排混入历史测试数。[静态分镜视频草稿](../../output/video/LeaseRadar_Storyboard_Review.mp4)非连续录屏或最终提交版，构建与边界见[视频验收](VIDEO_DRAFT.md)。

2026-10-23材料更新。成品：output/pdf/LeaseRadar_Competition_Intro_Draft.pdf，6页A4；实现证据基于0.1.16/ccd5a1c，本轮演示证据另记，来源证据清单RELEASE_EVIDENCE.json。该实现提交的GitHub CI已核对成功；不是报名/正式提交证明。文件名保留Draft供已有链接兼容，内容为本版审阅稿。

## 内容与数据边界

场景/流程、合成界面、实现结构、真实有限验证及缺口、启动和倒排目标。25挂牌/41版本是本地有限存量，不代表当前可报名数量；材料引用ccd5a1c阶段的262项本机回归，不等于准确率；本轮另加打包版本拒绝用例后完整263项通过。第二来源现时完整字段、真实PDF/OCR、生产并发及试用尚未验收。页面截图仅合成DEMO，无真实公告全文、联系人、私人笔记或密码；截图源文件assets/synthetic-comparison.png随源码保留。

内容依据：PROJECT_CONTEXT.md、SOURCE_AUDIT.md、DOCUMENT_DOWNLOADS_VERIFICATION.md、WZPT_ADAPTER_VERIFICATION.md、DEMO_ROUTE_VERIFICATION.md及COMPETITION_DEMO.md（均在仓库内，后五项在docs下）。字体使用本机授权Arial Unicode，仅在PDF嵌入使用的字形，不把系统字体文件拷入仓库。

## 重建

文档构建与QA使用独立可选环境，版本见requirements-pdf.lock；不会改应用backend/requirements.lock。

```sh
python -m pip install -r docs/submission/requirements-pdf.lock
python scripts/build_competition_intro.py --font /可嵌入且支持中文的TrueType字体路径.ttf
```

先更新RELEASE_EVIDENCE.json并核对来源验收，不从运行数据库自动生成业绩；PDF构建器读取版本/日期/测试数/依据提交。默认输出稳定路径output/pdf/LeaseRadar_Competition_Intro_Draft.pdf。本机已用Codex内置Python和ReportLab4.4.9/Pillow12.3.0/pypdf6.10.0验证；默认字体查找/Library/Fonts/Arial Unicode.ttf，其它环境传--font。Poppler用于渲染QA，未作为应用运行依赖。

## 已执行检查

- PDFInfo：6页A4，无表单、无JavaScript、无加密；约268KB。
- 全部页面渲染PNG逐页查看；本次更新截图，修正表格行首孤立标点及代码/英文附近换行；不拉伸截图。最终不变页面以PNG哈希对照已审查版本，变化页重新查看；页码/标题/表格/截图无重叠或缺字。
- pypdf提取文本：6页，262/0.1.16/ccd5a1c/合成/未知/未完成等关键边界存在；无本机绝对路径、密码或SMTP配置值。
- QA图片和中间版本在private/pdf-qa-20261021，不入Git；最终PDF、构建脚本和合成截图保留。

## 定稿前剩余

检查官方最新表单/页数等具体要求；根据最终实现刷新测试/验证记录；完成真实/合成分开的录制和视频导出；确认仓库评审访问/公开方式及数据许可；用户最终授权后再提交。本稿只用于内部审阅，材料还没有正式发布。

## 本地录制包

```sh
.venv/bin/python scripts/build_recording_bundle.py --output private/recording-new.zip
```

输出必须是新文件，拒绝覆盖。仅打包明确许可清单中的运行代码、锁依赖、合成fixture/截图、现有PDF初稿、[逐镜头操作与讲解稿](RECORDING_SCRIPT.md)及启动指南。不会打包private、.env、数据库、真实原公告、密码或用户笔记；代码/必需文件含符号链接则拒绝，材料缺失不生成残包。

解压后按START_HERE.md安装应用依赖并创建全新DEMO，数据和账号在接收者本机生成。MANIFEST.json记录打包时UTC时间、源码提交/工作树是否有改动，以及每个文件字节数/SHA256。它是完整性清单，不是签名，未把Git提交等同于所有打包字节。包的源码提交/全局工作树状态如实记录；本地无关文件可能使dirty为true，另核对包内每项字节与已提交源码一致；仍明确ready_to_submit=false及视频/终审/评审访问/提交缺口。生成包默认放private，不推送GitHub，仓库保留构建脚本和测试。

应用无需新增依赖或数据库迁移。包的离线初始化、登录、静态资源和四条筛选结果已用禁用网络的独立解压目录测试；依赖安装仍需要可用软件源，不宣称跨系统离线依赖包或已在Windows运行。PDF已更新至本版审阅稿并重新逐页渲染核验。材料元数据与应用版本不一致时打包失败；这不替代PDF内容和官方要求的人工审查。
