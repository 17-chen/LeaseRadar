# 0.1.10 受控来源附件下载

2026-10-16（Asia/Shanghai）。本机Python3.13、CI Python3.12；Python锁依赖不变，迁移0011。

## 范围

未缓存附件以版本+URL唯一建持久任务，与采集事务提交；下载单独开关默认false，并要求SOURCE_DOCUMENTS_ENABLED和有效SOURCE_DOCUMENTS_USER_ID管理员。每观察最多5份，检查前20个附件，每管理员最多20份待下载；每poll至多处理一份，待提取20份时延后下载。容量限制已在单worker合成场景验证，多worker并发容量上限尚未压力验收。

只接纳核准HTTPS白名单的明确.pdf/.docx链接，不猜测脚本下载地址。复用DNS核验/固定连接IP、原Host/SNI、证书验证、无跳转网络层。流式解码字节限制5MB，校验声明长度/签名，流式检查60秒总时限（单次read仍受25秒网络超时），下载不执行文档。

与HTML抓取共享Source租约，任务也有独立token/3分钟租约；旧任务或来源owner不能发布结果。过期GET可有限重新获取，累计最多3次；429等保留Retry-After，退避时延后同源网络访问。401/403保留blocked，同址后续版本不自动重试；其它解析/格式错误保留failed。旧版本/管理员变化取消，关闭开关暂停已有任务，不重定向私人审核归属。下载成功进入downloaded并引用DocumentReview，不等于提取成功或业务字段已确认。

页面“条款与附件”展示独立下载记录、错误、尝试次数和重试时间，分页与审核列表独立计数；API仅管理员本人可看，不返回租约token。提取继续使用原无网络隔离worker，不自动改挂牌或制造业务事件。

## 检查

- 213项本机完整回归通过（新增28项下载测试）。覆盖事务回滚、幂等、HTTP分支、大小/签名、三次停止、旧版本/归属取消、任务token/来源租约抢占、过期接管、背压与SSRF。测试仅合成传输；原本地SMTP测试不发真实外部消息。
- 对真实库已有公告的一份公开DOCX做单次受控GET成功：1,461,321字节，SHA256 3fbe6d346d19861eb7d83aed8873c787a24e6553d30cc7bb1762dd5b9acb1a93。文件与proof保存在private/download-check-20261016，不入Git。没有向真实审核库插入记录，没有运行真实OCR或把单份成功视为全来源覆盖。
- 原库0009先通过SQLite backup API复制到异目录升级0011：25挂牌/41版本/0审核/0下载，integrity ok，FK错误0；proof为private/downloads-restore-proof.json。
- 本地正式API/worker未运行，因此先备份private/backups/20261016T081410Z，再原库升级0011并启动API0.1.10与local_worker。25挂牌/41版本/0下载/0审核/0启用来源，integrity ok。OpenAPI已验证版本和下载历史路由。下载/附件入队/真实邮件开关均明确false。
- 隔离DEMO（private/downloads-demo-20261016）合成403记录页面已验证，提示受阻/未绕过、尝试次数和下载不等于字段核实；没有真实站点访问。截图private/screenshots/downloads-demo-20261016.png。验收后退出、关闭DEMO并停止其服务器。
- node语法、pip兼容、Compose配置与git diff检查通过。Docker实际运行、生产PostgreSQL与多worker压力尚未验收。

## 命令

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
# 常规升级：先停API/worker、备份，再migrate和重启
PYTHONPATH=backend .venv/bin/python -m app.cli backup
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

可选配置：SOURCE_DOCUMENTS_ENABLED=true、SOURCE_DOCUMENTS_USER_ID=有效管理员ID、SOURCE_DOCUMENT_DOWNLOADS_ENABLED=true。此次未启用。附件处理仍需原compose.extraction.yml隔离worker，缺工具保留待处理。

## 未验证与下一步

不支持无扩展名下载接口、跨域跳转、DOC/压缩包和历史全库补扫。没有扩大真实挂牌或第二来源关键字段覆盖。真实PDF/OCR效果、完整第二来源适配、复杂条款候选与生产/标注评测继续开发；外部凭据按既有约定最后统一补齐。
