cd "$(dirname "$0")/../../.."
# Ensure there is something to tear down, so the count below is real.
terraform apply -auto-approve -no-color -input=false > /dev/null 2>&1
terraform destroy -auto-approve -no-color -input=false > /tmp/destroy.txt 2>&1
# Resource IDs carry the account number, so project only type and status.
grep "Destruction complete" /tmp/destroy.txt | sed 's/ \[id=.*//' | tail -9
grep "^Destroy complete" /tmp/destroy.txt
