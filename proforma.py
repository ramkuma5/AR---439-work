"""Lab 09: ABG three-statement projection. Standard library only; USD millions.

Run: python3 proforma.py
Proof and financing tests: python3 proforma.py --self-test
Deliberate failure (nonzero exit): python3 proforma.py --break-2026-cash
Source: https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-05/lab-09-proforma-build.md
"""

import argparse
import math
from copy import deepcopy


OPENING = dict(revenue=17999.0, inventory=2135.8, ppe=3070.4,
               other_assets=6371.6, cash=40.4, floor_plan=2027.0,
               debt=3572.0, other_liabilities=2127.5, equity=3891.7,
               revolver=0.0)
ASSUMPTIONS = dict(growth=0.018, gross_margin=0.1705,
                   sga_ratios=(0.665, 0.655, 0.645, 0.645, 0.645),
                   depreciation_ratio=82.4 / 3070.4, impairment=120.0,
                   capex=250.0, tax_rate=0.255,
                   inventory_days=2135.8 / (17999.0 - 3071.7) * 365,
                   floor_plan_ratio=2027.0 / 2135.8, other_wc_ratio=0.008,
                   minimum_cash=25.0, revolver_limit=850.0,
                   revolver_rate=0.06, repayment=150.0, buyback=150.0,
                   floor_plan_rate=0.0467, debt_rate=0.0544,
                   cost_of_equity=0.10, terminal_growth=0.025,
                   shares=17.951349)


def cash_and_revolver(cash_before, opening_revolver, minimum, limit):
    """Apply the cash sweep, respecting revolver capacity."""
    if cash_before < minimum:
        movement = min(minimum - cash_before, max(0.0, limit - opening_revolver))
    else:
        movement = -min(cash_before - minimum, opening_revolver)
    return cash_before + movement, opening_revolver + movement, movement


def project(opening=OPENING, assumptions=ASSUMPTIONS):
    a = assumptions
    prior = dict(opening)
    result = []
    for i, year in enumerate(range(2026, 2031)):
        r = dict(year=year)
        r['revenue'] = prior['revenue'] * (1 + a['growth'])
        r['gross_profit'] = r['revenue'] * a['gross_margin']
        r['cogs'] = r['revenue'] - r['gross_profit']
        r['sga'] = r['gross_profit'] * a['sga_ratios'][i]
        r['depreciation'] = prior['ppe'] * a['depreciation_ratio']
        r['impairment'] = a['impairment']
        r['operating_income'] = (r['gross_profit'] - r['sga']
                                 - r['depreciation'] - r['impairment'])
        r['interest'] = (prior['floor_plan'] * a['floor_plan_rate']
                         + prior['debt'] * a['debt_rate']
                         + prior['revolver'] * a['revolver_rate'])
        r['pretax'] = r['operating_income'] - r['interest']
        r['tax'] = max(0.0, r['pretax']) * a['tax_rate']
        r['net_income'] = r['pretax'] - r['tax']
        r['inventory'] = r['cogs'] * a['inventory_days'] / 365
        r['floor_plan'] = r['inventory'] * a['floor_plan_ratio']
        r['capex'] = a['capex']
        r['ppe'] = prior['ppe'] + r['capex'] - r['depreciation']
        r['change_other_wc'] = a['other_wc_ratio'] * (r['revenue'] - prior['revenue'])
        r['other_assets'] = prior['other_assets'] + r['change_other_wc'] - r['impairment']
        r['repayment'] = a['repayment']
        if r['repayment'] > prior['debt']:
            raise ValueError(f'FY{year}E: scheduled repayment exceeds opening debt')
        r['debt'] = prior['debt'] - r['repayment']
        r['other_liabilities'] = prior['other_liabilities']
        r['buyback'] = a['buyback']
        r['equity'] = prior['equity'] + r['net_income'] - r['buyback']
        r['change_inventory'] = r['inventory'] - prior['inventory']
        r['change_floor_plan'] = r['floor_plan'] - prior['floor_plan']
        r['cfo'] = (r['net_income'] + r['depreciation'] + r['impairment']
                    - r['change_inventory'] - r['change_other_wc'] + r['change_floor_plan'])
        r['fcfe'] = r['cfo'] - r['capex'] - r['repayment']
        r['opening_cash'] = prior['cash']
        cash_before = prior['cash'] + r['fcfe'] - r['buyback']
        r['cash'], r['revolver'], r['change_revolver'] = cash_and_revolver(
            cash_before, prior['revolver'], a['minimum_cash'], a['revolver_limit'])
        r['cfi'] = -r['capex']
        r['cff'] = -r['repayment'] - r['buyback'] + r['change_revolver']
        r['change_cash'] = r['cfo'] + r['cfi'] + r['cff']
        result.append(r)
        prior = r
    return result


