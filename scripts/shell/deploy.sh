#!/bin/sh

echo sudo rm /var/lib/dpkg/lock
sudo rm /var/lib/dpkg/lock
sudo dpkg --configure -a

gcloud auth activate-service-account 828983778729-compute@developer.gserviceaccount.com --key-file=creds.json
gcloud compute instances list --project gtp-cpe-integration-testing --filter='ef-test'
# Delete any existing instances
echo "Deleting instances."
for i in `gcloud compute instances list --project gtp-cpe-integration-testing --filter='ef-test' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project gtp-cpe-integration-testing --zone us-west1-a -q; done

echo mkdir -p terraform
mkdir -p terraform
cd terraform
wget https://releases.hashicorp.com/terraform/0.11.8/terraform_0.11.8_linux_amd64.zip
unzip terraform_0.11.8_linux_amd64.zip
echo sudo cp terraform /usr/local/bin/.
sudo cp terraform /usr/local/bin/.
cd ~
echo mkdir elastifile
mkdir elastifile
cd elastifile/
git clone https://github.com/66fastback/Terraform-Elastifile-GCP.git
cd Terraform-Elastifile-GCP/
echo changeme > password.txt
cp /creds.json .
cp /terraform.tfvars .
ls -l
terraform init
echo terraform apply -auto-approve
terraform apply -auto-approve
cat ./create_vheads.log
terraform destroy -auto-approve
for i in `gcloud compute instances list --project gtp-cpe-integration-testing --filter='ef-test' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project gtp-cpe-integration-testing --zone us-west1-a -q; done
