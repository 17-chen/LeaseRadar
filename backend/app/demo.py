"""Synthetic competition storyline. Fresh SQLite only, no source/SMTP requests."""
import json
import os
import secrets
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from argon2 import PasswordHasher
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect,select,func
from .config import ROOT,DATA,DATABASE_URL,MODE
from .db import engine,Session,User,Subscription,Followup,Source,Listing,Version,Outbox,DocumentDownload,seed_sources
from .service import ingest,deliver_local


def prepare():
    expected='sqlite:///'+str(DATA/'demo.db')
    if MODE!='demo' or DATABASE_URL!=expected or inspect(engine).get_table_names():
        raise ValueError('演示仅允许demo模式、独立DATA_DIR/demo.db及全新空数据库；不覆盖任何已有库')
    for key in ('EMAIL_ENABLED','SOURCE_ALERT_EMAIL_ENABLED','SOURCE_DOCUMENTS_ENABLED','SOURCE_DOCUMENT_DOWNLOADS_ENABLED'):
        if os.getenv(key,'false').lower()=='true':raise ValueError('演示必须关闭全部外部通道与自动附件操作')
    command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
    password=secrets.token_urlsafe(18)
    at=datetime.now(timezone.utc);future=(at+timedelta(days=10)).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d 16:30')
    past=(at-timedelta(days=2)).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d 16:30')
    def university(title,amount,area,deadline=future,conflict=False):
        rows=[('挂牌价格',f'{amount} 元/年'),('出租面积',f'{area}平方米'),('出租标的地址','合成演示市演示区示范路'),('报名截止时间',deadline),('出租用途','经营条件需线下审批确认')]
        if conflict:rows.append(('租金挂牌价','180000 元/年'))
        return '<title>合成演示：'+title+'</title><div class="wp_articlecontent"><table>'+''.join('<tr><td>'+k+'</td><td>'+v+'</td></tr>' for k,v in rows)+'</table></div>'
    def url(i):return f'https://www.wzpt.edu.cn/2099/0101/c739771a{900000+i}/page.htm'
    with Session() as db:
        seed_sources(db)
        user=User(username='demo',role='admin',password_hash=PasswordHasher().hash(password));db.add(user);db.flush()
        db.add(Subscription(user_id=user.id,name='合成演示：30㎡以上、月租不超过12000',filters={'area_m2_min':'30','first_year_monthly_max':'12000'},unknown_policy='review_digest'));db.commit()
        identities=[]
        for i,title,amount,area,deadline,conflict in [
            (1,'可比年租A',96000,60,future,False),(2,'可比年租B',120000,80,future,False),
            (3,'超出预算',216000,120,future,False),(4,'已过报名期限',72000,50,past,False),
            (5,'价格冲突待确认',96000,65,future,True)]:
            identity,_=ingest(db,'wzpt',url(i),university(title,amount,area,deadline,conflict),observed_at=at.isoformat());identities.append(identity)
        html=(ROOT/'fixtures/replay/nongjy.html').read_text().replace('演示路11号商铺','周期未知的五年租赁权').replace('2099-10-16 16:00:00',future+':00')
        identity,_=ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/990001',html,observed_at=at.isoformat());identities.append(identity)
        # A second synthetic observation exercises the existing business-change path.
        ingest(db,'wzpt',url(1),university('可比年租A',90000,60),observed_at=at.isoformat())
        db.add(Followup(user_id=user.id,listing_id=identities[0],status='待联系',favorite=True,note='合成演示笔记：核验经营条件后再决定是否联系；没有真实联系或看铺。'))
        version=db.get(Listing,identities[0]).current_version_id
        db.add(DocumentDownload(user_id=user.id,version_id=version,source_id='wzpt',url='https://www.wzpt.edu.cn/synthetic-demo.docx',format='docx',state='blocked',attempts=1,error='合成回放HTTP403；没有执行网络请求'))
        source=db.get(Source,'nongjy');source.status='blocked';source.error='合成回放访问受阻，无真实请求；旧记录仍可核验'
        for source in db.scalars(select(Source)):source.enabled=False
        db.commit()
    deliver_local()
    with Session() as db:
        summary={'mode':'demo','synthetic':True,'network_requests':0,'listings':db.scalar(select(func.count()).select_from(Listing)),
                 'versions':db.scalar(select(func.count()).select_from(Version)),'inbox':db.scalar(select(func.count()).select_from(Outbox).where(Outbox.state=='accepted'))}
    summary.update(schema=1,owner_user_id=user.id,comparison_ids=[identities[0],identities[1],identities[-1]],detail_id=identities[0],unknown_id=identities[-1])
    guide=DATA/'DEMO_GUIDE.md'
    guide.write_text(f'''# LeaseRadar 合成演示（非真实试用）

账号：demo
密码：{password}

访问：http://127.0.0.1:{os.getenv('DEMO_PORT','8001')}

1. 确认顶部DEMO标识；默认全部关闭网络采集/邮件/自动下载，不启动后台worker。
   可使用页面“演示路线”依次打开筛选、比较、依据、提醒、跟进和来源；弹窗关闭后继续下一步。
2. 候选页有6条合成记录；选择30㎡以上、月租上限12000，含待确认，展示明确匹配/未知/超预算/已截止差别。
3. 比较“可比年租A/B”与“周期未知”记录，解释周期未知不能按标题五年除60个月。
4. 查看详情字段依据、租金公式及保存的原文；原公告URL是格式测试地址，不要访问或当真实接通证据。
5. 提醒收件箱查看合成年租变动（96000→90000）与待确认提醒，强调站内入箱不等于外部邮件投递。
6. 收藏和跟进页面已存合成笔记，可演示修改；来源健康/条款与附件展示合成受阻仍保留历史。

所有记录、变动及受阻均为合成场景；没有真实联系、收益、试用、投递或跑分。
重复演示请重新运行scripts/demo.py创建新目录；不删除或重置已有演示。
''')
    guide.chmod(0o600)
    (DATA/'demo-proof.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':print(json.dumps(prepare(),ensure_ascii=False))
