"""
Derive every other build from index.html, so they can never drift again.

index.html is the ONLY hand-edited file. It is the Supabase build. Everything
else here is index.html with the cloud turned off, which is a two-line change
rather than surgery: with placeholder credentials cloudConfigured() is false,
loadAll() never reaches Supabase, and the app falls through to the artifact
database and then to localStorage exactly as it was designed to.
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "index.html")
src = io.open(SRC, encoding="utf-8").read()


def decloud(s):
    """Turn the cloud off without removing the code that implements it."""
    # 1. the client is dead weight once the keys are placeholders
    tag = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>\n'
    assert tag in s, "supabase script tag not found"
    s = s.replace(tag, "", 1)

    # 2. the real project must not ship inside a file anyone can open
    url = re.search(r'const SUPABASE_URL = "([^"]*)";', s)
    key = re.search(r'const SUPABASE_KEY = "([^"]*)";', s)
    assert url and key, "supabase constants not found"
    s = s.replace(url.group(0), 'const SUPABASE_URL = "PASTE_YOUR_PROJECT_URL_HERE";', 1)
    s = s.replace(key.group(0), 'const SUPABASE_KEY = "PASTE_YOUR_PUBLISHABLE_KEY_HERE";', 1)

    assert url.group(1) not in s and key.group(1) not in s, "credentials survived the strip"
    return s


def seed_payload(s, payload):
    """Bake a backup in, so the file opens with the figures already there."""
    assert 'const SEED_MODE = "blank";' in s
    s = s.replace('const SEED_MODE = "blank";',
                  'const SEED_MODE = "payload";\nconst SEED_PAYLOAD = '
                  + json.dumps(payload, separators=(",", ":")) + ";", 1)
    old = """async function seedFirstRun(){
  const blank = SEED_MODE === "blank";"""
    new = """async function seedFirstRun(){
  // A file built with a backup baked in opens with the figures already there,
  // instead of asking someone to find and import a second file.
  if (SEED_MODE === "payload"){
    applyPayload(JSON.parse(JSON.stringify(SEED_PAYLOAD)));
    persistCore();
    for (const k of Object.keys(state.txMonths)) persistMonth(k);
    for (const k of Object.keys(state.budgetMonths)) persistBudget(k);
    return;
  }
  const blank = SEED_MODE === "blank";"""
    assert old in s, "seedFirstRun not found"
    return s.replace(old, new, 1)


def retitle(s, title):
    return re.sub(r"<title>[^<]*</title>", "<title>" + title + "</title>", s, count=1)


def write(path, s, label):
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("  %-22s %7d bytes   %s" % (os.path.basename(path), len(s), label))


print("building from index.html (%d bytes)\n" % len(src))

# ---------------------------------------------------------------- 1. standalone
# The published, shareable build: no login, no account, no data. Saves to the
# artifact database when it has one, otherwise to the browser it is opened in.
solo = retitle(decloud(src), "Better Budget")
write(os.path.join(ROOT, "standalone.html"), solo, "no login, starts empty")

# ---------------------------------------------------------------- 2. my-budget
# The same file with a backup baked in. Gitignored — it holds real figures.
def newest_backup():
    """The most recently exported backup in the folder, whatever it is called.

    Baking a stale snapshot is worse than baking none: it opens full of numbers
    that look current and are not. So the file is chosen by the timestamp INSIDE
    it, not by its name or its mtime.
    """
    best, best_when = None, ""
    for f in os.listdir(ROOT):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(io.open(os.path.join(ROOT, f), encoding="utf-8"))
        except Exception:
            continue
        if d.get("app") != "better-budget":
            continue
        when = str(d.get("exportedAt") or "")
        if when >= best_when:
            best, best_when = os.path.join(ROOT, f), when
    return best


backup_path = newest_backup()
if backup_path:
    payload = json.load(io.open(backup_path, encoding="utf-8"))
    mine = seed_payload(retitle(decloud(src), "My Budget"), payload)
    write(os.path.join(ROOT, "my-budget.html"), mine,
          "offline, " + os.path.basename(backup_path) + " (" +
          str(payload.get("exportedAt", "?"))[:10] + ") baked in")
else:
    print("  my-budget.html         SKIPPED — no backup .json found")

print("\ndone")
