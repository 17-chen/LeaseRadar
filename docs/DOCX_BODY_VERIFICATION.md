# 0.1.8 DOCX正文与队列验收

日期：2026-10-14（Asia/Shanghai）。Python3.13本机、Python3.12 CI；现有requirements.lock不变，数据库仍0009，无迁移。

## 完成范围

- DOCX正文段落及表格按XML文档顺序提取，保留“正文段N／表N行N”；保留换行/制表符，排除删除与移出修订。不捏造页码。
- 纯正文附件可通过管理员上传→DB发布请求→文件worker→结果身份校验→review；不会自动创建挂牌版本、字段或通知。纯表格兼容旧docx_table结果。
- 5MB输入、ZIP条目/展开/压缩比、实体/宏/异常路径与100k字符上限保留；共用XML入口新增重复正文拒绝与UTF-16实体声明拒绝。
- 坏JSON、非对象、身份类型错误及过大请求均保留失败结果；原请求不删，下一文档仍能处理。数据库不接受身份不匹配的结果。

## 检查

170项本机pytest通过，含9项新增用例；既有备份恢复测试继续覆盖附件输入/结果与数据库。node语法、pip依赖兼容和git diff检查通过。首次完整回归为168通过2失败：旧备份合成DOCX缺w:body已修正；本地SMTP监听受沙箱限制，在授权本地监听后重跑。未删除失败用例或放宽断言。

端到端为合成文件的API与文件worker测试，无真实公告上传或真实外部消息。前端沿用现有附件审核组件，无布局变更。本阶段未重启本地常驻进程，重启后加载新版本。

## 运行与复核

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
# 正常应用启动（已有进程需先正常停止）
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

附件提取仍须使用compose.extraction.yml禁网络隔离容器；本地单轮worker仅用于可信合成fixture。本机没有Docker服务，本阶段不宣称实际容器运行。

## 真实范围与下一步

未抓取新来源；既有25挂牌/41版本的真实数据未改写，真实邮件保持关闭。页眉页脚、脚注、浮动布局、嵌套表格坐标与复杂条款自动识别不保证覆盖。真实DOCX/PDF/OCR准确率、自动来源附件队列、完整第二来源与生产验收仍待完成；外部账号/凭据按既有约定最后统一补齐。
