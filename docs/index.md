# Getting Started

## Logging in to the UChicago Analysis Facility

First you will need to sign up on the [Analysis Facility website](https://af.uchicago.edu). 

Please use your institutional or CERN identity (lxplus username) when signing up, as this will make the approval process smoother. You should set your institution to be your home institute. If e.g. you are from the University of Chicago but use your CERN credentials, you should set the institution under your profile to be the University of Chicago.

As part of signing up you will need to upload an SSH Public Key.

If you are not sure if you have generated an SSH Public Key before, try the following command (Mac/Linux) on your laptop to print the content of the file that contains the SSH Public Key:

    cat ~/.ssh/id_rsa.pub

If the file exists, you should be able to copy the contents of this file to your profile on the AF website.

    Important: Do not copy the contents of a file that does not end in .pub. You must only upload the public (.pub) part of the key.

If you do not have a public key (the file doesn't exist), you can generate one via the following command (Mac/Linux):

    ssh-keygen -t rsa

Upload the resulting public key (ending in .pub) to your profile.

Once you have uploaded a key, it will take a little bit of time to process your profile and add your account to the system. After 10-15 minutes, you ought to be able to login via SSH:

    ssh <username>@login.af.uchicago.edu

If it does not work, please double check that you have been approved, have a public key uploaded and have waited at least 15 minutes. If you still have an issue, feel free to reach out to us for help.

## Using Analysis Facility Filesystems

The UChicago analysis facility has three filesystems that you should be aware of when running workloads. The table below describes their differences:

| Filesystem | Quota  | Path        | Backup         | Notes                                                  |
| ---------- | ------ | ----------- | -------------- | ------------------------------------------------------ |
| $HOME      | 100 GB | /home/$USER | Yes            | Solid-state filesystem, shared to all worker nodes     |
| $DATA      | 5 TB  | /data/$USER | No             | CephFS filesystem, shared to all worker nodes          |
| $SCRATCH   | n/a    | /scratch    | No             | Ephemeral storage for workloads, local to worker nodes |

<!-- here need to describe which ones are used for what eg. for jobs submission, from jupyter notebook, etc. -->
