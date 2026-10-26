# 连续浏览器操作片段审阅 · 2026-10-26

补充素材：`output/video/LeaseRadar_Browser_Walkthrough_20261026.webm`，55.68秒、1280×800、25fps、WebM/VP8，无音轨，5,587,001字节，SHA256 `4ac6ae3eeb088456cee084185d93cf35e88e7b6cf8be2121e4fd3c240d277fdd`。它是Chrome中由Playwright自动点击的**连续浏览器页面录制**，不是人工实时操作或带讲解的最终投稿视频；合成DEMO标识全程可见。已有207.5秒静态分镜/合成旁白仍单独保留，不能混称两者同一录制方式。

基于`a9e6981`应用代码，以`private/demo-runs/0ed56115cb4d`新建隔离DEMO在127.0.0.1:8015录制。初始化返回6候选、7版本、5站内提醒、0来源网络请求。脚本先通过本地API登录，再创建被录制的页面；没有键入或录到密码。浏览器拦截非本地请求，来源、邮件和下载开关保持关闭。首轮原始捕获在`private/browser-video-20261026`，新通用脚本`node scripts/record_demo_browser.js`再次走完七步并生成带SHA256的私有proof，复现现场在`private/browser-video-20261026-repro`。这两个现场都不进入Git或审阅包。

录制顺序为自由筛选→三项比较→金额依据→周期未知→站内提醒→跟进笔记→来源受阻。首步DOM确认筛选4条；七个步骤的标题与进度均在真实页面核对，关键场景抽帧目视可读。原始56.48秒素材开头有浏览器初始化瞬间的空白登录表单，已从成品裁掉前0.8秒，原始文件保留。成品首帧为已登录合成候选页；抽查筛选、比较、金额依据、周期未知、提醒、跟进和末尾来源页。使用Playwright匹配的ffmpeg 7.0.1对成品完整解码再编码，退出码0；媒体探测显示单路VP8视频、无音轨。`output/video/LeaseRadar_Browser_Walkthrough_20261026.proof.json`保存文件哈希、格式、七步清单和边界。

脚本依赖独立于应用：本机Google Chrome及可选`playwright-core` **1.62.1**，Playwright对应`ffmpeg-1011`只用于录制。新环境可将固定版本安装到private目录，再将`PLAYWRIGHT_CORE_PATH`指向该目录的`playwright-core`；同时设置`CHROME_EXECUTABLE`为本机Chrome路径。命令须传`--url http://127.0.0.1:空闲端口/ --guide private/demo-runs/新目录/DEMO_GUIDE.md --output-dir private/不存在的新目录`。脚本只接受127.0.0.1和private中的合成指南，拒绝覆盖输出。录制需要新建DEMO及本机浏览器可运行；不会启用真实来源。

仍需人工审阅整片视觉节奏、说明方式及最终投稿格式；这段短片没有讲解，不满足独立的正式视频签收。现有静态分镜的逐字听审也仍待完成。正式视频托管、仓库评审访问、报名和投稿均未执行，包状态仍为`ready_to_submit=false`。

本轮检查：17项包专项、285项完整应用回归、1项Poppler合成PDF集成通过；录制脚本与前端JS语法、依赖一致性和差异检查通过。测试范围只覆盖本地合成运行与包规则；8015录制服务检查后已停止。
