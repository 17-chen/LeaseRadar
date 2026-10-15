"""Configuration inventory with no secret values or credential transmission."""
import os,shutil
from sqlalchemy import select
from .db import Source
from .email_delivery import settings


def inventory(db):
    try:email='configured' if settings() else 'not_configured'
    except (ValueError,TypeError):email='invalid_configuration'
    from .incident_email import configuration
    try:alerts='configured' if configuration(db) else 'disabled'
    except (ValueError,TypeError):alerts='invalid_configuration'
    from .source_documents import configuration as document_configuration
    try:documents='configured' if document_configuration(db) else 'disabled'
    except (ValueError,TypeError):documents='invalid_configuration'
    return {'email':email,'source_alert_email':alerts,'source_documents':documents,'cookie_secure':os.getenv('COOKIE_SECURE','false').lower()=='true',
        'runtime_config':'private/runtime.json (optional; environment variables override)',
        'sources':[{'id':s.id,'enabled':s.enabled,'status':s.status,'last_success_at':s.last_success_at} for s in db.scalars(select(Source))],
        'external_validation_required':['真实SMTP指定地址投递','常驻服务器/HTTPS','PostgreSQL恢复与多worker压力验证','真实标注及用户试用','完整第二来源关键字段验收'],
        'pending_implementation':['未缓存来源附件获取/复杂条款候选提取','PDF/OCR真实样本与隔离容器运行验收','比赛PDF与演示视频'],
        'message':'配置就绪不等于真实环境已验收；本检查不发送邮件、不启用来源。'}
