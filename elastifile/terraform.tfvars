EMPLATE_TYPE = "small"
#small,medium,standard,custom
NUM_OF_VMS = "3"
USE_LB = "true"
DISK_TYPE = "local"
#local,ssd,hdd
VM_CONFIG = "4_32"
# <cpucores>_<ram> default: 4_42
DISK_CONFIG = "4_375"
# <num_of_disks>_<disk_size>
MIN_CLUSTER = "3"
CLUSTER_NAME = "try-elastifile-storage"
ZONE = "us-east1-b"
PROJECT = "cpe-performance-storage"
SUBNETWORK = "default"
IMAGE = "elastifile-storage-2-7-5-12-ems"
CREDENTIALS = "elastifile.json"
SERVICE_EMAIL = "storage@cpe-performance-storage.iam.gserviceaccount.com"
