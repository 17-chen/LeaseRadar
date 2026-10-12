# 0.1.6 条款与附件阶段

日期：2026-10-12，Python3.13本机、Python3.12 CI，Python依赖锁不变。当前实现并未完成全部来源/生产验收。

## 完成与边界

新增登录后的“条款与附件”页面和只读POST /api/v1/lease-calculations。金额全程Decimal；支持明确月租、首年价、全租期总价、每年复利递增、固定租金、明确免租月份及完整分段表。每项计算条件有依据；后续规则未知不外推，非整年首年口径无折算依据保留未知，免租须确认基价未扣减。总价只得到租期平均月租，不伪造首年/付款序列。不可退费用和可退保证金单列，未知不是0，cost_complete始终false。计算不会修改挂牌或产生通知。

独立附件上传/队列/审核：PDF/DOCX限5MB，上传20份待处理上限；0008 document_reviews为权威，只有提交成功的记录发布请求。worker只有输入/请求的只读文件卷与结果写卷，不带数据库、SMTP凭据；部署包禁网络、非root、只读根文件系统、512MB、单CPU、64进程、128MB临时区。结果必须匹配DB哈希/格式并通过大小/结构校验才能接纳。文档失败保留，重提不删除失败样本。

PDF文字按页定位；空文字页走有界渲染与OCR，PDF限20页、单页20k字符、每工具20秒/整文120秒；OCR明示待人工核验。DOCX目前提取安全表格文本和表/行位置，不声称正文全覆盖。加密PDF不处理，不读取外部资源，不自动把文字当业务字段。非标准复利、按三年递增、天级免租等可用完整分段月租或保留未知；自动复杂条款识别尚未完成。

## 已执行检查

- 148项完整本机pytest通过；新增20项条款/附件规则。之后“无DOCX表格不报成功”的更改由20项相关回归复核通过。既有认证、通知、迁移和恢复回归保留。
- node语法、pip check通过。隔离Compose首次因未给项目名失败，已补明确name，config校验通过；未隐藏失败或称实际Docker运行。
- 本机缺pdftotext/tesseract，不声称本机PDF/OCR真实通过；CI新增安装公开系统工具并执行独立真实Poppler文字提取测试，结果以GitHub对应提交为准。OCR分支本机用合成工具响应验证，真实扫描样本准确率未测。
- 浏览器真实本地页面只读合成算式：首年120000、36个月、每年复利5%，租金总额378300、首年平均月租10000、全租期平均10508.33，费用与保证金待确认。没有写入真实挂牌。
- 隔离DEMO（private/terms-demo-20261012）浏览器DOCX上传→DB queued→独立单轮worker→结果校验→页面review，并展示“表1 行1：合成条款”。不进入真实库。
- 升级前停止API/worker并备份private/backups/20261012T085651Z；真实库0008后25挂牌/41版本。复制0007备份到新临时目录升级0008：integrity ok、FK错误0、41原文hash一致、附件记录0，private/terms-restore-proof.json保留证据。

截图private/screenshots/terms-calculation-desktop.png与document-review-demo.png。原始公告、数据库和附件仍不入Git。

## 使用命令

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

条款计算直接网页使用。附件需单独提取worker；本机无Docker服务所以仍未启动生产提取容器：

```sh
mkdir -p private/document_queue/inputs private/document_queue/requests private/document_queue/results
EXTRACTION_UID=$(id -u) EXTRACTION_GID=$(id -g) docker compose -f compose.extraction.yml --profile extraction up --build -d
```

上述隔离包用于本机SQLite的DATA_DIR=private。生产Compose使用命名卷时须以同一队列目录挂入提取容器，保持输入/请求只读、结果可写；不要把DB或SMTP环境变量传给提取容器。本地单轮worker仅用于可信合成fixture验证，不能代替处理不可信文档的隔离部署。

## 未验证与下一步

真实PDF/OCR样本准确率、隔离容器实际运行/版本镜像固化与资源压力、生产卷集成、原公告自动附件采集到本队列、DOCX正文和复杂条款自动候选提取仍需补齐。没有扩大第二来源关键字段接通，没有开启长期采集或真实邮件；完整第二来源、告警外发/死信审核、生产和真实评测继续推进，外部配置最后统一补齐。
