# Lab 09 — ABG pro-forma build

The completed model values the case equity at **$5,237.34 million**, or **$291.75 per share**. The discounted terminal value accounts for **79.76%** of equity value. All five annual balance sheets balance, and cash stays above the required minimum.

## Files and running the model

- [proforma.py](proforma.py): single-file Python model, standard library only.
- [proforma_results.txt](proforma_results.txt): complete statements and valuation output.
- [verification.txt](verification.txt): executed verification results.

From the folder containing the files, run:

```bash
python3 proforma.py
```

Use `python` instead of `python3` if that is your Python 3 command. To do the break test, uncomment `projection[0]['cash'] = 40.4` near the end of the file and run it. The program should stop with the error shown below before printing a valuation. Comment that line again to restore the correct model.

## Known-answer verification

All amounts below are USD millions except value per share. Calculations retain full precision; rounding is for presentation only.

| Metric | FY2026E | FY2030E |
|---|---:|---:|
| Revenue | 18,323.0 | 19,678.3 |
| Operating income | 844.2 | 971.4 |
| Net income | 413.6 | 527.5 |
| FCFE | 211.4 | 342.3 |
| Closing cash | 101.8 | 719.8 |
| Assets less liabilities and equity | 0.0 | 0.0 |

The model was checked against both endpoints and the expected per-share result. A separate verification run changed the first projected cash balance to 40.4. The program stopped before valuation with:

```text
FY2026E: assets - liabilities - equity gap -61.4
```

The simplified version was also compared with the original verified model for every year and under larger buyback assumptions that require borrowing. Its calculations and printed results are unchanged. The base case needs no revolver borrowing.

## Explanation and reflection

**What are the statements worth?** Discounting the five projected FCFE gives $1,059.87 million. Discounting the terminal value adds $4,177.46 million. Their unrounded sum is $5,237.34 million. The terminal calculation adds the final year's scheduled debt repayment back to FCFE before growing it, following the case's assumption that this repayment does not continue indefinitely. Buybacks reduce cash and book equity; they do not get subtracted a second time from FCFE in valuation. The case uses a fixed share count.

**Which three operating judgments drive the model?** Revenue growth determines the scale of sales and working-capital needs. Gross margin determines how much of those sales remains after vehicle costs. SG&A as a fraction of gross profit determines how much gross profit survives overhead. The supplied path assumes improving overhead efficiency initially and then a steady ratio. These inputs are scenario judgments supplied by the course, rather than independently verified forecasts. They would need support from company filings, operating trends, and management commentary for an original company valuation. The discount rate and terminal growth also matter greatly because nearly four-fifths of value comes after the explicit projection period.

**Why compute cash last?** Profit is not the same as cash generation. Depreciation and impairment reduce earnings without using current-period cash; inventory and other working capital absorb cash; capital spending, debt repayment, and buybacks use cash. Once these flows are known, opening cash plus the net cash movement determines ending cash. Revolver borrowing or repayment then applies the liquidity rule. Computing cash this way permits an independent balance-sheet test rather than forcing the balance sheet to balance with a plug.

**What does the negative 61.4 gap reveal?** Holding 2026 cash at its opening balance omits the year's 61.4 cash increase. Assets are therefore understated by exactly that amount, while liabilities and equity retain their correct values. The sign points to a missing asset increase (or an equivalent overstatement on the financing side), and its match to the cash movement directs attention to the cash roll-forward. The check alone identifies an inconsistency; matching the amount to the cash movement identifies the deliberate error here.

**What is floor-plan financing?** Dealers finance vehicle inventory through inventory-backed loans from lenders such as manufacturers' finance companies and banks. As inventory grows, the case's linked floor-plan balance grows too, providing cash to fund much of the inventory investment. The model charges interest on the opening loan balance and includes the change in floor-plan borrowing in operating cash flow and FCFE, as instructed for this case.

**Why does deleting floor-plan financing cause a cash problem?** Inventory still needs funding if its associated loan disappears. Removing an existing loan requires replacement funding or repayment; simply deleting the liability without its cash counterpart breaks the accounts. Omitting only future borrowing increases is a much smaller change: this model's five annual increases total approximately 189.5 million. The lab's reference to roughly negative $1.1 billion concerns the video's scenario; the page does not specify that scenario's timing and adjustments, so that exact figure is not claimed as a reproduced result here. The economic explanation is the loss of financing for a large vehicle inventory balance.

## Scope and remaining in-class work

This work implements the complete ABG engine and automated break test from the [Lab 09 instructions](https://github.com/CinderZhang/FIN43900-Fall2026/blob/main/lessons/week-05/lab-09-proforma-build.md). The source assumptions, including exact historical-ratio arithmetic, are in `ASSUMPTIONS`; the supplied starting balances are in `OPENING`. They are classroom inputs, not newly researched market data.

AI assisted with code, explanations, and execution checks. The automated break test is not a claim that a classmate ran the program. The student still needs to watch the assigned video if not already completed, explain the judgments and reflections to a partner, and perform the partner swap. The earlier Week 3 `dcf.py` and prior chat were not supplied, so their prerequisite rerun was not performed.
