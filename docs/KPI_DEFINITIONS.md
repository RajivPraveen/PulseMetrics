# KPI definitions and grain

All money is USD. Monthly recurring revenue is the active subscription run rate at **calendar month end**. A subscription period has an inclusive start and exclusive end. The demo sources are synthetic; revenue and spend are not financial forecasts.

| KPI | Definition | Grain / caveat |
| --- | --- | --- |
| MRR | Sum of end-of-month active period MRR | Month; excludes one-time charges and taxes |
| ARR | MRR × 12 | Run rate, not booked annual contracts |
| New MRR | MRR from customers with prior month MRR = 0 | Reactivation would count as new in this demo |
| Expansion MRR | Positive MRR change for continuously paying customers | Month |
| Contraction MRR | Negative MRR change for continuously paying customers | Month |
| Churned MRR | Prior MRR for customers with current MRR = 0 | Month |
| Logo churn | Churned customers ÷ previous month paid customers | Month |
| Gross revenue churn | Churned MRR ÷ starting MRR | Month; excludes contraction |
| NRR | (Starting MRR + expansion − contraction − churned MRR) ÷ starting MRR | Month |
| CAC | Marketing spend ÷ newly paid customers | Blended monthly; channel version attributes by acquisition channel |
| Estimated LTV | ARPA ÷ monthly logo churn | Simple steady-state estimate; null when churn is zero |
| Trial → paid | Signup cohort trials paying within 30 days ÷ trials | Cohort month; recent cohorts may be immature |
| Activation | Trial users with activation event within seven days ÷ trials | Cohort month; recent cohorts may be immature |
| DAU / WAU / MAU | Distinct session users in trailing 1 / 7 / 30 days | Calendar day, UTC |
| Stickiness | DAU ÷ MAU | Calendar day |
| Feature adoption | Distinct feature users ÷ monthly active session users | Feature, month |
| Cohort retention | Paid cohort members active at month end ÷ original paid cohort | First paid month and months since |
| ROAS | Same-month invoices from channel-attributed customers ÷ channel spend | Channel, month; includes returning customers |
| Funnel | Distinct visitors → signup → trial → activated in seven days → paid in 30 days | Monthly signup cohort; visitors are visit-month distinct |

The last two funnel steps use a fixed maturity window. For strict comparisons, exclude cohorts younger than 30 days. The dashboard keeps recent cohorts visible to show live progress and labels their measures accordingly.

## Experiment methodology

The onboarding experiment uses the first assignment on each account and a binary activation outcome within seven days of trial start. Accounts whose trial has not had seven days to mature are excluded. The primary analysis is a two-sided pooled two-proportion z-test at α = 0.05. The displayed 95% interval is Newcombe's score interval for treatment minus control conversion. Relative lift is (treatment − control) / control. Cohen's h is the standardized proportion effect. MDE is the smallest positive absolute difference detectable with 80% target power at the current sample sizes and baseline conversion. The displayed design power uses a preregistered 3 percentage point practical threshold. A ship recommendation requires the entire interval above zero and observed absolute lift at least that threshold. This is illustrative; no sequential-testing or multiple-testing correction is included.
