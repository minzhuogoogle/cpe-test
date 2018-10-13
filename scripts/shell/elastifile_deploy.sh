cd Terraform-Elastifile-GCP/ 
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json 
gcloud auth activate-service-account --key-file elastifile.json
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

# --service-account=127791159139-compute@developer.gserviceaccount.com --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append --image=ubuntu-1604-lts-drawfork-v20180810 --image-project=eip-images --boot-disk-size=10GB --boot-disk-type=pd-standard --boot-disk-device-name=instance-2

