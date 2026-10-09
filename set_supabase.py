"""
Point the app at a Supabase project.

    python set_supabase.py https://YOURREF.supabase.co sb_publishable_xxxxxxxx

Validates both values, rewrites the two constants in index.html, and rebuilds the
derived files. Refuses a secret key outright: that one bypasses row-level security,
and in a file served to a browser it would hand every visitor every budget.

Nothing is printed in full and nothing is committed — run git yourself once you
have checked the diff.
"""
import io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "index.html")

URL_RE = re.compile(r"^https://[a-z0-9-]+\.supabase\.(co|in)$")
PUBLISHABLE_RE = re.compile(r"^(sb_publishable_[A-Za-z0-9_\-]{10,}|eyJ[A-Za-z0-9_\-.]{30,})$")
SECRET_RE = re.compile(r"sb_secret_|service_role")


def fail(msg):
    print("\n  " + msg + "\n")
    return 1


def mask(v):
    return v[:18] + "…" + v[-4:] if len(v) > 26 else v[:6] + "…"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    url = sys.argv[1].strip().rstrip("/")
    key = sys.argv[2].strip()

    # ---- the url -----------------------------------------------------------
    if "/rest/v1" in url or "/auth/v1" in url:
        return fail("That is an API endpoint, not the project URL. Drop everything "
                    "after .supabase.co — the client adds the path itself.")
    if not URL_RE.match(url):
        return fail("That does not look like a project URL. It should be exactly\n"
                    "  https://<your-ref>.supabase.co\n"
                    "from Settings -> Data API -> Project URL.")

    # ---- the key -----------------------------------------------------------
    if SECRET_RE.search(key):
        return fail("That is your SECRET key. It bypasses row-level security, so in a\n"
                    "  file anyone can open it would expose every budget to every visitor.\n"
                    "  Use the PUBLISHABLE key from Settings -> API Keys. Nothing was changed.")
    if not PUBLISHABLE_RE.match(key):
        return fail("That does not look like a publishable key. It should start with\n"
                    "  sb_publishable_ (or eyJ for an older project).")

    # ---- patch -------------------------------------------------------------
    s = io.open(SRC, encoding="utf-8").read()
    old_url = re.search(r'const SUPABASE_URL = "([^"]*)";', s)
    old_key = re.search(r'const SUPABASE_KEY = "([^"]*)";', s)
    if not old_url or not old_key:
        return fail("Could not find the two constants in index.html.")

    if old_url.group(1) == url and old_key.group(1) == key:
        print("\nAlready pointing there. Nothing to do.\n")
        return 0

    print("\n  was   " + old_url.group(1))
    print("  now   " + url)
    print("  key   " + mask(old_key.group(1)) + "  ->  " + mask(key) + "\n")

    s = s.replace(old_url.group(0), 'const SUPABASE_URL = "%s";' % url, 1)
    s = s.replace(old_key.group(0), 'const SUPABASE_KEY = "%s";' % key, 1)
    io.open(SRC, "w", encoding="utf-8", newline="").write(s)
    print("  index.html updated")

    # the old project's values must not survive anywhere in the tree
    stale = [old_url.group(1).split("//")[-1].split(".")[0], old_key.group(1)]
    build = os.path.join(ROOT, "build.py")
    if os.path.exists(build):
        subprocess.run([sys.executable, build], cwd=ROOT)

    leaked = []
    for f in ("standalone.html", "my-budget.html"):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        t = io.open(p, encoding="utf-8").read()
        for bad in [url, key] + stale:
            if bad and bad in t:
                leaked.append((f, bad[:20]))
    print("\n  published builds carry no keys: " + ("yes" if not leaked else "NO -> " + str(leaked)))

    print("""
  Next:
    1. git diff index.html        -- check only those two lines moved
    2. git add -A && git commit -m "Point at the new Supabase project"
    3. git push
    4. Open the app with a cache-buster, create your account, then
       Data -> Restore from file with your backup JSON.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
