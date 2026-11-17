cd "$(dirname "$0")/../../.."
# Ensure there is something to tear down, so the count below is real.
terraform apply -auto-approve -no-color -input=false > /dev/null 2>&1
terraform destroy -auto-approve -no-color -input=false > /tmp/destroy.txt 2>&1
grep "^Destroy complete" /tmp/destroy.txt
cd ..
python scripts/verify_torn_down.py --mask
