"""Fail if a lab left anything behind.

    python scripts/verify_torn_down.py            # after a lab's terraform destroy
    python scripts/verify_torn_down.py --json

Runs after every destroy. "I ran destroy" and "nothing is left" are different
claims, and only the second one keeps the bill at zero.

Two passes, because either alone misses things:

  1. Everything tagged Project=aws-labs. Catches anything Terraform created
     through the provider's default_tags.
  2. The expensive services directly, tags or not. A resource created by hand,
     or one AWS does not propagate tags to, still bills. NAT gateways and idle
     Redshift workgroups are the realistic ways to lose money here.

Lab 01 is permanent infrastructure for the series, so its three resources are
allowed. Anything else is a finding.
"""
import argparse
import json
import subprocess
import sys

REGIONS = ["us-east-1"]

# Lab 01 builds the floor every later lab stands on; it is meant to survive.
PERMANENT = (
    "aws-labs-tfstate-",      # terraform state bucket
    "aws-labs-tflock",        # state lock table
    "aws-labs-monthly",       # budget
)


def aws(args, profile, region=None):
    cmd = ["aws", *args, "--profile", profile, "--output", "json"]
    if region:
        cmd += ["--region", region]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or "null")
    except json.JSONDecodeError:
        return None


def permanent(arn):
    return any(p in arn for p in PERMANENT)


def tagged_resources(profile, region):
    out = aws(["resourcegroupstaggingapi", "get-resources",
               "--tag-filters", "Key=Project,Values=aws-labs"], profile, region)
    if not out:
        return []
    return [m["ResourceARN"] for m in out.get("ResourceTagMappingList", [])]


# (label, aws cli args, jmespath-free extractor) — kept explicit so a failure
# in one service does not hide the others.
def billable(profile, region):
    found = []

    def add(label, items):
        for i in items or []:
            found.append(f"{label}: {i}")

    r = aws(["ec2", "describe-instances",
             "--filters", "Name=instance-state-name,Values=running,stopped"],
            profile, region)
    if r:
        add("EC2", [i["InstanceId"]
                    for res in r.get("Reservations", []) for i in res.get("Instances", [])])

    r = aws(["ec2", "describe-nat-gateways",
             "--filter", "Name=state,Values=available,pending"], profile, region)
    if r:
        add("NAT gateway", [n["NatGatewayId"] for n in r.get("NatGateways", [])])

    r = aws(["ec2", "describe-addresses"], profile, region)
    if r:
        add("Elastic IP", [a.get("AllocationId") for a in r.get("Addresses", [])])

    r = aws(["rds", "describe-db-instances"], profile, region)
    if r:
        add("RDS", [d["DBInstanceIdentifier"] for d in r.get("DBInstances", [])])

    r = aws(["elbv2", "describe-load-balancers"], profile, region)
    if r:
        add("Load balancer", [l["LoadBalancerName"] for l in r.get("LoadBalancers", [])])

    r = aws(["redshift-serverless", "list-workgroups"], profile, region)
    if r:
        add("Redshift workgroup", [w["workgroupName"] for w in r.get("workgroups", [])])

    r = aws(["kafka", "list-clusters-v2"], profile, region)
    if r:
        add("MSK cluster", [c["ClusterName"] for c in r.get("ClusterInfoList", [])])

    r = aws(["mwaa", "list-environments"], profile, region)
    if r:
        add("MWAA environment", r.get("Environments", []))

    r = aws(["opensearch", "list-domain-names"], profile, region)
    if r:
        add("OpenSearch domain",
            [d["DomainName"] for d in r.get("DomainNames", [])])

    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="preethi-portfolio")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    findings, kept = [], []
    for region in REGIONS:
        for arn in tagged_resources(args.profile, region):
            (kept if permanent(arn) else findings).append(f"tagged: {arn}")
        findings += [f"{region} {f}" for f in billable(args.profile, region)]

    if args.json:
        print(json.dumps({"findings": findings, "permanent": kept}, indent=2))
    else:
        print(f"Permanent (expected, {len(kept)}):")
        for k in kept:
            print("   " + k.replace("tagged: ", ""))
        print()
        if findings:
            print(f"LEFT BEHIND ({len(findings)}):")
            for f in findings:
                print("   " + f)
            print("\nDestroy did not finish. Resolve before publishing the lab.")
        else:
            print("Clean: nothing left behind.")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
