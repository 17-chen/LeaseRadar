# 附件结果校验与文字层提取

2026-10-21，应用0.1.16；依赖锁和数据库0011不变。

## 完成项与语义

PDF文字层只要求pdfinfo/pdftotext，不再因缺tesseract阻止可提取文字的页面。遇无文字页才检查pdftoppm/tesseract；缺工具明确指出对应页，OCR返回空白则提取失败。保持20页、5MB、每页20000字符、工具资源与总时限边界。当前采用整份附件成功或失败，不把前几页成功冒充完整提取；不承诺混合扫描页识别完整性。

数据库只接收正文非空且结构一致的review结果：PDF页码必须从1连续排列、方法只能pdf_text/ocr_review；DOCX为一个正文/表格定位结果、无虚构页码，方法不能混用。无效顶层JSON、正文为空/超限和格式方法冲突转failed；失败结果页清空并保留错误及磁盘原样结果，接口继续返回可审阅状态。已有非queued历史记录不自动重写；没有重新跑模型、生成市场变化或改业务字段。

## 本机检查

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

262项完整本机回归通过，37.27秒，1条既有Starlette/AnyIO弃用警告；JavaScript语法、依赖和空白检查通过。新增10项回归，包含文字PDF缺OCR仍可提取、无文字页缺工具、空白OCR拒绝、空review/空白正文/跨格式方法拒绝、非对象结果接口不崩溃、PDF零/乱序/布尔/缺失页码拒绝，保留失败文件且Version数不增。

本机用Codex内置Poppler的真实pdfinfo/pdftotext运行已有合成字节fixture集成：

```sh
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
```

1项通过，1.01秒；环境没有tesseract，不依赖假工具响应。它验证合成PDF的文字层路径、页码与正文，不是来源真实PDF、OCR准确率或系统全局工具配置。工具仅通过本命令PATH使用，未改变用户系统安装或生产服务。

## 真实样本检查与阻塞

只读复核10月16日实际下载的1份公开DOCX，文件SHA256仍为3fbe6d346d19861eb7d83aed8873c787a24e6553d30cc7bb1762dd5b9acb1a93，1461321字节。使用app.attachments.docx_review_text的既有压缩/XML/正文限制，在CPU限时且禁止socket外联的新Python进程中解析，未运行文档代码或打开外链。

提取16087字符，包含233个正文段和16个表行定位，发现首年租金字段标签；未把该标签推断为每个标的价格周期，也未衡量金额/内容准确率。全文和哈希证明留private/docx-review-check-20261021/extracted.txt及proof.json，未入Git、真实库或通知队列。这是只读解析复核，没有运行不可信文档的生产提取worker。

docker info只读检查失败：本机Docker socket不存在，服务不可用。没有绕过隔离要求在宿主机外部工具中处理真实PDF；真实隔离worker、中文扫描/OCR样本与准确率仍未验收。已有真实数据仍为农交云24条、高校1条链接型，未扩大第二来源或开启来源/邮件/下载。

## 下一步

让隔离容器在具备Docker的环境运行真实PDF/OCR标注样本；在此之前保持未验收。演示主链路、实际视频导出和介绍PDF定稿按10月31日提交计划继续，本阶段没有视频导出或重建介绍PDF。
