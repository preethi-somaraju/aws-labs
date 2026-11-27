"""Print a post's headings and figure captions in document order.

    python scripts/figure_order.py ../Preethi/blog/aws-lab-03-s3-data-lake.html

Run before publishing. A figure showing a result should come after the figure
showing it being built, and figure numbers should ascend down the page.
Exits non-zero if they do not.
"""
import io
import re
import sys

TAG = re.compile(r"<h2>(.*?)</h2>|<figcaption>(.*?)</figcaption>", re.S)
NUM = re.compile(r"Figure (\d+)")


def text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    src = io.open(sys.argv[1], encoding="utf-8").read()

    seen, unnumbered = [], 0
    for m in TAG.finditer(src):
        if m.group(1):
            print(f"\n{text(m.group(1))}")
            continue
        cap = text(m.group(2))
        print(f"    {cap[:88]}")
        n = NUM.match(cap)
        if n:
            seen.append(int(n.group(1)))
        else:
            unnumbered += 1

    print()
    problems = []
    if unnumbered:
        problems.append(f"{unnumbered} caption(s) with no figure number")
    if seen != sorted(seen):
        problems.append(f"figure numbers out of document order: {seen}")
    if seen and seen != list(range(1, len(seen) + 1)):
        problems.append(f"figure numbers are not 1..{len(seen)}: {seen}")

    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print(f"{len(seen)} figures, numbered in document order.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
