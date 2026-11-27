"""Point the GitHub profile README at the lab just published.

    python scripts/update_profile.py 03 "S3 as a data lake" \
        aws-lab-03-s3-data-lake "a bucket that refuses writes outside its own
        zones, and 5 MiB of billed storage that appears in no listing."

The profile lives in its own repo (preethi-somaraju/preethi-somaraju), which is
why it kept going stale: it is not checked out beside the lab or the site. This
clones it to a temp dir, rewrites the Latest line, and pushes.
"""
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "preethi-somaraju/preethi-somaraju"
SITE = "https://preethi-somaraju.github.io/blog"
AUTHOR = ("Preethi Somaraju", "304569681+preethi-somaraju@users.noreply.github.com")


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    num, title, slug, blurb = sys.argv[1:]
    blurb = " ".join(blurb.split())

    work = Path(tempfile.mkdtemp(prefix="profile-"))
    run(["gh", "repo", "clone", REPO, str(work), "--", "--quiet"], cwd=None)

    readme = work / "README.md"
    s = io.open(readme, encoding="utf-8").read()
    new = (f"Latest: **[Lab {num} — {title}]({SITE}/{slug}.html)**\n"
           f"— {blurb}")
    s2, n = re.subn(r"Latest: \*\*\[Lab .*?\n(?:—.*?\n)(?:.*?\n)*?(?=\n)",
                    new + "\n", s, count=1)
    if not n:
        raise SystemExit("no Latest line found; the README changed shape")

    io.open(readme, "w", encoding="utf-8", newline="\n").write(s2)
    run(["git", "config", "user.name", AUTHOR[0]], cwd=work)
    run(["git", "config", "user.email", AUTHOR[1]], cwd=work)
    if not run(["git", "status", "--porcelain"], cwd=work).strip():
        print("profile already current")
        return 0
    run(["git", "commit", "-qam", f"Point the latest-lab line at lab {num}"], cwd=work)
    run(["git", "push", "-q", "origin", "HEAD"], cwd=work)
    print(f"profile now points at lab {num}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
