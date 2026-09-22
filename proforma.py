# Lab 09: ABG pro-forma statements, 2026-2030
# Amounts are in millions of dollars, except value per share.

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


def project(opening=OPENING, assumptions=ASSUMPTIONS):
    a = assumptions
    prior = dict(opening)
    result = []
    for i, year in enumerate(range(2026, 2031)):
        r = dict(year=year)

        # Income statement: interest uses opening loan balances.
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

        # Balance sheet, leaving cash until the cash flows are calculated.
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

        # Cash flow: add back non-cash expenses and account for investment.
        r['change_inventory'] = r['inventory'] - prior['inventory']
        r['change_floor_plan'] = r['floor_plan'] - prior['floor_plan']
        r['cfo'] = (r['net_income'] + r['depreciation'] + r['impairment']
                    - r['change_inventory'] - r['change_other_wc'] + r['change_floor_plan'])
        r['fcfe'] = r['cfo'] - r['capex'] - r['repayment']
        r['opening_cash'] = prior['cash']
        cash_before = prior['cash'] + r['fcfe'] - r['buyback']
        # Borrow to reach minimum cash, or use extra cash to repay the revolver.
        if cash_before < a['minimum_cash']:
            available = a['revolver_limit'] - prior['revolver']
            change_revolver = min(a['minimum_cash'] - cash_before, available)
        else:
            change_revolver = -min(cash_before - a['minimum_cash'], prior['revolver'])
        r['cash'] = cash_before + change_revolver
        r['revolver'] = prior['revolver'] + change_revolver
        r['change_revolver'] = change_revolver
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
    # Recalculate the gap here so a changed cash balance is caught.
    for r in rows:
        year = f"FY{r['year']}E"
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
    print(f"{'':38}", end='')
    for r in rows:
        print(f"{'FY' + str(r['year']) + 'E':>13}", end='')
    print()
    for label, field in lines:
        print(f'{label:38}', end='')
        for r in rows:
            number = r[field]
            if abs(number) < 0.00000001:
                number = 0.0
            print(f'{number:13,.1f}', end='')
        print()


def report(rows):
    for r in rows:
        r['assets'], r['liabilities'], r['balance_gap'] = totals(r)
        r['liabilities_equity'] = r['liabilities'] + r['equity']
        r['inventory_cash_flow'] = -r['change_inventory']
        r['other_wc_cash_flow'] = -r['change_other_wc']
        r['debt_cash_flow'] = -r['repayment']
        r['buyback_cash_flow'] = -r['buyback']
        r['cash_cushion'] = r['cash'] - ASSUMPTIONS['minimum_cash']
        r['cash_gap'] = r['cash'] - r['opening_cash'] - r['change_cash']

    table('INCOME STATEMENT', rows, [(k.replace('_', ' ').title(), k) for k in
          ('revenue', 'cogs', 'gross_profit', 'sga', 'depreciation', 'impairment',
           'operating_income', 'interest', 'pretax', 'tax', 'net_income')])
    table('BALANCE SHEET', rows, [
        ('Cash', 'cash'), ('Inventory', 'inventory'), ('PP&E', 'ppe'),
        ('Other assets', 'other_assets'), ('Total assets', 'assets'),
        ('Floor plan', 'floor_plan'), ('Term debt', 'debt'), ('Revolver', 'revolver'),
        ('Other liabilities', 'other_liabilities'), ('Total liabilities', 'liabilities'),
        ('Equity', 'equity'), ('Liabilities + equity', 'liabilities_equity')])
    table('CASH FLOW STATEMENT', rows, [
        ('Net income', 'net_income'), ('Add depreciation', 'depreciation'),
        ('Add impairment', 'impairment'), ('Inventory investment', 'inventory_cash_flow'),
        ('Other working capital investment', 'other_wc_cash_flow'),
        ('Floor plan financing (operating)', 'change_floor_plan'), ('Operating cash flow', 'cfo'),
        ('Investing cash flow / capex', 'cfi'), ('Term debt repayment', 'debt_cash_flow'),
        ('FCFE before buyback / revolver', 'fcfe'), ('Buyback', 'buyback_cash_flow'),
        ('Revolver draw / (repayment)', 'change_revolver'), ('Financing cash flow', 'cff'),
        ('Change in cash', 'change_cash'), ('Opening cash', 'opening_cash'), ('Closing cash', 'cash')])
    table('CHECKS', rows, [('Assets - liabilities - equity', 'balance_gap'),
          ('Cash above minimum (must be >= 0)', 'cash_cushion'),
          ('Cash flow reconciliation', 'cash_gap')])
    assert_balanced(rows)
    print('\nAll annual checks: PASS')
    v = value_equity(rows)
    print(f"\nPV of 2026-2030 FCFE: ${v['pv_fcfe']:,.2f} million")
    print(f"PV of terminal value: ${v['pv_terminal']:,.2f} million")
    print(f"Equity value: ${v['equity_value']:,.2f} million")
    print(f"Share of value after 2030: {v['terminal_share']:.2%}")
    print(f"Value per share: ${v['per_share']:.2f}")


if __name__ == '__main__':
    projection = project()
    # For the lab's break test, uncomment the next line, run, then comment it again.
    # projection[0]['cash'] = 40.4
    report(projection)
