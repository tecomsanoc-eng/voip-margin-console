"""Turn the original single-file console into a data-free, auth-gated app.

The original bakes its data into six `const` declarations and then runs ~600
lines of render logic against them. Rather than rewrite that logic (and risk
subtle behaviour changes), this rebuilds the page mechanically:

  * the six data constants are dropped;
  * the surviving logic is wrapped in `bootConsole(DATA)`, which receives the
    same six objects from Supabase and is therefore untouched otherwise;
  * a login overlay is placed in front of the dashboard.

Output is public/index.html — roughly 50 KB, containing no business data, which
is what makes it safe to publish on GitHub Pages.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "public", "index.html")

DATA_CONSTS = ["RAW", "CUST", "AMDATA", "CARR", "TRUNK", "DAILY"]

AUTH_CSS = """
/* --- injected by build_app.py: login gate ------------------------------- */
.auth-gate{position:fixed;inset:0;background:var(--bg);display:flex;
  align-items:center;justify-content:center;z-index:100;padding:20px;}
.auth-card{background:var(--panel);border:1px solid var(--border);
  border-radius:14px;padding:30px 28px;width:100%;max-width:360px;}
.auth-card h2{margin:0 0 4px;font-size:19px;font-weight:800;
  letter-spacing:-.01em;}
.auth-sub{color:var(--muted);font-size:12.5px;margin:0 0 20px;}
.auth-card input{width:100%;padding:11px 13px;margin-bottom:10px;
  border-radius:9px;border:1px solid var(--border);background:var(--panel2);
  color:var(--text);font-size:14px;font-family:var(--sans);outline:none;}
.auth-card input:focus{border-color:var(--accent);}
.auth-card button{width:100%;padding:11px;border-radius:9px;border:none;
  background:var(--accent);color:#08131a;font-size:14px;font-weight:700;
  cursor:pointer;font-family:var(--sans);}
.auth-card button:disabled{opacity:.55;cursor:default;}
.auth-msg{margin-top:12px;font-size:12.5px;min-height:17px;line-height:1.5;}
.auth-msg.err{color:var(--red);}
.auth-msg.ok{color:var(--muted);}
.signout{position:fixed;top:16px;right:18px;z-index:50;padding:7px 13px;
  border-radius:8px;border:1px solid var(--border);background:var(--panel);
  color:var(--muted);font-size:11.5px;font-weight:600;cursor:pointer;
  font-family:var(--sans);}
.signout:hover{color:var(--accent);border-color:var(--accent);}
"""

LOGIN_MARKUP = """<div class="auth-gate" id="authGate">
  <form class="auth-card" id="authForm" autocomplete="on">
    <h2>VoIP Margin Console</h2>
    <p class="auth-sub">Sign in to load margin data.</p>
    <input id="authEmail" type="email" placeholder="you@tecomsa.me" required
           autocomplete="username">
    <input id="authPassword" type="password" placeholder="Password" required
           autocomplete="current-password">
    <button id="authSubmit" type="submit">Sign in</button>
    <div class="auth-msg" id="authMsg"></div>
  </form>
</div>
<button class="signout" id="signOutBtn" style="display:none;">Sign out</button>
"""

BOOT_PREFIX = """// Data now arrives from Supabase instead of being baked into this file.
// Everything below is the original render logic, unchanged, reading the same
// six objects it always did.
function bootConsole(DATA){
const RAW    = DATA.RAW;
const CUST   = DATA.CUST;
const AMDATA = DATA.AMDATA;
const CARR   = DATA.CARR;
const TRUNK  = DATA.TRUNK;
const DAILY  = DATA.DAILY;
"""

BOOT_SUFFIX = """}
window.bootConsole = bootConsole;
"""

HEAD_SCRIPTS = """<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>
<script src="./config.js"></script>
"""


def find_line(lines, predicate, what):
    for i, line in enumerate(lines):
        if predicate(line):
            return i
    sys.exit("Could not locate %s in the source HTML." % what)


def main():
    if len(sys.argv) < 2:
        print("usage: build_app.py <path-to-original.html>")
        return 1

    with io.open(sys.argv[1], "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    style_end   = find_line(lines, lambda l: l.strip() == "</style>", "</style>")
    head_end    = find_line(lines, lambda l: l.strip() == "</head>", "</head>")
    body_open   = find_line(lines, lambda l: l.strip() == "<body>", "<body>")
    script_open = find_line(lines, lambda l: l.strip() == "<script>", "<script>")

    # The data constants sit directly after <script>; find the last of them so
    # the split point survives them being reordered upstream.
    const_re = re.compile(r"^const\s+(%s)\s*=" % "|".join(DATA_CONSTS))
    data_idx = [i for i, l in enumerate(lines)
                if i > script_open and const_re.match(l)]
    if len(data_idx) != len(DATA_CONSTS):
        sys.exit("Expected %d data constants, found %d — aborting rather than "
                 "guessing where the logic starts."
                 % (len(DATA_CONSTS), len(data_idx)))
    logic_start = max(data_idx) + 1

    logic_end = len(lines) - 1 - find_line(
        list(reversed(lines)), lambda l: l.strip() == "</script>", "</script>")

    body_inner = lines[body_open + 1:script_open]
    # Keep the dashboard hidden until a session exists.
    body_inner = [
        l.replace('<div class="wrap">', '<div class="wrap" id="appWrap" style="display:none;">')
        for l in body_inner
    ]

    out = []
    out += lines[:style_end]                       # everything up to </style>
    out += AUTH_CSS.rstrip("\n").split("\n")       # extra rules, still inside it
    out += lines[style_end:head_end]               # </style> .. just before </head>
    out += ["</head>", "<body>"]
    out += LOGIN_MARKUP.rstrip("\n").split("\n")
    out += body_inner
    out += HEAD_SCRIPTS.rstrip("\n").split("\n")
    out += ["<script>"]
    out += BOOT_PREFIX.rstrip("\n").split("\n")
    out += lines[logic_start:logic_end]
    out += BOOT_SUFFIX.rstrip("\n").split("\n")
    out += ["</script>", '<script src="./auth.js"></script>', "</body>", "</html>"]

    text = "\n".join(out)

    out_dir = os.path.dirname(OUT)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)

    print("wrote %s" % OUT)
    print("  %.1f KB, %d lines" % (len(text.encode("utf-8")) / 1024.0,
                                   len(out)))

    # Guard against the whole point of this script silently failing. A leaked
    # dataset would be a JSON literal on the right-hand side, not a reference
    # to DATA, so match the literal form specifically.
    # The only assignment we expect is `const NAME = DATA.NAME;` — anything
    # else on the right-hand side means a dataset survived the rewrite.
    leaked = []
    for n in DATA_CONSTS:
        m = re.search(r"^const\s+%s\s*=\s*(\S+)" % n, text, re.MULTILINE)
        if m is None or not m.group(1).startswith("DATA."):
            leaked.append(n)
    longest = max(len(l) for l in out)
    if leaked:
        sys.exit("REFUSING OUTPUT: %s still embedded." % ", ".join(leaked))
    if longest > 5000:
        sys.exit("REFUSING OUTPUT: a %d-char line suggests embedded data."
                 % longest)
    print("  verified: no embedded datasets (longest line %d chars)" % longest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
