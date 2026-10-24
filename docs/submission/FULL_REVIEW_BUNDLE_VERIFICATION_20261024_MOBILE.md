# 含移动端修复的本地审阅包 · 2026-10-24

## 交付物

- 最新本地包：`private/LeaseRadar_Review_20261024_Mobile.zip`，16,897,615字节，SHA256 `f0b86d94a96ac4d6fb65cc545d95d46b79bb91b24d26b9e4062e535b1349b557`。只在private，未推送GitHub。
- 包的`source_commit`为`234918cb5c4c4e0acdd4279c35c5363291d73818`，包含会话到期提示修复的前端、六页PDF和原静态分镜视频。80个payload文件中79个仓库文件与该提交Git对象逐字节相同，另一个`START_HERE.md`由构建器生成。
- PDF SHA256 `22c20ee8fe7ba0a9884c65973ae5296cca1fa5b0118a5ad8a297054bed3b1566`；视频SHA256仍为`833ffa946aaa5c7b75fffbcfbf62dce25bb0f54fc7de6148ab8c15d36b9c5806`。`working_tree_dirty=true`记录既有未跟踪文件，不表示包内文件有未提交修改。
- `mode=synthetic_demo_review_bundle`、`video_capture_kind=static_ui_storyboard`、`ready_to_submit=false`。这份包取代本地10月23日和10月24日早先审阅包用于当前审阅；旧包作为历史保留。

## 验证

```sh
.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261024_Mobile.zip
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

本机完整280项回归通过，1条Starlette/AnyIO弃用警告保留；Poppler集成1通过，JS语法、依赖一致性和Git空白检查通过。新PDF以110 DPI渲染6页；第5页更新390px核验范围并目视检查，其他5页PNG与前版逐字节一致；pypdf检查文字层和历史证据边界。浏览器390px详情/比较与服务端到期后明确重新登录提示见[MOBILE_SESSION_VERIFICATION_20261024.md](MOBILE_SESSION_VERIFICATION_20261024.md)。

ZIP CRC、每项大小/SHA256、安全路径及79项Git对象字节核对通过，包内PDF与工作树当前PDF字节相同。独立解压至`private/review-restore-20261024-mobile`，只使用解压源码执行`--prepare-only`，得到6条合成候选、7个版本、5条站内提醒和0次网络请求。HTTP登录/筛选链路在10月23日旧包独立恢复及10月24日新建DEMO浏览器中通过；本次没有再次从解压目录执行HTTP链路。全新环境安装锁依赖仍需软件源；未验收Windows或生产容器。

## 未完成

视频为约3分27秒的静态分镜与合成旁白，尚未逐字人工听审或确定最终形式；PDF仍为审阅稿。官网实时表单/主体资格、评审源码与视频访问、正式提交需进一步确认或用户授权。真实第二来源完整字段、PDF/OCR准确率、生产部署、真实外部邮件及用户试用均未验收；没有扩大真实接入范围。
