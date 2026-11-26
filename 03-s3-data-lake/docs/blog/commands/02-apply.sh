cd "$(dirname "$0")/../../.."
# The capture runs these commands twice: once headless to scan the output for
# credentials, once in the window. Starting from nothing makes both a real
# create rather than a no-op re-apply.
terraform destroy -auto-approve -no-color -input=false > /dev/null 2>&1
terraform apply -auto-approve -no-color -input=false > /tmp/apply03.txt 2>&1
grep "Creation complete" /tmp/apply03.txt | sed 's/ \[id=.*//' | tail -n 10
grep "^Apply complete" /tmp/apply03.txt
