"""Email a batch of LinkedIn post drafts, ready to paste.

    python scripts/send_linkedin_drafts.py

Drafts are written by hand from findings the labs actually produced. Reuses
mailer_config.json from the daily mailer for SMTP.
"""
import io
import json
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG = Path(r"C:\Projects\job-application-agent-code\mailer_config.json")

DRAFTS = [
    dict(
        tag="The mistake post — strongest material you have",
        body="""I wrote a test to prove an analyst role could not read raw data in an S3 lake.

The test failed.

The policy was fine. My test was wrong.

`aws s3 cp` issues a HeadObject before the GET, and a denied HEAD returns a bare 403 Forbidden with no reason attached. My assertion was looking for "AccessDenied" and never found it.

`aws s3api get-object` returns the real thing:

  not authorized to perform: s3:GetObject
  with an explicit deny in an identity-based policy

Two lessons. `aws s3` tells you THAT something failed; `aws s3api` tells you WHAT stopped it. And a test that fails for an unexpected reason is not a passing test — I nearly spent an hour debugging a policy that was already correct.

Week 2 of 52, building AWS data engineering in public."""),

    dict(
        tag="Concept explainer — the locked door",
        body="""A room with no door and a room with a locked door both keep you out today.

But if someone later adds a door to the first room, you can walk in. The locked door stays locked.

That is the difference between implicit deny and explicit deny in IAM.

Implicit: nothing grants you access, so you are refused. Add any policy that grants it later, and you are in.

Explicit: something actively forbids it. No later grant overrides it.

For raw data in a lake — the unconformed landing zone nobody has cleared for general use — I wanted the locked door. AWS's policy simulator distinguishes them by name: implicitDeny vs explicitDeny.

Worth knowing which one your "nobody can access this" actually is."""),

    dict(
        tag="Cost gotcha — these travel furthest",
        body="""A NAT Gateway costs about $32 a month and announces nothing.

It will comfortably outlast your interest in the side project that created it. By the time the bill arrives, it has been running for weeks.

There is not one anywhere in my 52-week AWS lab series. Private subnets reach AWS services through VPC endpoints instead — a gateway endpoint for S3 is free.

Two habits from week 1 that cost nothing:

- Create the budget alarm BEFORE the first resource. It is the only resource whose entire value is preventative.
- Alert on forecast, not just actual. By the time actual spend crosses a threshold, the money is gone. A forecast breach on day three is a warning."""),

    dict(
        tag="A control that surprised me",
        body="""I tried to make an S3 bucket public while running as AdministratorAccess.

AWS said no.

  not authorized to perform: s3:PutBucketPolicy
  because public policies are prevented by the BlockPublicPolicy setting
  in S3 Block Public Access

S3 Block Public Access sits ABOVE identity permissions. An administrator cannot grant public access while it is on. The setting has to be deliberately turned off first — which is a separate action, and one that leaves a record.

That is a meaningfully stronger guarantee than "no policy currently grants public access."

Most accidental data exposure is a bucket somebody made public without meaning to. This is the switch that prevents it, and it is on by default for new buckets."""),

    dict(
        tag="Practice post — short, opinionated",
        body=""""I ran terraform destroy" and "nothing is left" are different claims.

Only the second one keeps the bill at zero.

Destroy can fail partway. A resource created by hand will not be in state. Some services do not propagate tags, so a tag-based sweep misses them entirely.

So after every lab I run a script that checks two things:

1. Everything tagged for the project
2. The services that bill whether tagged or not — EC2, NAT gateways, Elastic IPs, RDS, load balancers, Redshift, MSK, MWAA, OpenSearch

It exits non-zero if anything survived, and no lab gets published until it returns clean.

Took twenty minutes to write. I tested it by planting a resource and confirming it screamed — a guard you have never seen fail is not a guard."""),
]


def main() -> int:
    cfg = json.loads(io.open(CONFIG, encoding="utf-8").read())["email_settings"]

    blocks = []
    for i, d in enumerate(DRAFTS, 1):
        text = (d["body"]
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\n", "<br>"))
        blocks.append(f"""
        <div style="border-left:3px solid #9c6f4f;padding:0 0 0 18px;margin:0 0 34px 0">
          <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;
                      color:#9c6f4f;margin-bottom:10px">Draft {i} &middot; {d['tag']}</div>
          <div style="font-size:15px;line-height:1.65;color:#2d2823;
                      white-space:normal">{text}</div>
        </div>""")

    html = f"""
    <html><body style="margin:0;padding:28px;background:#f6f2ec;
      font-family:Georgia,'Times New Roman',serif;color:#2d2823">
      <div style="max-width:620px;margin:0 auto">
        <h2 style="font-size:22px;font-weight:400;margin:0 0 6px">LinkedIn drafts</h2>
        <p style="font-size:14px;color:#6f665c;font-style:italic;margin:0 0 28px">
          Five posts, each from something that actually happened in weeks 1 and 2.
          Paste as-is or edit. Two a week is plenty.</p>
        {''.join(blocks)}
        <p style="font-size:13px;color:#6f665c;border-top:1px solid #e2dacd;
                  padding-top:16px;margin-top:8px">
          Posting notes: skip the emoji bullets and "Agree? 👇" formatting &mdash;
          it reads as generated, which would undercut work that visibly is not.
          Early on, a substantive comment on a large account reaches more of the
          right people than a post on a small one.</p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[JobAgent] 5 LinkedIn drafts from the AWS labs"
    msg["From"] = cfg["agent_email"]
    msg["To"] = cfg["notification_email"]
    cc = cfg.get("cc", [])
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(cfg.get("smtp_server", "smtp.gmail.com"),
                      cfg.get("smtp_port", 587)) as srv:
        srv.starttls()
        srv.login(cfg["agent_email"], cfg["agent_password"])
        srv.sendmail(cfg["agent_email"],
                     list(dict.fromkeys([cfg["notification_email"]] + cc)),
                     msg.as_string())
    print(f"sent {len(DRAFTS)} drafts to {cfg['notification_email']}"
          + (f" (cc {', '.join(cc)})" if cc else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
