"""
Turn a Better Budget backup into CSV files you can import into Google Sheets.

    python to_sheets.py my-budget-backup.json

Writes a folder of CSVs — one per tab. In Sheets: File -> Import -> Upload, and
choose "Insert new sheet" so each one lands on its own tab.

Amounts are written as plain decimal numbers, not cents and not text, so Sheets
treats them as numbers the moment they land.
"""
import csv, io, json, os, sys


def dollars(cents):
    """Cents -> a decimal Sheets will read as a number. Never a string."""
    if cents is None:
        return ""
    return round(int(cents) / 100.0, 2)


def write(path, header, rows):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print("  %-26s %4d rows" % (os.path.basename(path), len(rows)))


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

    out = os.path.splitext(src)[0] + "-sheets"
    if not os.path.isdir(out):
        os.makedirs(out)
    print("reading  " + src)
    print("writing  " + out + "\n")

    acct_name = {a.get("id"): a.get("name", "") for a in p.get("accounts", [])}
    cat_name = {c.get("id"): c.get("name", "") for c in p.get("categories", [])}
    cat_group = {c.get("id"): c.get("group", "") for c in p.get("categories", [])}

    # ---------------------------------------------------------------- accounts
    write(os.path.join(out, "accounts.csv"),
          ["Name", "Kind", "Balance", "APR %", "Min payment", "Due day",
           "Buffer lives here", "Leftover cash here", "In budget"],
          [[a.get("name", ""), a.get("kind", ""), dollars(a.get("openingBalance_c")),
            round((a.get("apr_bps") or 0) / 100.0, 2), dollars(a.get("minPayment_c")),
            a.get("dueDay") or "", "yes" if a.get("isBuffer") else "",
            "yes" if a.get("isSweep") else "",
            "yes" if a.get("participatesInBudget") else ""]
           for a in p.get("accounts", [])])

    # ------------------------------------------------------- income & expenses
    for kind, fname in [("income", "income.csv"), ("expense", "expenses.csv")]:
        rows = []
        for r in p.get("recurrences", []):
            if r.get("kind") != kind:
                continue
            rows.append([
                r.get("name", ""),
                cat_name.get(r.get("categoryId"), ""),
                acct_name.get(r.get("accountId"), ""),
                dollars(r.get("amount_c")),
                r.get("frequency", ""),
                r.get("intervalN") or "",
                r.get("anchorDate", ""),
                r.get("endDate") or "",
                r.get("annualRaisePct") or "",
                r.get("businessDayPolicy", ""),
                r.get("monthEndPolicy", ""),
                r.get("note", ""),
            ])
        write(os.path.join(out, fname),
              ["Name", "Category", "Account", "Amount", "Frequency", "N",
               "Anchor date", "Ends", "Yearly raise %", "Weekends", "Month end", "Note"],
              rows)

    # ------------------------------------------------------------------- goals
    write(os.path.join(out, "goals.csv"),
          ["Goal", "Kind", "Target", "Linked account", "Priority", "Target date"],
          [[g.get("name", ""), g.get("kind", ""), dollars(g.get("targetAmount_c")),
            acct_name.get(g.get("linkedAccountId"), ""),
            g.get("priority") if g.get("priority") is not None else "",
            g.get("targetDate") or ""]
           for g in p.get("goals", [])])

    # -------------------------------------------------------------- categories
    write(os.path.join(out, "categories.csv"),
          ["Group", "Category", "Rollover", "Sinking fund", "Income"],
          [[c.get("group", ""), c.get("name", ""), c.get("rollover", ""),
            "yes" if c.get("isEarmarked") else "",
            "yes" if c.get("isIncome") else ""]
           for c in p.get("categories", [])])

    # ------------------------------------------------------------ transactions
    txrows = []
    for mk in sorted(p.get("transactions", {})):
        for t in p["transactions"][mk]:
            txrows.append([t.get("date", ""), t.get("payee", ""),
                           cat_name.get(t.get("categoryId"), ""),
                           acct_name.get(t.get("accountId"), ""),
                           dollars(t.get("amount_c")), t.get("memo", "")])
    txrows.sort(key=lambda r: r[0])
    write(os.path.join(out, "transactions.csv"),
          ["Date", "Payee", "Category", "Account", "Amount", "Memo"], txrows)

    # ------------------------------------------------------------- the budget
    # One row per category, one column per month — the shape a budget is read in.
    months = sorted(p.get("budgetMonths", {}))
    if months:
        cats = [c for c in p.get("categories", []) if not c.get("isIncome")]
        header = ["Group", "Category"] + months
        rows = []
        for c in cats:
            row = [c.get("group", ""), c.get("name", "")]
            for mk in months:
                row.append(dollars((p["budgetMonths"][mk].get("budgeted") or {}).get(c.get("id"), 0)))
            rows.append(row)
        total = ["", "TOTAL"]
        for mk in months:
            b = p["budgetMonths"][mk].get("budgeted") or {}
            total.append(dollars(sum(b.get(c.get("id"), 0) or 0 for c in cats)))
        rows.append(total)
        write(os.path.join(out, "budget-by-month.csv"), header, rows)

        # per-payday income overrides, if any were used
        ov = []
        for mk in months:
            for k, v in (p["budgetMonths"][mk].get("incomeOverrides") or {}).items():
                rec_id, _, occ = k.partition("|")
                name = next((r.get("name", "") for r in p.get("recurrences", [])
                             if r.get("id") == rec_id), rec_id)
                ov.append([mk, name, occ, dollars(v)])
        if ov:
            write(os.path.join(out, "income-overrides.csv"),
                  ["Month", "Source", "Payday", "Edited amount"], ov)

    # --------------------------------------------------------------- settings
    s = p.get("settings", {}) or {}
    write(os.path.join(out, "settings.csv"), ["Setting", "Value"],
          [["Balances as of", s.get("asOfDate", "")],
           ["Operating floor", dollars(s.get("operatingFloor_c"))],
           ["Buffer already saved", dollars(s.get("bufferHeld_c"))],
           ["Rollover policy", s.get("overspendPolicy", "")],
           ["Budget starts", s.get("budgetStartMonth") or ""],
           ["Months planned ahead", s.get("budgetLookaheadMonths", "")],
           ["Exported", p.get("exportedAt", "")]])

    print("\ndone — import each CSV into Sheets as a new tab")
    return 0


if __name__ == "__main__":
    sys.exit(main())
