cd "$(dirname "$0")/../../.."
terraform apply -auto-approve -no-color -input=false > /tmp/apply03.txt 2>&1
grep "Creation complete" /tmp/apply03.txt | sed 's/ \[id=.*//' | tail -n 10
grep "^Apply complete" /tmp/apply03.txt
