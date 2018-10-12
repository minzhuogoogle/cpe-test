#!/bin/bash

# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#

cd Terraform-Elastifile-GCP
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json .
gcloud auth activate-service-account --key-file  cpe-performance-storage-b13c1a7348ad.json;
terraform init;
terraform  apply --auto-approve
