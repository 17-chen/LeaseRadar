"""Evidence-backed arithmetic only; never forecasts or inferred contract terms."""
from decimal import Decimal, localcontext, ROUND_HALF_UP
from typing import Literal
from pydantic import BaseModel, Field, model_validator

Money = Decimal
class RentSegment(BaseModel):
    start_month: int = Field(ge=1,le=600)
    end_month: int = Field(ge=1,le=600)
    monthly: Money = Field(ge=0,le=1000000000000,allow_inf_nan=False)
    quote: str = Field(min_length=5,max_length=2000)
    @model_validator(mode='after')
    def valid(self):
        if self.end_month<self.start_month or len(self.quote.strip())<5:raise ValueError('租金段范围或依据无效')
        return self

class LeasePlan(BaseModel):
    basis: Literal['monthly','first_year','total_term','segments']
    amount: Money | None = Field(default=None,ge=0,le=1000000000000,allow_inf_nan=False)
    term_months: int = Field(ge=1,le=600)
    annual_escalation_percent: Decimal | None = Field(default=None,ge=0,le=100,allow_inf_nan=False)
    annual_compound: bool = False
    fixed_rent: bool = False
    amount_before_free: bool = False
    prorate_partial_year: bool = False
    free_months: list[int] = Field(default_factory=list,max_length=600)
    segments: list[RentSegment] = Field(default_factory=list,max_length=100)
    nonrefundable_fees: Money | None = Field(default=None,ge=0,le=1000000000000,allow_inf_nan=False)
    refundable_deposit: Money | None = Field(default=None,ge=0,le=1000000000000,allow_inf_nan=False)
    evidence: dict[str,str] = Field(default_factory=dict,max_length=10)
    @model_validator(mode='after')
    def valid(self):
        required={'basis','term_months'}
        if self.basis=='segments':
            if self.amount is not None or self.annual_escalation_percent is not None or self.free_months:raise ValueError('分段表直接填写实际应付月租，不叠加金额、递增或免租')
            segments=sorted(self.segments,key=lambda s:s.start_month)
            cursor=1
            for segment in segments:
                if segment.start_month!=cursor:raise ValueError('分段租金存在重叠或遗漏月份')
                cursor=segment.end_month+1
            if cursor!=self.term_months+1:raise ValueError('分段必须完整覆盖租期')
            self.segments=segments
        else:
            if self.amount is None or self.segments:raise ValueError('金额必填；分段表只用于分段口径')
            required.add('amount')
        if self.annual_escalation_percent is not None:
            if self.basis not in ('first_year','monthly') or not self.annual_compound:raise ValueError('递增只支持明确的每年复利；其他规则须填写分段')
            required.add('escalation')
        if self.fixed_rent:
            if self.annual_escalation_percent is not None:raise ValueError('固定租金与递增规则不能同时选择')
            required.add('fixed_rent')
        if self.free_months:
            if not self.amount_before_free:raise ValueError('免租扣减须明确基价尚未扣免租，防重复扣减')
            required.add('amount_before_free')
            if self.basis=='total_term':raise ValueError('租期总额已是总价，不能再次减免租月')
            if len(set(self.free_months))!=len(self.free_months) or any(isinstance(m,bool) or not 1<=m<=self.term_months for m in self.free_months):raise ValueError('免租月份须为租期内不重复月份')
            required.add('free_months')
        if self.prorate_partial_year:required.add('proration')
        if self.nonrefundable_fees is not None:required.add('fees')
        if self.refundable_deposit is not None:required.add('deposit')
        if any(len(self.evidence.get(k,'').strip())<5 for k in required):raise ValueError('每个计算条件均须提供明确依据：'+', '.join(sorted(required)))
        return self


def calculate(plan: LeasePlan):
    def money(value):return str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if value is not None else None
    result={'basis':plan.basis,'term_months':plan.term_months,'first_year_monthly':None,
            'average_monthly':None,'total_rent':None,'schedule':[], 'cost_complete':False,
            'nonrefundable_fees':money(plan.nonrefundable_fees),'refundable_deposit':money(plan.refundable_deposit),
            'evidence':plan.evidence,'warnings':['已知支出不是完整总成本；税费、维修、物业及其他合同条件须核验。保证金仅列现金占用。']}
    with localcontext() as ctx:
        ctx.prec=80
        if plan.basis=='total_term':
            result.update(total_rent=money(plan.amount),average_monthly=money(plan.amount/plan.term_months),formula=f'{plan.amount} ÷ {plan.term_months}个月')
            result['warnings'].append('租期平均月租不能当作首年月租；总额口径不推算逐月付款。')
            return result
        if plan.basis in ('monthly','first_year') and plan.term_months>12 and plan.annual_escalation_percent is None and not plan.fixed_rent:
            result['warnings'].append('后续租金是否固定/递增未核验，不能按首年金额外推全租期。')
            return result
        if plan.term_months%12 and plan.basis=='first_year' and not plan.prorate_partial_year:
            result['warnings'].append('非整年租期没有明确按月折算依据，保留未知；可填完整分段月租表。')
            return result
        monthly=[Decimal(0)]*plan.term_months
        if plan.basis=='segments':
            for segment in plan.segments:
                for i in range(segment.start_month-1,segment.end_month):monthly[i]=segment.monthly
        else:
            base=plan.amount/12 if plan.basis=='first_year' else plan.amount
            rate=(plan.annual_escalation_percent or Decimal(0))/100
            monthly=[base*(1+rate)**(i//12) for i in range(plan.term_months)]
            for month in plan.free_months:monthly[month-1]=Decimal(0)
        result['warnings'].append('月度明细按两位小数展示，合计按未舍入值计算；不是合同付款日期或分期计划。')
        total=sum(monthly)
        result.update(total_rent=money(total),average_monthly=money(total/plan.term_months),
            first_year_monthly=money(sum(monthly[:12])/12) if plan.term_months>=12 else None,
            schedule=[{'month':i+1,'rent':money(value)} for i,value in enumerate(monthly)],
            formula='按明确应付月租序列求和；平均月租=已知租金总额÷明确租期月数')
        if plan.basis=='segments':result['segment_evidence']=[s.model_dump(mode='json') for s in plan.segments]
        return result
