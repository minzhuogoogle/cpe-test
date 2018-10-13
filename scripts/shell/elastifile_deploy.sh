cd Terraform-Elastifile-GCP/ 
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json 
gcloud auth activate-service-account --key-file elastifile.json
project='cpe-performance-storage'
zone='us-east1-b'

for i in `gcloud compute instances list --project $project --filter='evm-' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
for i in `gcloud compute instances list --project $project --filter='test-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
terraform init
terraform  apply --auto-approve
NOW=$(date +"%Y%m%d")
HOSTNAME=$(hostname)
instance_name=evm-$HOSTNAME-$NOW
gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$HOSTNAME.$NOW.log

project='cpe-performance-storage'
zone='us-east1-b'
machine_type='n1-standard-4'
gcloud beta compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type  --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  
sleep 1200
