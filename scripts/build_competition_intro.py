#!/usr/bin/env python3
"""Build the evidence-based competition introduction draft. Requires reportlab."""
import argparse
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
INK=colors.HexColor('#203F34');MUTED=colors.HexColor('#64766C');CREAM=colors.HexColor('#F4F6EF');LINE=colors.HexColor('#D5DED3')


def build(output,font):
    pdfmetrics.registerFont(TTFont('CN',str(font)))
    pdfmetrics.registerFontFamily('CN',normal='CN',bold='CN',italic='CN',boldItalic='CN')
    styles={
        'title':ParagraphStyle('title',fontName='CN',fontSize=31,leading=43,textColor=INK,spaceAfter=18),
        'h1':ParagraphStyle('h1',fontName='CN',fontSize=23,leading=32,textColor=INK,spaceAfter=17),
        'h2':ParagraphStyle('h2',fontName='CN',fontSize=14,leading=21,textColor=INK,spaceBefore=12,spaceAfter=8),
        'body':ParagraphStyle('body',fontName='CN',fontSize=10.5,leading=18,textColor=INK,spaceAfter=10),
        'small':ParagraphStyle('small',fontName='CN',fontSize=8.5,leading=14,textColor=MUTED,spaceAfter=8),
        'label':ParagraphStyle('label',fontName='CN',fontSize=10,leading=16,textColor=MUTED,spaceAfter=12),
    }
    def p(text,kind='body'):return Paragraph(text,styles[kind])
    def block(title,text):return KeepTogether([p(title,'h2'),p(text)])
    def table(rows,widths=(112,379)):
        data=[[p(str(cell),'body') for cell in row] for row in rows]
        t=Table(data,colWidths=list(widths),hAlign='LEFT')
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),CREAM),('LINEBELOW',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        return t
    story=[]
    def heading(n,title):story.extend([p(f'LEASERADAR / {n:02d}','label'),p(title,'h1')])
    def end():story.append(PageBreak())
    story.extend([Spacer(1,42),p('LeaseRadar · 铺讯','title'),p('招租公告发现与<br/>证据核验工作空间','title'),p('参赛作品介绍初稿 | 2026-10-18 | 实现版本 0.1.13','label'),Spacer(1,22)])
    story.append(p('把分散的招租信息、价格口径与跟进记录放进同一条可核查流程。自由筛选条件，保留未知，展示依据。'))
    story.append(Spacer(1,22))
    story.append(table([('真实存量','25条挂牌、41个版本；农交云24条、高校链接型1条。有限覆盖，不等于当前可报名数量。'),('工程验证','237项本机回归通过；对应实现提交9ce2f3d的GitHub CI通过。测试数量不代表字段准确率。'),('可重复演示','独立合成DEMO：6条候选、7个版本、5条站内提醒；七步可点击路线，不访问外部源。')]))
    story.extend([Spacer(1,28),p('本稿定位','h2'),p('可演示实现与已验证边界说明。尚未满足完整生产验收，不包含真实试用、合作、收益或准确率业绩。','small')]);end()
    heading(2,'从公告到跟进，保留每个判断的依据')
    story.append(p('面向门店拓展的信息整理场景。公开公告分布在不同站点，金额可能缺少周期，报名时间与竞价时间也可能不同，关键条款往往藏在附件。系统帮助缩小待核验范围。'))
    story.append(table([('01 发现','来源列表、存量详情复查、原文快照与版本；失败/受阻保留，不把有限扫描称为全网覆盖。'),('02 筛选','面积、城市、价格、用途与状态由用户选择。明确满足、明确不满足、信息未知分开处理。'),('03 比较','2-5条候选并列，价格性质分组。已核实周期才生成月租基准，保证金与租金分开。'),('04 依据','字段引用原文；来源变化与提取更新分开。人工纠正及撤销保留历史，不覆盖原始观测。'),('05 跟进','站内收件箱、收藏与个人跟进笔记。外部邮件是否启用、服务商是否接受分别展示。')]))
    story.extend([Spacer(1,16),p('关键保护：未知不是0','h2'),p('标题“五年租赁权 + 120000元”不能推出120000元是五年总租金，更不能直接除以60。未说明经营许可，也不能推断允许经营咖啡。')]);end()
    heading(3,'核心界面与合成演示场景')
    story.append(p('以下截图全部为合成数据，用于展示规则和交互；不是实时采集、用户试用或外部通知投递证明。','small'))
    story.append(Image(str(ROOT/'docs/submission/assets/synthetic-comparison.png'),width=491,height=276))
    story.append(Spacer(1,12))
    story.append(table([('同口径比较','A年租90000元，月租基准7500元；B年租120000元，月租基准10000元。尚不能推出完整总成本。'),('未知口径','第三条记录的金额120000元周期不明；月租/单位面积月租保留待确认，不能参与最低成本结论。'),('完整演示路线','筛选、比较、金额依据、周期未知、提醒、跟进、来源受阻共七步。返回第一步只恢复查询与选择，不重建业务数据。')]))
    story.append(p('合成变化：A年租96000变为90000，使用真实业务版本/outbox逻辑形成站内变化提醒；不声称源站发生了这一变化。','small'));end()
    heading(4,'模块化实现与可审计的数据流')
    story.append(p('本机API：FastAPI、SQLAlchemy/Alembic、SQLite。<br/>前端：原生HTML/CSS/JavaScript。<br/>部署包：PostgreSQL、Redis、Celery与隔离提取容器；生产运行仍待验收。'))
    story.append(table([('采集边界','来源adapter、独立fixture；HTTPS白名单、DNS核验与固定连接IP、TLS校验、禁止自动跳转。'),('数据权威','资产/挂牌/源记录分离，原文快照和不可变版本；金额Decimal，明确时刻带时区。'),('匹配与事件','三值匹配；业务事件/outbox同事务、唯一键幂等。报名提醒、商业变更及重新提取分别处理。'),('附件处理','PDF/DOCX受控下载限额、租约/退避/失败记录；独立无网络提取worker，结果验哈希后进入人工审核。'),('认证与隔离','登录会话、CSRF、服务端admin/member权限、个人订阅/笔记隔离。密钥和原始私有数据不入Git。')]))
    story.extend([Spacer(1,16),p('外部通知的实际语义','h2'),p('站内入箱与SMTP回执分别记录。发送结果不明需人工依据审核；服务商接受不等于最终投递，不能承诺外部绝对一次。当前真实邮件关闭。')]);end()
    heading(5,'验证证据与仍然存在的缺口')
    story.append(table([('本机与CI','237项完整本机回归通过；GitHub CI验证测试、迁移、JS语法及合成PDF文字工具集成。不是OCR准确率或生产负载测试。'),('真实来源','本地存量25条/41版本。高校链接型记录不算完整第二来源接通；产权首页可达不等于详情适配完成。'),('真实单样本','一份公开DOCX受控GET成功，约1.46MB；另一份高校历史HTML核对年租/面积/披露日期。不是多样样本准确率验收。'),('演示验收','浏览器走完七步并重演后，合成库保持6条/7版本/5提醒；没有新增或删除业务记录。'),('恢复与升级','SQLite备份、异目录恢复及0011升级检查通过。<br/>真实库保持25条/41版本，生产数据库与容器仍待验证。')]))
    story.extend([Spacer(1,12),p('未完成能力如实列出','h2'),p('完整第二来源现时字段覆盖、真实PDF/OCR效果、复杂条款自动候选、生产部署/并发压力、真实用户试用及其效果指标仍待验证。录屏、介绍PDF定稿和公开发布也需要最后审查。'),p('核验材料：<br/>docs/SOURCE_AUDIT.md<br/>docs/DOCUMENT_DOWNLOADS_VERIFICATION.md<br/>docs/WZPT_ADAPTER_VERIFICATION.md<br/>docs/DEMO_ROUTE_VERIFICATION.md','small')]);end()
    heading(6,'可复现启动与提交前计划')
    story.append(block('一键隔离演示','安装锁定依赖后执行：<br/><font size="11">.venv/bin/python scripts/demo.py</font><br/>每次新建私有目录，随机本地账号与步骤见DEMO_GUIDE.md；仅绑定127.0.0.1，关闭采集/邮件/自动下载，不覆盖已有数据库。'))
    story.append(block('源码与治理','代码仓库：https://github.com/17-chen/LeaseRadar<br/>当前私有，公开发布或评审访问方式待授权确认。提供MIT许可证、README、贡献/安全/数据政策与CI；真实公告和私人笔记不默认公开。'))
    story.append(table([('10月26日前','目标：冻结核心演示，完成一次可复现彩排。'),('10月27-29日','目标：录制、视频导出、介绍PDF定稿、链接与数据许可审查，修复影响展示的问题。'),('10月30日','目标：完成可提交包并核对内容与访问方式。'),('10月31日','按用户给定截止安排正式提交缓冲；报名、正式提交和发布需用户最终授权。')]))
    story.extend([Spacer(1,14),p('本稿尚非提交完成证明','h2'),p('当前材料是介绍初稿。尚未执行正式报名、视频发布、仓库公开或比赛提交；官方最新表单/规则仍需在提交前复核。所有排期为目标，不是已完成结果。','small')])
    def footer(c,doc):
        c.setStrokeColor(LINE);c.line(48,43,547,43);c.setFillColor(MUTED);c.setFont('CN',8)
        c.drawString(48,29,'LeaseRadar · 铺讯 | 参赛介绍初稿 | 2026-10-18')
        c.drawRightString(547,29,f'{doc.page} / 6')
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=(595.28,841.89),leftMargin=48,rightMargin=48,topMargin=44,bottomMargin=58,title='LeaseRadar 铺讯 - 参赛作品介绍初稿',author='LeaseRadar 项目')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'output/pdf/LeaseRadar_Competition_Intro_Draft.pdf');parser.add_argument('--font',type=Path)
    args=parser.parse_args();font=args.font or Path('/Library/Fonts/Arial Unicode.ttf')
    if not font.exists():parser.error('请用--font指定可嵌入、支持中文的TrueType字体')
    build(args.output,font);print(args.output)

if __name__=='__main__':main()
