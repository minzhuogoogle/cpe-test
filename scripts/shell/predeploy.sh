date
wget https://releases.hashicorp.com/terraform/0.11.8/terraform_0.11.8_linux_amd64.zip
unzip terraform_0.11.8_linux_amd64.zip
cp terraform /usr/local/bin/. 
git clone https://github.com/Elastifile/gcp-automation.git
echo sunnydog > gcp-automation/password.txt

gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json

HNOW=$(date +"%Y%m%d")
NOW=`date +%m.%d.%Y.%H.%M.%S`
HOSTNAME=$(hostname)
instance_name=evm-$HOSTNAME

for i in `gcloud compute instances list --project $project --filter='elfs' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done

date
cd gcp-automation/ 
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.local.ssd
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.pssd
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.phhd

elfs_types=("terraform.tfvars.local.ssd" "terraform.tfvars.pssd" "terraform.tfvars.phhd" )
for i in "${elfs_types[@]}"
do   
   echo "Start provision", $i   
   terraform init
   terraform apply -var-file $i --auto-approve   
   date
   export zone=`grep ZONE terraform.tfvars | awk -v N=3 '{print $N}'`
   export project=`grep PROJECT terraform.tfvars | awk -v N=3 '{print $N}'`
   export cluster_name=`grep CLUSTER_NAME terraform.tfvars | awk -v N=3 '{print $N}'`
   export disk=`grep DISK_TYPE terraform.tfvars | awk -v N=3 '{print $N}'`

   HNOW=$(date +"%Y%m%d")
   NOW=`date +%m.%d.%Y.%H.%M.%S`
   HOSTNAME=$(hostname)
   instance_name=elfs-$disk-$HOSTNAME
   echo $instance_name
   cat $i >> create_vheads.log 
   gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$HOSTNAME.$NOW.txt
   machine_type='n1-standard-4'
   gcloud compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh  
done
