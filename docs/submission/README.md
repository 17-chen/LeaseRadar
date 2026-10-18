# 参赛介绍材料初稿

2026-10-18。成品：output/pdf/LeaseRadar_Competition_Intro_Draft.pdf，6页A4；内容基于实现0.1.13与已通过CI的9ce2f3d。不是报名/正式提交证明。

## 内容与数据边界

场景/流程、合成界面、实现结构、真实有限验证及缺口、启动和倒排目标。25挂牌/41版本是本地有限存量，不代表当前可报名数量；237项回归不等于准确率。第二来源现时完整字段、真实PDF/OCR、生产并发及试用尚未验收。页面截图仅合成DEMO，无真实公告全文、联系人、私人笔记或密码；截图源文件assets/synthetic-comparison.png随源码保留。

内容依据：PROJECT_CONTEXT.md、SOURCE_AUDIT.md、DOCUMENT_DOWNLOADS_VERIFICATION.md、WZPT_ADAPTER_VERIFICATION.md、DEMO_ROUTE_VERIFICATION.md及COMPETITION_DEMO.md（均在仓库内，后五项在docs下）。字体使用本机授权Arial Unicode，仅在PDF嵌入使用的字形，不把系统字体文件拷入仓库。

## 重建

文档构建与QA使用独立可选环境，版本见requirements-pdf.lock；不会改应用backend/requirements.lock。

```sh
python -m pip install -r docs/submission/requirements-pdf.lock
python scripts/build_competition_intro.py --font /可嵌入且支持中文的TrueType字体路径.ttf
```

默认输出稳定路径output/pdf/LeaseRadar_Competition_Intro_Draft.pdf。本机已用Codex内置Python和ReportLab4.4.9/Pillow12.3.0/pypdf6.10.0验证；默认字体查找/Library/Fonts/Arial Unicode.ttf，其它环境传--font。Poppler用于渲染QA，未作为应用运行依赖。

## 已执行检查

- PDFInfo：6页A4，无表单、无JavaScript、无加密；约265KB。
- 全部页面渲染PNG逐页查看；修正英文长串导致的孤立标点及引用换行。最终不变页面以PNG哈希对照已审查版本，变化页重新查看；页码/标题/表格/截图无重叠或缺字。
- pypdf提取文本：6页，237/0.1.13/合成/未知/未完成等关键边界存在；无本机绝对路径、密码或SMTP配置值。
- QA图片和中间版本在private/pdf-qa，不入Git；最终PDF、构建脚本和合成截图保留。

## 定稿前剩余

检查官方最新表单/页数等具体要求；根据最终实现刷新测试/验证记录；完成真实/合成分开的录制和视频导出；确认仓库评审访问/公开方式及数据许可；用户最终授权后再提交。本稿只用于内部审阅，材料还没有正式发布。
