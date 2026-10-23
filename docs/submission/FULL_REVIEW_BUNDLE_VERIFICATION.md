# 本地完整审阅包验收 · 2026-10-23

## 交付物与边界

- 本机文件：`private/LeaseRadar_Review_20261023.zip`；16,890,919 字节；SHA256 `66e0e4a4dcbbf187e3f3d67b5bfa0dbff60171b6133d5021c4300a8d2ea62223`。保持在 private，不推送公开材料。
- 包的 `source_commit` 为 `d3062775f437b387848118d56dc9a8d15c0f4825`，`app_version` 为 0.1.16；80 个 payload 文件，包含可运行合成DEMO源码/锁依赖、6页PDF审阅稿、静态分镜MP4及校验元数据、场景素材和说明。`START_HERE.md` 为构建时生成，另外79个文件与该提交的Git对象逐字节一致。
- `working_tree_dirty=true` 如实反映未纳入包的既有未跟踪教学视频/图片；不意味着包内源码未提交。逐文件哈希与大小、ZIP CRC均通过；`MANIFEST.json`不是数字签名。
- `mode=synthetic_demo_review_bundle`、`video_capture_kind=static_ui_storyboard`、`ready_to_submit=false`。现有视频不是连续录屏，尚未逐字人工听审；PDF仍是审阅稿，比赛资格/规则、评审访问、视频托管和正式提交未完成。

## 构建与独立恢复

```sh
.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261023.zip
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_recording_bundle.py
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
```

构建器在读取全部明确许可文件后核对应用/材料版本、PDF签名、MP4签名、视频字节数与SHA256、静态合成标记、完整解码记录和时间线时长；输入不一致、缺失、含符号链接或输出已存在时拒绝生成。专项12项、完整280项本机回归通过；另1项Poppler集成通过。JS语法、依赖一致性、Python语法和Git空白检查通过。唯一上游Starlette/AnyIO弃用警告保留。

实际将ZIP解压至全新`private/review-restore-20261023`，逐项核对MANIFEST字节数/SHA256、79个仓库文件与`d306277`的Git blob、无`private/`/`.env`路径及ZIP CRC；随后仅用解压目录的源码创建全新合成DEMO。登录、演示场景API、首页/CSS/JS和面积≥30㎡、月租≤12000、仅可报名的4条筛选结果均通过；恢复检查将socket连接禁用，没有访问外部来源。首次恢复命令因含空格路径未加引号在shell层失败，修正引号后成功，未生成不完整数据。

验证使用本机Python3.13和现有锁依赖。包内说明从全新环境安装依赖需要联网；“演示运行不需外部网络”不等于跨系统离线安装或正式生产验收。没有访问真实来源、改真实库、发送邮件或向比赛方提交材料。
