cd "$(dirname "$0")/../../.."
terraform destroy -auto-approve -no-color -input=false > /tmp/destroy03.txt 2>&1
grep "Destruction complete" /tmp/destroy03.txt | sed 's/ \[id=.*//' | tail -n 10
grep "^Destroy complete" /tmp/destroy03.txt
