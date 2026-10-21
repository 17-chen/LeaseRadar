# 0.1.16材料收敛验收

2026-10-21。已核对实现提交ccd5a1c的GitHub CI成功。本轮应用版本不变，没有依赖或迁移变更。

## 完成项

- 六页A4介绍审阅稿：0.1.16/2026-10-21/ccd5a1c，换当前合成比较画面，补个人视图/筛选导出及附件校验边界。仍明确视频未导出、容器/真实PDF-OCR/生产/试用未验收。
- RELEASE_EVIDENCE.json集中记录材料依据；PDF与口播引用ccd5a1c的262项实现回归，有对应证据。本轮另加一个打包版本拒绝测试后当前完整套件为263项，不把新检查倒填到旧提交。
- 打包器纳入证据清单；材料元数据版本与FastAPI应用版本不符时拒绝生成。ZIP仍为本地录制交接，ready_to_submit=false，不冒充最终提交。
- 旧文档由Git历史保留，现有Draft.pdf文件名不变以兼容既有链接。系统字体没有复制进Git，仅PDF嵌入使用字形。

## 检查命令与结果

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
git diff --check
# 独立文档环境：docs/submission/requirements-pdf.lock
python scripts/build_competition_intro.py
pdftoppm -scale-to 1100 -png output/pdf/LeaseRadar_Competition_Intro_Draft.pdf private/pdf-qa-20261021/page
.venv/bin/python scripts/build_recording_bundle.py --output private/recording-new.zip
```

完整263项通过，48.91秒，1条既有Starlette/AnyIO弃用警告。已包含实际源码打包/独立解压/禁网络初始化登录与筛选测试；新版本不匹配会拒绝且不生成残包。JS语法、依赖兼容和空白检查通过。以本机Codex内置Poppler PATH运行backend/integration/test_document_tools.py，1项通过，0.18秒；不是OCR或真实来源PDF评测。

文档用内置Python/ReportLab、系统可嵌入中文字体构建。6页全部渲染目视检查；几轮修复行首孤立标点及比较记录顺序措辞，重建后变化页重新看，不变页PNG哈希比对一致。最终图private/pdf-qa-20261021/final3-1.png至6.png；最终PDF6页，无表单/加密、未见缺字/重叠/裁切。pypdf核对0.1.16/262/ccd5a1c/视频尚未导出等边界，无旧237/9ce2f3d、账号密码或本机绝对路径。文本与proof.json留私有目录。

浏览器以全新隔离DEMO在127.0.0.1:8005登录并进入比较，A7500/B10000/未知口径待确认可见，截图存assets/synthetic-comparison.png。账号指南在private/demo-runs/8f3e57012f5f，未打包账号或私有运行目录。本轮没有修改业务数据、外部通道或真实源范围。

## 交付与边界

提交后生成独立本地录制ZIP并复算大小/哈希，与对应提交的包内每个源文件逐项字节核对；MANIFEST仍如实记录全局工作树dirty，因为未纳入包的既有教学视频/图片保留在工作区。未把无关文件隐藏或加入仓库。ZIP只含清单许可内容，不包含数据库、真实公告、private或.env；README提供安装依赖和生成新演示的步骤。

本轮完成介绍材料与交接包更新，不代表视频完成或已提交。待办：实际产品视频录制/导出及播放验收、官方最终规则/格式核对、仓库评审访问与发布方式确认、正式提交。真实来源仍农交云24条与高校1条链接型；完整第二来源、真实PDF/OCR、容器和生产运行仍未验收，不以合成材料替代。