def totals(r):
    assets = sum(r[k] for k in ('cash', 'inventory', 'ppe', 'other_assets'))
    liabilities = sum(r[k] for k in ('floor_plan', 'debt', 'revolver', 'other_liabilities'))
    return assets, liabilities, assets - liabilities - r['equity']


def assert_balanced(rows, assumptions=ASSUMPTIONS, tolerance=1e-7):
    """Recompute checks from live balances so edited cash cannot evade checks."""
    for r in rows:
        year = f"FY{r['year']}E"
        if not all(math.isfinite(v) for v in r.values()):
            raise AssertionError(f'{year}: non-finite model value')
        gap = totals(r)[2]
        if abs(gap) > tolerance:
            raise AssertionError(f'{year}: assets - liabilities - equity gap {gap:.1f}')
        gap = r['cash'] - assumptions['minimum_cash']
        if gap < -tolerance:
            raise AssertionError(f'{year}: cash below minimum; gap {gap:.1f}')
        if not -tolerance <= r['revolver'] <= assumptions['revolver_limit'] + tolerance:
            raise AssertionError(f"{year}: revolver outside permitted range: {r['revolver']:.1f}")
        gap = r['cash'] - r['opening_cash'] - r['change_cash']
        if abs(gap) > tolerance:
            raise AssertionError(f'{year}: cash-flow reconciliation gap {gap:.1f}')


def value_equity(rows, assumptions=ASSUMPTIONS):
    assert_balanced(rows, assumptions)
    k, g = assumptions['cost_of_equity'], assumptions['terminal_growth']
    if not k > g:
        raise ValueError('Cost of equity must exceed terminal growth')
    pv_fcfe = sum(r['fcfe'] / (1 + k) ** t for t, r in enumerate(rows, 1))
    terminal_fcfe = (rows[-1]['fcfe'] + rows[-1]['repayment']) * (1 + g)
    terminal_value = terminal_fcfe / (k - g)
    pv_terminal = terminal_value / (1 + k) ** len(rows)
    equity_value = pv_fcfe + pv_terminal
    return dict(pv_fcfe=pv_fcfe, terminal_fcfe=terminal_fcfe,
                terminal_value=terminal_value, pv_terminal=pv_terminal,
                equity_value=equity_value, terminal_share=pv_terminal / equity_value,
                per_share=equity_value / assumptions['shares'])


def table(title, rows, lines):
    print('\n' + title + ' (USD millions)')
    print(f"{'':38}" + ''.join(f"{'FY' + str(r['year']) + 'E':>13}" for r in rows))
    for label, field in lines:
        vals = [field(r) if callable(field) else r[field] for r in rows]
        print(f'{label:38}' + ''.join(f'{0.0 if abs(v) < 1e-8 else v:13,.1f}' for v in vals))


