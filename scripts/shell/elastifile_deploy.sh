cd Terraform-Elastifile-GCP/ 
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json 
gcloud auth activate-service-account --key-file elastifile.json
project='cpe-performance-storage'
zone='us-east1-b'

for i in `gcloud compute instances list --project $project --filter='test-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone; done
terraform init
terraform  apply --auto-approve
NOW=$(date +"%m.%d.%Y")
HOSTNAME=$(hostname)
gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$HOSTNAME.$NOW.log

project='cpe-performance-storage'
instance_name=$HOSTNAME_$NOW
zone='us-east1-b'
machine_type='n1-standard-4'
gcloud beta compute --project=$project instances create $instance_name --zone=$zone --machine-type=$machine_type --metadata=startup-script=curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh$'\n'sudo\ chmod\ 777\ vm_runfio.sh$'\n'sudo\ ./vm_runfio.sh --boot-disk-size=10GB

