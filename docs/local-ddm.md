## Accessing data directly from DDMs

If your dataset is available at the local DDM endpoint (eg. MWT2_UC_LOCALGROUPDISK), it would be very performat to read the data directly from it.
First you need to discover paths to the files of your dataset. This is easiest done in Rucio.
You would issue a command like:

```bash
setupATLAS
lsetup rucio
rucio
# get your grid proxy
voms-proxy-init -voms atlas
rucio list-file-replicas user.ivukotic:xcache.test.dat --protocols root --pfns
```

This will give you a list of paths to all of the files and all the replicas in your dataset.
You can also limit it to only paths to specific RSES:

```bash
rucio list-file-replicas user.ivukotic:xcache.test.dat --protocols root --pfns --rses MWT2_UC_LOCALGROUPDISK
# output will look like this:
# root://fax.mwt2.org:1094//pnfs/uchicago.edu/atlaslocalgroupdisk/rucio/user/ivukotic/7d/9b/xcache.test.dat
```

If you need only some files, you can simply grep or awk for them and save filepaths to txt file that your jobs will use.