def report(rows):
    table('INCOME STATEMENT', rows, [(k.replace('_', ' ').title(), k) for k in
          ('revenue', 'cogs', 'gross_profit', 'sga', 'depreciation', 'impairment',
           'operating_income', 'interest', 'pretax', 'tax', 'net_income')])
    table('BALANCE SHEET', rows, [
        ('Cash', 'cash'), ('Inventory', 'inventory'), ('PP&E', 'ppe'),
        ('Other assets', 'other_assets'), ('Total assets', lambda r: totals(r)[0]),
        ('Floor plan', 'floor_plan'), ('Term debt', 'debt'), ('Revolver', 'revolver'),
        ('Other liabilities', 'other_liabilities'), ('Total liabilities', lambda r: totals(r)[1]),
        ('Equity', 'equity'), ('Liabilities + equity', lambda r: totals(r)[1] + r['equity'])])
    table('CASH FLOW STATEMENT', rows, [
        ('Net income', 'net_income'), ('Add depreciation', 'depreciation'),
        ('Add impairment', 'impairment'), ('Inventory investment', lambda r: -r['change_inventory']),
        ('Other working capital investment', lambda r: -r['change_other_wc']),
        ('Floor plan financing (operating)', 'change_floor_plan'), ('Operating cash flow', 'cfo'),
        ('Investing cash flow / capex', 'cfi'), ('Term debt repayment', lambda r: -r['repayment']),
        ('FCFE before buyback / revolver', 'fcfe'), ('Buyback', lambda r: -r['buyback']),
        ('Revolver draw / (repayment)', 'change_revolver'), ('Financing cash flow', 'cff'),
        ('Change in cash', 'change_cash'), ('Opening cash', 'opening_cash'), ('Closing cash', 'cash')])
    table('CHECKS', rows, [('Assets - liabilities - equity', lambda r: totals(r)[2]),
          ('Cash above minimum (must be >= 0)', lambda r: r['cash'] - ASSUMPTIONS['minimum_cash']),
          ('Cash flow reconciliation', lambda r: r['cash'] - r['opening_cash'] - r['change_cash'])])
    assert_balanced(rows)
    print('\nAll annual checks: PASS')
    v = value_equity(rows)
    print(f"\nPV of 2026-2030 FCFE: ${v['pv_fcfe']:,.2f} million")
    print(f"PV of terminal value: ${v['pv_terminal']:,.2f} million")
    print(f"Equity value: ${v['equity_value']:,.2f} million")
    print(f"Share of value after 2030: {v['terminal_share']:.2%}")
    print(f"Value per share: ${v['per_share']:.2f}")


def self_test():
    rows = project()
    expected = {'revenue': (18323.0, 19678.3), 'operating_income': (844.2, 971.4),
                'net_income': (413.6, 527.5), 'fcfe': (211.4, 342.3), 'cash': (101.8, 719.8)}
    for key, values in expected.items():
        for r, expected_value in zip((rows[0], rows[-1]), values):
            assert f'{r[key]:.1f}' == f'{expected_value:.1f}', (r['year'], key, r[key])
    assert f"{value_equity(rows)['per_share']:.2f}" == '291.75'
    print('PASS: all published endpoint values and $291.75 per share')
    broken = deepcopy(rows)
    broken[0]['cash'] = OPENING['cash']
    try:
        value_equity(broken)
    except AssertionError as error:
        assert str(error) == 'FY2026E: assets - liabilities - equity gap -61.4'
        print(f'PASS: valuation refused broken model: {error}')
    else:
        raise AssertionError('Broken model was accepted')
    assert cash_and_revolver(10, 0, 25, 850) == (25, 15, 15)
    assert cash_and_revolver(100, 50, 25, 850) == (50, 0, -50)
    assert cash_and_revolver(40, 50, 25, 850) == (25, 35, -15)
    stressed = dict(ASSUMPTIONS, buyback=2000.0)
    try:
        value_equity(project(assumptions=stressed), stressed)
    except AssertionError as error:
        assert 'cash below minimum' in str(error)
        print(f'PASS: exhausted revolver capacity rejected: {error}')
    else:
        raise AssertionError('Cash shortfall was accepted')
    print('PASS: revolver draw, full repayment, partial repayment')
    assert_balanced(rows)
    print('PASS: original model remains balanced after deliberate failure test')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--break-2026-cash', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        projection = project()
        if args.break_2026_cash:
            projection[0]['cash'] = OPENING['cash']
        report(projection)
