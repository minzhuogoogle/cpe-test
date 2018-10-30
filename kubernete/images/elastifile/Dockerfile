# Copyright 2017 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Includes go and gcloud
FROM gcr.io/cpe-performance-storage/baseimage:latest
#FROM gcr.io/gtp-cpe-integration-testing/baseimage:latest
LABEL maintainer="mzhuo@google.com"

# add env we can debug with the image name:tag
ARG IMAGE_ARG
ENV IMAGE=${IMAGE_ARG}


WORKDIR /workspace

Run wget https://releases.hashicorp.com/terraform/0.11.8/terraform_0.11.8_linux_amd64.zip && \
    unzip terraform_0.11.8_linux_amd64.zip && \
    cp terraform /usr/local/bin/. && \
    git clone https://github.com/Elastifile/gcp-automation.git && \
    echo sunnydog > gcp-automation/password.txt && \
    cd gcp-automation && \
    curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.lssd && \
    curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.pssd && \
    curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.phdd  

#ADD runner /
ENTRYPOINT ["/bin/bash"]
#, "/runner"]
