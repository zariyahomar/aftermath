# Payoff simulation rules used by AfterMath tools

These are deterministic calculator rules. The language model must call tools instead of doing the arithmetic itself.

stacking_risk(window_dues, available_cash):
- utilization = window_dues / available_cash when cash > 0, else 9.99
- low: utilization < 0.4
- medium: 0.4 to 0.8
- high: 0.8 to 1.0
- critical: utilization > 1.0 (the window costs more than stated cash)

compute_payoff(remaining_balance, installment, extra_per_period):
- If extra is 0, periods_left = ceil(remaining_balance / installment)
- If extra > 0, each period pays installment + extra until balance hits 0
- Never suggest borrowing to pay BNPL
- Never output a plan that schedules more total outflow in 7 days than available_cash unless the evaluator marks it infeasible and asks for a revised, smaller extra payment

Evaluator loop:
- Draft a plan from per-account analyses
- Score feasibility against 7-day and 30-day dues vs cash
- If infeasible, reduce extras and push non-urgent extras past the next payday
