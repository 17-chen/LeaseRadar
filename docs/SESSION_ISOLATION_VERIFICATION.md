# 同主机演示会话隔离验收

日期：2026-10-22；兼容Python 3.12/3.13，当前本机Python 3.13。

## 问题与修改

浏览器Cookie按主机/路径保存，不区分端口。此前LIVE和每个DEMO都使用lease_session，后登录的环境会覆盖另一环境的Cookie；不同数据库拒绝陌生token，表现为另一页掉线，不能将其描述为已发现跨库数据泄露。

DEMO改用lease_demo_加数据库URL SHA256前24位；相同URL重启稳定，不将数据库URL原文放入Cookie名。读取、登录设置和退出删除共用配置。LIVE/replay保留lease_session；DEMO不读取或清除旧名。保持HttpOnly、SameSite=Lax、Path=/、12小时有效期及COOKIE_SECURE设置，服务端会话撤销、CSRF和数据库权限路径不变。

旧DEMO升级重启后重新登录一次；旧Cookie可等待自然过期，不需清空浏览器Cookie或修改真实数据库。正在运行的旧进程不会自动获得修复。本阶段未重启真实服务或既有演示进程。

## 检查命令与结果

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_session_cookies.py
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
git diff --check
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
```

- 新增6项测试；完整回归275项通过，41.39秒，1条既有Starlette/AnyIO弃用提示。
- 专项含LIVE/replay旧名兼容、DEMO稳定/不同数据库不同名、独立进程配置接线；共享浏览器Cookie jar、同主机不同端口、3个独立SQLite数据库的登录/退出检查，分别覆盖Secure开/关。
- 三环境同时登录后逐一核对身份；一个DEMO退出仅移除自身Cookie，另外两个保持登录；重放已退出token被拒绝，无CSRF/错用另一会话CSRF均403。故意向LIVE库传递只含旧名的jar时，DEMO命名空间拒绝回退认证。
- JavaScript语法、依赖一致性、差异空白检查通过；另1项真实Poppler工具/合成PDF集成通过，0.56秒。
- 完整回归也包含既有禁外网新建DEMO和独立解压录制包登录/筛选测试。未新增依赖或迁移，API版本保持0.1.16。

## 范围与限制

本阶段为TestClient内存HTTP请求及真实独立SQLite库/Cookie jar验证；没有另做原生浏览器多端口彩排或公网反向代理验收。不同数据库URL文本即不同名，不对同库URL别名做归一化；相同数据库故意共享身份。多套LIVE仍使用同名，应使用不同主机/域名；同主机恶意服务仍可访问同主机Cookie，此修复不是安全隔离边界。

真实来源仍为农交云24条与高校1条链接型，41版本；本次没有访问新来源、变更真实库或发送外部邮件。第二来源完整接通、生产容器和真实PDF/OCR指标仍未完成。

10月21日PDF与10月22日静态分镜视频保留各自提交/测试数快照，本次未重建或将它们重新标为当前全部证据。下一步继续提交材料终审、录制彩排与演示冻结；正式发布/提交未执行。
