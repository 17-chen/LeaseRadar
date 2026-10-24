# 视频审阅草稿与重建

## 2026-10-24口播修订版

新草稿为[LeaseRadar_Storyboard_Review_20261024.mp4](../../output/video/LeaseRadar_Storyboard_Review_20261024.mp4)，207.5秒、1920×1080、10fps、H.264/AAC，16,211,580字节，SHA256 `01f296ea063f1178614fc712b03a62a3375b89237e6924979e426754c516ff54`。末镜头将旧版“当前本机完整回归二百六十三项”改为“视频所用界面对应的源码阶段，自动化回归和文字提取工具集成已验证”，避免把取样时的历史测试数说成当前结果；未改画面/场景标题/字幕及真实范围。`source_commit=f50223e`仍指截图取样阶段；新增`storyboard_sha256`绑定这次实际口播稿，完整包生成时会核对，不把新口播倒填成旧视频内容。

本机Tingting重新合成并导出，完整解码2075帧、574个音频缓冲，峰值0.776，10张场景预览；时间线和原图片哈希核对通过。首次在受限沙箱中AAC编码失败，失败现场留在`private/storyboard-u_j0zjee`；授权本机媒体编码后成功，成功现场与预览在`private/storyboard-0u3sgpd5`。这仍是静态分镜，不是连续录屏。**尚未人工逐字听审，也没有把自动解码当成听审。**旧版MP4和证明保持原状，以下为2026-10-22历史记录。

## 2026-10-22历史版本

2026-10-22。成品[LeaseRadar_Storyboard_Review.mp4](../../output/video/LeaseRadar_Storyboard_Review.mp4)，206.9秒（约3分27秒），1920×1080、10fps、H.264视频/AAC旁白、16107204字节。视频是**实际合成界面的静态截图分镜**，不是连续录屏。片中持续显示合成、分镜及非连续录屏标识；系统Tingting旁白不是用户录音，不含真实试用/投递业绩。

## 素材与范围

应用固定0.1.16，依据源码f50223e。10个场景覆盖开场、筛选、三条比较、已知/未知口径依据、站内收件箱、个人跟进、来源受阻、收藏入口和限制收尾；9张原始截图在video-assets。截图通过浏览器实际登录/点击七步路线取得，不是绘制的假界面。合成DEMO在127.0.0.1:8006，私有账号和数据没有进入素材或Git。

VIDEO_STORYBOARD.json记录讲解与图片，口播263项对应f50223e应用验收，不把本轮新增6项媒体输入检查倒填到旧提交；当前完整测试269项。影片不宣称完整第二来源、真实OCR或生产运行完成。介绍PDF保留10月21日快照；正式版本需统一收尾信息。

## 重建（仅macOS路径已验证）

需要本地macOS工具say/afconvert、Swift编译器与AVFoundation/AppKit，不新增应用依赖。实际环境macOS15.7.7、Apple Swift6.1.2；未在其他系统验证。系统框架及TTS是平台组件，不把它们宣称为本仓库开源代码，也不复制系统字体或语音包。

```sh
.venv/bin/python scripts/build_storyboard_video.py --output output/video/新视频.mp4
```

必须指定不存在的输出；素材只接受同目录PNG/JPEG及匹配签名，拒绝符号链接/越界路径/空白文字与不明确标记。临时语音、模块缓存、失败视频和日志在private/storyboard-*，不入Git。工具保留失败现场，只有完成导出和全片解码检查才生成proof.json。若编码服务在受限环境不可用，需要允许本地媒体服务；不是录屏/摄像头/麦克风或网络权限。

本轮发现首轮截图实际为JPEG但误命名PNG，校验拒绝，已改正确扩展名。沙箱内媒体编码器不可用；获得本地编码服务执行权限后生成视频，首次直接合成失败产物保留。后续改AAC旁白、直封装及保留视频源asset/使用源时长后，最终端到端重建成功，最终proof中mux_recovery_used=false；恢复路径仍留作故障保全。早期样本在private/video-qa-20261022，未删失败记录。

## 检查结果

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

完整269项通过，51.07秒，1条既有Starlette/AnyIO弃用警告；JS、依赖和差异检查通过。另1项真实Poppler/合成PDF集成通过，0.64秒。媒体输入6项检查包括明确标签、数量、路径/链接/签名、空白旁白和已有视频不覆盖。Swift源码本机实际编译通过，部分AVFoundation旧接口有弃用警告；Linux CI不执行macOS编码，也不能视为跨系统媒体验收。

verify_storyboard_video.swift完整解码2069帧、573个音频缓冲，音频峰值0.776（非静音），时长206.9秒，无视频帧时间倒序；导出10张分镜预览。目视检查标题/中文字幕、合成标识、比较金额以及跟进笔记；调整筛选/受阻/收藏画面后重建，关键字段可读。最终私有预览/解码证明在private/storyboard-pkma7_qx/qa。QuickTime打开超时，改本机浏览器http://127.0.0.1:8010预览，媒体readyState=4、无错误，播放到33.95秒后暂停；证明和截图在private/video-qa-final-20261022。没有逐字人工听审，不称声音内容已最终审稿。

输出旁的media.json是时间线，proof.json含来源图片哈希、文件哈希和解码结果；它们不是可信签名。MP4 SHA256：833ffa946aaa5c7b75fffbcfbf62dce25bb0f54fc7de6148ab8c15d36b9c5806。所有帧为合成，真实库、来源开关、下载/SMTP和真实服务进程未操作。

## 预览与剩余

```sh
.venv/bin/python -m http.server 8010 --bind 127.0.0.1 --directory output/video
```

浏览器打开http://127.0.0.1:8010，目录仅含合成视频/元数据/预览页，不提供private。静态预览服务器不替代产品API/worker。

官网索引补核在COMPETITION_REQUIREMENTS.md：赛道一/二要求视频展示功能与流程，3-5分钟明确属于赛道三，不能混用为本项目硬要求。直接官网读取未获得正文，个人报名主体资格未确认，未报名/发邮件。下一步为逐字听审、按正式指引确定连续操作最终版与必要的PDF信息更新、评审访问/视频托管和正式提交授权；当前ready_to_submit=false，没有公开视频或发布仓库。
