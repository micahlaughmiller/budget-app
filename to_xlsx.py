"""
Turn a Better Budget backup into ONE workbook with a tab per sheet, so Google
Sheets takes it in a single upload instead of eight separate CSV imports.

    python to_xlsx.py better-budget-backup-2026-10-09.json

Then in Drive: New -> File upload, pick the .xlsx, and open it with Google
Sheets. Every tab arrives at once, numbers stay numbers, dates stay dates.

Reuses to_sheets.py for the table building, so the two can never disagree about
what the data is.
"""
import io, json, os, sys

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    print("This needs openpyxl:  pip install openpyxl")
    sys.exit(1)

import to_sheets as T


HEAD_FILL = PatternFill("solid", fgColor="0F766E")
HEAD_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FONT = Font(bold=True)
MONEY = '#,##0.00;[Red]-#,##0.00'


def is_money_header(h):
    h = str(h).lower()
    if h in ("n", "due day", "priority", "yearly raise %", "apr %"):
        return False
    return (h in ("amount", "balance", "target", "min payment", "value", "edited amount")
            or h.startswith("20"))          # the budget's month columns


def add(wb, title, header, rows, money_all=False):
    ws = wb.create_sheet(title[:31])
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))

    for c in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    money_cols = [i + 1 for i, h in enumerate(header) if money_all or is_money_header(h)]
    for col in money_cols:
        for row in range(2, ws.max_row + 1):
            ws.cell(row=row, column=col).number_format = MONEY

    # a TOTAL row, if the table carries one, reads as a total
    if ws.max_row > 1:
        last = [ws.cell(row=ws.max_row, column=c).value for c in range(1, len(header) + 1)]
        if "TOTAL" in [str(v) for v in last]:
            for c in range(1, len(header) + 1):
                ws.cell(row=ws.max_row, column=c).font = TOTAL_FONT

    for i, h in enumerate(header, start=1):
        widest = len(str(h))
        for r in rows:
            if i - 1 < len(r):
                widest = max(widest, len(str(r[i - 1])))
        ws.column_dimensions[get_column_letter(i)].width = min(42, max(10, widest + 2))

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    print("  %-22s %4d rows" % (title, len(rows)))
    return ws


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    if not os.path.exists(src):
        print("No such file: " + src)
        return 1
    p = json.load(io.open(src, encoding="utf-8"))
    if p.get("app") != "better-budget":
        print("That is not a Better Budget backup (missing the app marker).")
        return 1

    d = T.dollars
    acct = {a.get("id"): a.get("name", "") for a in p.get("accounts", [])}
    cat = {c.get("id"): c.get("name", "") for c in p.get("categories", [])}

    wb = Workbook()
    wb.remove(wb.active)
    print("reading  " + src + "\n")

    add(wb, "Accounts",
        ["Name", "Kind", "Balance", "APR %", "Min payment", "Due day",
         "Buffer lives here", "Leftover cash here", "In budget"],
        [[a.get("name", ""), a.get("kind", ""), d(a.get("openingBalance_c")),
          round((a.get("apr_bps") or 0) / 100.0, 2), d(a.get("minPayment_c")),
          a.get("dueDay") or "", "yes" if a.get("isBuffer") else "",
          "yes" if a.get("isSweep") else "", "yes" if a.get("participatesInBudget") else ""]
         for a in p.get("accounts", [])])

    for kind, title in [("income", "Income"), ("expense", "Expenses")]:
        add(wb, title,
            ["Name", "Category", "Account", "Amount", "Frequency", "N", "Anchor date",
             "Ends", "Yearly raise %", "Weekends", "Month end", "Note"],
            [[r.get("name", ""), cat.get(r.get("categoryId"), ""),
              acct.get(r.get("accountId"), ""), d(r.get("amount_c")),
              r.get("frequency", ""), r.get("intervalN") or "", r.get("anchorDate", ""),
              r.get("endDate") or "", r.get("annualRaisePct") or "",
              r.get("businessDayPolicy", ""), r.get("monthEndPolicy", ""), r.get("note", "")]
             for r in p.get("recurrences", []) if r.get("kind") == kind])

    add(wb, "Goals", ["Goal", "Kind", "Target", "Linked account", "Priority", "Target date"],
        [[g.get("name", ""), g.get("kind", ""), d(g.get("targetAmount_c")),
          acct.get(g.get("linkedAccountId"), ""),
          g.get("priority") if g.get("priority") is not None else "",
          g.get("targetDate") or ""] for g in p.get("goals", [])])

    # ---- the budget: one row per category, one column per month ----
    months = sorted(p.get("budgetMonths", {}))
    if months:
        cats = [c for c in p.get("categories", [])]
        rows = []
        for c in cats:
            rows.append([c.get("group", ""), c.get("name", "")] +
                        [d((p["budgetMonths"][mk].get("budgeted") or {}).get(c.get("id"), 0))
                         for mk in months])
        known = {c.get("id") for c in cats}
        for cid in sorted({cid for mk in months
                           for cid in (p["budgetMonths"][mk].get("budgeted") or {})
                           if cid not in known}):
            rows.append(["(deleted category)", cid] +
                        [d((p["budgetMonths"][mk].get("budgeted") or {}).get(cid, 0))
                         for mk in months])
        rows.append(["", "TOTAL"] +
                    [d(sum((p["budgetMonths"][mk].get("budgeted") or {}).values()))
                     for mk in months])
        add(wb, "Budget by month", ["Group", "Category"] + months, rows)

        ov = []
        for mk in months:
            for k, v in (p["budgetMonths"][mk].get("incomeOverrides") or {}).items():
                rid, _, occ = k.partition("|")
                nm = next((r.get("name", "") for r in p.get("recurrences", [])
                           if r.get("id") == rid), rid)
                ov.append([mk, nm, occ, d(v)])
        if ov:
            add(wb, "Income overrides", ["Month", "Source", "Payday", "Edited amount"], ov)

    txrows = []
    for mk in sorted(p.get("transactions", {})):
        for t in p["transactions"][mk]:
            txrows.append([t.get("date", ""), t.get("payee", ""),
                           cat.get(t.get("categoryId"), ""), acct.get(t.get("accountId"), ""),
                           d(t.get("amount_c")), t.get("memo", "")])
    txrows.sort(key=lambda r: r[0])
    add(wb, "Transactions", ["Date", "Payee", "Category", "Account", "Amount", "Memo"], txrows)

    add(wb, "Categories", ["Group", "Category", "Rollover", "Sinking fund"],
        [[c.get("group", ""), c.get("name", ""), c.get("rollover", ""),
          "yes" if c.get("isEarmarked") else ""] for c in p.get("categories", [])])

    s = p.get("settings", {}) or {}
    add(wb, "Settings", ["Setting", "Value"],
        [["Balances as of", s.get("asOfDate", "")],
         ["Operating floor", d(s.get("operatingFloor_c"))],
         ["Buffer already saved", d(s.get("bufferHeld_c"))],
         ["Rollover policy", s.get("overspendPolicy", "")],
         ["Budget starts", s.get("budgetStartMonth") or ""],
         ["Months planned ahead", s.get("budgetLookaheadMonths", "")],
         ["Exported", str(p.get("exportedAt", ""))[:19].replace("T", " ")]])

    out = os.path.splitext(src)[0] + ".xlsx"
    wb.save(out)
    print("\nwrote " + out)
    print("upload that to Drive and open it with Google Sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
