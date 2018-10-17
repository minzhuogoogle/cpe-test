date
rm -rf Terraform-Elastifile-GCP
#git clone https://github.com/minzhuogoogle/Terraform-Elastifile-GCP.git
git clone https://github.com/Elastifile/gcp-automation.git
echo sunnydog > gcp-automation/password.txt
cd gcp-automation/ 
#gsutil cp gs://elastifile_test/nelastifile.json elastifile.json
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json
#project='gtp-cpe-integration-testing'
#zone='us-west1-b'

project='cpe-performance-storage'
zone='us-east1-b'

for i in `gcloud compute instances list --project $project --filter='evm-' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
#for i in `gcloud compute instances list --project $project --filter='try-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
date
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars
#terraform init
#terraform  apply --auto-approve
date
NOW=$(date +"%Y%m%d")
#NOW=`date +%m.%d.%Y.%H.%M.%S`
HOSTNAME=$(hostname)
instance_name=evm-$HOSTNAME-$NOW

#gsutil cp create_vheads.log gs://elastifile_test/test_result/create_vheads.$HOSTNAME.$NOW.log
#gsutil cp create_vheads.log gs:/cpe-performance-storage/test_result/create_vheads.$HOSTNAME.$NOW.log
machine_type='n1-standard-4'
gcloud compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  

#for i in 1 2 3 4 5 6 7 8 9; do 
#    sleep 1500
#    gcloud compute instances delete $instance_name --project $project --zone $zone -q
#    gcloud beta compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  
#done
