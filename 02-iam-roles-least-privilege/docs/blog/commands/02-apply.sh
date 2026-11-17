cd "$(dirname "$0")/../../.."
# Start from nothing so this is a real create, not a no-op re-apply.
terraform destroy -auto-approve -no-color -input=false > /dev/null 2>&1
terraform apply -auto-approve -no-color -input=false > /tmp/apply.txt 2>&1
# Resource IDs carry the account number, so project only type and status.
grep "Creation complete" /tmp/apply.txt | sed 's/ \[id=.*//' | tail -8
grep "^Apply complete" /tmp/apply.txt
