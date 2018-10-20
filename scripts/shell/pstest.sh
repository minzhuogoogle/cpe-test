disktype=$1
echo $disktype
echo `date`
cd gcp-automation/ 
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.lssd 
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.pssd
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.phdd 
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json

cp terraform.tfvars.$disktype terraform.tfvars
export zone=`grep ZONE terraform.tfvars | awk -v N=3 '{print $N}'`
zone=${zone:1:-1}
export project=`grep PROJECT terraform.tfvars | awk -v N=3 '{print $N}'`
project=${project:1:-1}
export cluster_name=`grep CLUSTER_NAME terraform.tfvars | awk -v N=3 '{print $N}'`
cluster_name=${cluster_name:1:-1}
export disk=`grep DISK_TYPE terraform.tfvars | awk -v N=3 '{print $N}'`
disk=${disk:1:-1}
echo $project, $zone, $cluster, $disk

HNOW=$(date +"%Y%m%d")
NOW=`date +%m.%d.%Y.%H.%M.%S`
HOSTNAME=$(hostname)
instance_name=$disktype-$HOSTNAME

for i in `gcloud compute instances list --project $project --filter="$disktype" | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
for i in `gcloud compute instances list --project $project --filter="$disk" | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; doneterraform init
terraform apply --auto-approve

echo `date`


HNOW=$(date +"%Y%m%d")
NOW=`date +%m.%d.%Y.%H.%M.%S`
HOSTNAME=$(hostname)

gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$HOSTNAME.$NOW.txt
machine_type='n1-standard-4'
gcloud compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  
