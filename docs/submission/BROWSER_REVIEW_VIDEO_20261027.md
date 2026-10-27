# 10月27日有声浏览器演示审阅稿

素材是[10月26日七步连续浏览器录制](../../output/video/LeaseRadar_Browser_Walkthrough_20261026.webm)，只含本地新建合成DEMO。由录屏抽帧转为10fps H.264，在上沿加录制方式说明，再按[八段旁白稿](BROWSER_NARRATION_20261027.json)插入macOS Tingting系统合成语音。成品是[55.8秒MP4](../../output/video/LeaseRadar_Browser_Review_20261027.mp4)，属于**自动化浏览器操作的剪辑有声审阅稿**，不是人工实时操作、真实房源展示或正式投稿视频。此前207.5秒静态分镜和55.68秒无声原录屏均保留，不能混称同一素材。

原WebM SHA256：`4ac6ae3eeb088456cee084185d93cf35e88e7b6cf8be2121e4fd3c240d277fdd`；本MP4 SHA256：`55927041480aaa340bb6deab13fc0d05cb400402e5e2c6e5ed3cab9e6f106e6c`，6,383,704字节。原录屏的应用源码为`a9e6981`；本轮只新增媒体加工、校验及打包代码，未以新应用代码重录。演示来源/邮件/下载均关闭，没有真实外部请求或发信。页面上的价格、提醒、笔记均为合成示例。

构建命令：`python3 scripts/build_browser_review_video.py --output output/video/不存在的新文件.mp4`。从已保存原片重建需要Playwright附带的ffmpeg、macOS `say`/`afconvert`及Swift/AVFoundation；若重录原片还需本机Chrome。输出拒绝覆盖。受限沙箱第一次AAC编码报`fmt?`，失败现场保留在`private/browser-review-97f6hsv1`。授权本机媒体编码后成功；第一次成片末句旁白偏早，保留在`private/browser-review-fcc142xv/early-narration.mp4`，修改起始帧后重建。最终构建现场为`private/browser-review-hwqqd3ei`，均不入Git或审阅包。

自动核验：完整视频558帧、1280×840、10fps、55.8秒；音轨145个解码缓冲、非静音峰值0.723；8个阶段抽帧可生成，筛选、三项比较、金额依据、周期未知、站内提醒、跟进和最后来源页已目视检查。末段在48.5秒开始、关键帧49.5秒为来源健康页；媒体[proof](../../output/video/LeaseRadar_Browser_Review_20261027.proof.json)及[时间线](../../output/video/LeaseRadar_Browser_Review_20261027.media.json)可复核。完整解码只能证明文件可读，**不能证明语音的发音、数字、停顿或全片听感正确**；本轮没有真人逐字听审，也未按最终投稿指引确定长短/形式。

工程检查：完整本机回归289项通过，1条Starlette/AnyIO弃用告警保留；其中审阅包/分镜专项27项通过。Poppler集成首次因未把宿主工具加入PATH失败，使用交接文档记录的固定Poppler路径重跑1项通过。前端与录制脚本`node --check`、`pip check`、`git diff --check`通过。macOS媒体编码和整片解码不在Linux CI中，CI须另核。

人工终审仍需从头到尾播放，按八段旁白逐字核对声音和对应画面，特别是“六条留四条”“周期未知”“没有真实邮件投递”“扫描失败”的否定词；记录问题时码并重建。还需核对正式赛道视频要求、PDF终稿、访问与提交授权。现标`ready_to_submit=false`。
