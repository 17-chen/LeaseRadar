# 0.1.7 告警与发送审核阶段

日期：2026-10-13。Python依赖锁保持原样。本阶段只本地/合成通道验证，没有真实外部消息。

## 完成

暂停监测也可能结束陈旧告警，因此已结束不等于源站恢复；邮件和页面明确标记“异常结束，现状须核验”，不伪造成功观测。

来源异常邮件独立于挂牌outbox：0009 incident_emails以异常编号/开始或恢复阶段唯一，恢复与开始分别保留回执；不造挂牌变更事件。SOURCE_ALERT_EMAIL_ENABLED默认false，依赖既有EMAIL_ENABLED和单用户SMTP配置，接收用户必须是admin，始终使用明确的原配置地址。启用前历史不补发，发送前旧开始告警若已恢复则取消。静默按管理员通知偏好延后；每轮最多20条，有限退避、死信和租约过期ambiguous，不自动重发结果不明。

管理员审核页面支持dead_letter修复后重试一次、ambiguous经服务商记录确认未接受后重试一次、回执确认已接受、关闭不再发送。须原因；确认ambiguous须服务商依据，接受时间须带时区、在通知创建之后且不晚于当前。服务器权限、状态条件UPDATE与审计同事务。累计次数不重置，人工重试仅允许一次；closed是独立终态，不作为普通cancelled自动恢复。accepted不能重发，不表示最终投递。

新发送记录在SMTP之前保存Message-ID及发件地址；跨重试保持同一Message-ID，目标或发件地址变化禁止重放旧记录。旧记录不伪造历史Message-ID/发件地址，显示未保存，需核验原日志。用户自己的邮件历史和管理员自己的告警邮件历史均分页；管理员服务端审核权限独立校验。

修复SQLite备份遗漏document_queue：现在连同原上传文件、请求和结果一起备份；原失败样本保留。备份须暂停API、业务worker及附件worker，运行配置/凭据另行保管。

## 验证

- 本机完整161项pytest通过，包含本地SMTP协议和13项新增告警/审核/附件备份用例；node语法、pip check、Compose配置、git diff检查通过。上游Starlette/AnyIO弃用提示保留。
- 增强旧库测试：0003历史outbox→0008已有SMTP接受记录→0009，原accepted/attempts保留，manual_retry=false，未杜撰历史Message-ID或发件地址。
- 实际库先备份private/backups/20261013T085254Z再升级0009；复制0008备份到独立目录升级0009，integrity=ok、FK错误0、41原文hash一致、25挂牌/41版本/0告警邮件；private/delivery-restore-proof.json。
- 独立合成库回归验证DOCX原文件/请求/结果一起备份，复制到不同DATA_DIR后文件hash和DB review状态保持。
- 浏览器隔离DEMO：来源页展示告警关闭和模拟ambiguous回执，审核表单提示服务商核验；选择关闭后页面显示管理员已关闭，累计次数仍1，记录保留。未发送任何真实消息。截图private/screenshots/delivery-review-dialog.png、delivery-review-closed.png。
- 远端完整CI及原有真实Poppler集成以对应GitHub提交结果为准，不将本机测试当远端通过。

## 配置与命令

private/runtime.json或环境变量中SOURCE_ALERT_EMAIL_ENABLED最后统一配置；默认false。与EMAIL_ENABLED、EMAIL_USER_ID、EMAIL_RECIPIENT、EMAIL_START_AT、SMTP_*配合，单用户必须是admin。Compose也提供相同开关。网页“来源健康→告警邮件与审核”，“提醒收件箱→邮件发送记录→审核发送结果”。旧开始告警不补历史，真实验证只针对用户明确授权地址。

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli backup
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
PYTHONPATH=backend .venv/bin/python -m app.cli readiness-check
```

## 未验证与下一步

真实SMTP/管理员地址、服务商回执核验流程、多worker生产压力和PostgreSQL恢复尚未验收。无全网/固定时效/外部绝对一次承诺。第二来源关键正文/附件、真实PDF/OCR样本、来源自动附件队列、复杂条款候选、大库性能、真实评测/试用及比赛材料继续推进。代码继续开发，外部配置最后统一补齐。
