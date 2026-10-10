from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

def decimal(value):
    if value is None or value == '':
        return None
    try:
        n = Decimal(str(value).replace(',', ''))
        return n if n.is_finite() else None
    except InvalidOperation:
        return None

def normalize_price(fields):
    amount, area = decimal(fields.get('raw_amount')), decimal(fields.get('area_m2'))
    result = {'first_year_monthly': None, 'unit_monthly': None, 'formula': None,
              'normalization_status': 'unknown', 'cost_complete': False}
    basis = fields.get('period_basis')
    if amount is None or amount < 0:
        return result
    if basis == 'first_year':
        monthly, formula = amount / 12, f'{amount} ÷ 12'
    elif basis == 'monthly':
        monthly, formula = amount, str(amount)
    else:
        return result
    result.update(first_year_monthly=str(monthly.quantize(Decimal('.01'))),
                  formula=formula, normalization_status='known')
    if area is not None and area > 0:
        result['unit_monthly'] = str((monthly / area).quantize(Decimal('.01')))
    return result

def match(fields, filters, at=None):
    checks = {}
    for field in ['city', 'district', 'property_type', 'environment', 'operation', 'status', 'price_kind']:
        wanted = filters.get(field)
        if wanted:
            actual = fields.get(field)
            checks[field] = 'unknown' if actual in (None, '', 'unknown') else ('pass' if actual == wanted else 'fail')
    for field in ['area_m2', 'first_year_monthly']:
        value = decimal(fields.get(field))
        for side in ['min', 'max']:
            limit = decimal(filters.get(f'{field}_{side}'))
            if limit is not None:
                checks[f'{field}_{side}'] = 'unknown' if value is None else ('pass' if (value >= limit if side == 'min' else value <= limit) else 'fail')
    keyword = filters.get('keyword')
    if keyword:
        checks['keyword'] = 'pass' if keyword in str(fields.get('title', '')) + str(fields.get('address', '')) else 'fail'
    if filters.get('registration_open'):
        deadline = fields.get('registration_deadline')
        disclosure = fields.get('disclosure_deadline')
        historical = disclosure and disclosure < (at or datetime.now(timezone.utc)).date().isoformat()
        if historical or fields.get('status') in ('closed', 'withdrawn', 'sold', 'failed'):
            checks['registration_open'] = 'fail'
        elif deadline:
            cutoff = datetime.fromisoformat(deadline)
            checks['registration_open'] = 'pass' if cutoff > (at or datetime.now(timezone.utc)) else 'fail'
        else:
            checks['registration_open'] = 'unknown'
    verdict = 'fail' if 'fail' in checks.values() else ('unknown' if 'unknown' in checks.values() else 'pass')
    return {'verdict': verdict, 'checks': checks}
