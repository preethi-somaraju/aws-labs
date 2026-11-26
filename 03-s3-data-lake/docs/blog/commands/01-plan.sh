cd "$(dirname "$0")/../../.."
terraform plan -no-color -input=false > /tmp/plan03.txt
tail -n 20 /tmp/plan03.txt
