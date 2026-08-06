"""Pull the six hardcoded datasets out of the original single-file console.

The source HTML bakes ~5.4 MB of JSON into `const NAME = {...};` statements.
This lifts each one into data/NAME.json so the rest of the pipeline never has
to parse HTML again. Run once against the original file.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "data")

# Order matters only for readable output.
NAMES = ["RAW", "CUST", "AMDATA", "CARR", "TRUNK", "DAILY"]


def extract(html_path):
    with open(html_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    found = {}
    for name in NAMES:
        # Each declaration sits alone on its own line, so anchor to line start
        # and take everything up to the trailing semicolon at line end.
        pattern = re.compile(
            r"^const\s+%s\s*=\s*(.+?);\s*(?://.*)?$" % re.escape(name),
            re.MULTILINE,
        )
        match = pattern.search(text)
        if not match:
            print("  ! %s not found" % name)
            continue
        found[name] = json.loads(match.group(1))
    return found


def describe(name, obj):
    if isinstance(obj, list):
        return "list, %d entries" % len(obj)
    if isinstance(obj, dict):
        bits = []
        for key, val in obj.items():
            if isinstance(val, list):
                bits.append("%s=%d" % (key, len(val)))
            elif isinstance(val, dict):
                bits.append("%s={%d}" % (key, len(val)))
            else:
                bits.append("%s=%r" % (key, val))
        return "dict(%s)" % ", ".join(bits)
    return type(obj).__name__


def main():
    if len(sys.argv) < 2:
        print("usage: extract_from_html.py <path-to-console.html>")
        return 1
    html_path = sys.argv[1]

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    data = extract(html_path)
    for name, obj in data.items():
        out = os.path.join(OUT_DIR, "%s.json" % name.lower())
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        size_mb = os.path.getsize(out) / 1048576.0
        print("%-8s %-7.2f MB  %s" % (name, size_mb, describe(name, obj)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
