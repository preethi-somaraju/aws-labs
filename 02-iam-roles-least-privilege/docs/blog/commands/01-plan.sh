cd "$(dirname "$0")/../../.."
terraform plan -no-color -input=false > /tmp/plan.txt
tail -n 22 /tmp/plan.txt
