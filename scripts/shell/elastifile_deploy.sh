date
cd Terraform-Elastifile-GCP/ 
gsutil cp gs://elastifile_test/nelastifile.json elastifile.json 
#gcloud auth activate-service-account --key-file elastifile.json
project='gtp-cpe-integration-testing'
zone='us-west1-a'

for i in `gcloud compute instances list --project $project --filter='evm-' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
for i in `gcloud compute instances list --project $project --filter='test-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
date
terraform init
terraform  apply --auto-approve
date
NOW=$(date +"%Y%m%d")
HOSTNAME=$(hostname)
instance_name=evm-$HOSTNAME-$NOW
gsutil cp create_vheads.log gs://elastifile_test/test_result/create_vheads.$HOSTNAME.$NOW.log


machine_type='n1-standard-4'
gcloud beta compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type  --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  
date
sleep 6000
date

