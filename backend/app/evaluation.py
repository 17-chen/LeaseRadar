"""Reproducible field evaluation from human-labelled JSONL, never invented results."""
from decimal import Decimal,InvalidOperation
from .domain import aware_time
FIELDS=('area_m2','raw_amount','price_kind','period_basis','operation','registration_deadline','status')
NUMERIC={'area_m2','raw_amount'}

def known(value):return value not in (None,'','unknown')
def equal(field,a,b):
    if not known(a) or not known(b):return not known(a) and not known(b)
    if field in NUMERIC:
        try:return Decimal(str(a)).is_finite() and Decimal(str(a))==Decimal(str(b))
        except InvalidOperation:return False
    if field.endswith('_deadline'):
        return aware_time(a) is not None and aware_time(a)==aware_time(b)
    return a==b

def evaluate(rows):
    ids=set();splits={};fields={k:{'labelled':0,'truth_known':0,'predicted_known':0,'correct_known':0,'false_known_on_unknown':0} for k in FIELDS}
    for row in rows:
        if not all(k in row for k in ('id','source','group','split','expected','predicted')):raise ValueError('Each row needs id/source/group/split/expected/predicted')
        identity=(row['source'],row['id'])
        if identity in ids:raise ValueError('Duplicate source record')
        ids.add(identity)
        # The same repost/project group may never cross development/holdout splits.
        group=row['group']
        if group in splits and splits[group]!=row['split']:raise ValueError('Project group leaks across splits')
        splits[group]=row['split']
        for key in FIELDS:
            if key not in row['expected']:continue # Unlabelled is not truth-unknown.
            counts=fields[key];counts['labelled']+=1
            truth,pred=row['expected'][key],row['predicted'].get(key)
            counts['truth_known']+=int(known(truth));counts['predicted_known']+=int(known(pred))
            counts['correct_known']+=int(known(pred) and known(truth) and equal(key,pred,truth))
            counts['false_known_on_unknown']+=int(known(pred) and not known(truth))
    for counts in fields.values():
        counts['precision']=counts['correct_known']/counts['predicted_known'] if counts['predicted_known'] else None
        counts['coverage']=counts['predicted_known']/counts['labelled'] if counts['labelled'] else None
        counts['known_truth_recall']=counts['correct_known']/counts['truth_known'] if counts['truth_known'] else None
    return {'n':len(ids),'groups':len(splits),'fields':fields,'limitations':'Label quality and split choice require human review. No all-web recall, user benefit or production performance inferred.'}
