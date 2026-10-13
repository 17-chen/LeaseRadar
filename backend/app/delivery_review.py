"""Evidence-based manual disposition, never a blind retry of ambiguous sends."""
from datetime import datetime,timezone
from sqlalchemy import update
from .db import EmailDelivery,IncidentEmail,Outbox,Subscription,AuditAction
from .domain import aware_time
from .email_delivery import settings,eligible


def review(db,model,identity,user_id,expected_state,action,reason,receipt,accepted_at=None):
    row=db.get(model,identity)
    if not row:raise LookupError('发送记录不存在')
    if row.state!=expected_state or row.state not in ('dead_letter','ambiguous'):raise ValueError('记录状态已变化或不可审核重试')
    if row.state=='ambiguous' and action=='retry':raise ValueError('结果不明不能直接重试；须先核验服务商未接受')
    if action in ('confirm_unsent','confirm_accepted') and (row.state!='ambiguous' or len(receipt.strip())<5):raise ValueError('确认结果须提供结果不明记录的服务商核验依据')
    at=datetime.now(timezone.utc)
    target='closed'
    if action in ('retry','confirm_unsent'):
        config=settings()
        if not config:raise ValueError('邮件通道未配置，不能重新入发送队列')
        if model is EmailDelivery:
            notice=db.get(Outbox,row.outbox_id);sub=db.get(Subscription,notice.subscription_id)
            valid=sub.user_id==config['user_id'] and row.recipient==config['recipient'] and (not row.sender_address or row.sender_address==config['sender']) and eligible(db,notice,at)
        else:
            from .incident_email import configuration,valid as incident_valid
            config=configuration(db)
            valid=config and incident_valid(db,row,config)
        if not valid:raise ValueError('原目标或通知已失效；不能换地址重放旧消息')
        target='queued'
    elif action=='confirm_accepted':
        when=aware_time(accepted_at)
        origin=aware_time(db.get(Outbox,row.outbox_id).created_at if model is EmailDelivery else row.created_at)
        if when is None or when>at or origin and when<origin:raise ValueError('服务商接受时间须带时区、不得早于通知创建或晚于当前时间')
        target='accepted'
    claimed=db.execute(update(model).where(model.id==identity,model.state==expected_state).values(state=target,manual_retry=target=='queued',token=None,lease_until=None,retry_at=None,error=None,accepted_at=when.isoformat() if action=='confirm_accepted' else row.accepted_at))
    if not claimed.rowcount:raise ValueError('另一审核已更新此记录，请刷新')
    db.add(AuditAction(user_id=user_id,kind=('email_' if model is EmailDelivery else 'incident_email_')+action,object_id=identity,
        reason=f'{expected_state} → {target}；{reason}；服务商核验：{receipt or "不适用"}'))
    # Historical attempt count is deliberately preserved. Manual retry grants one attempt.
    return target
