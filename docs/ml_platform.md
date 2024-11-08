# JupyterLab

To support machine learning code development, our users can deploy one or more private JupyterLab applications.

To encourage fair sharing these applications are time limited. We also ask users to request only the resources that they need.

## Limitations

* You can request 1 to 16 CPU cores.
* You can request 1 to 32 GB of memory.
* You can request 0 to 7 GPU instances.
* A notebook can have lifetime of up to 72 hours.
* You can select a GPU model based on its memory size. If you request a GPU, please make sure the GPU is available, by clicking on the icon next to GPU memory.

## Selecting GPU memory and instances

The AF cluster has four NVIDIA A100 GPUs. Each GPU can be partitioned into seven GPU instances. This means the AF cluster can have up to 28 GPU instances running in parallel.

A user can request 0 to 7 GPU instances as a resource for the notebook. A user can request 40,836 MB of memory for an entire A100 GPU, or 4864 MB of memory for a MIG instance.

## Selecting a Docker image

Users can choose from five images:

* `ml_platform:latest` -  Based on NVIDIA image, it has most of the ML packages (Tensorflow, Keras, ScikitLearn,...) preinstalled, and a small tutorial with example codes in /ML_platform_tests/tutorial, it supports NVidia GPUs and has ROOT preinstalled.
* `ml_platform:conda` - comes with full anaconda.
* `ml_platform:julia` - with Julia programming languge
* `ml_platform:lava` - with Intel Lava neuromorphic computing framework
* `ml_platform:centos`
* `AB-stable` - based on AnalysisBase
* `AB-dev` - based on AnalysisBase but with cutting edge uproot, dask, awkward arrays, etc.

For software additions and upgrades please contact <ivukotic@uchicago.edu>.

## Tutorials

Basic usage of the platform can be exerienced by running the set of tutorials that come preinstalled with both __latest__ and __conda__ image.

### Running in conda

To run tutorial in conda environment, one first has to initialize conda. Simply open a jupyter lab terminal, and execute: __conda init__. Close that terminal and open a new one. This will drop you in __(base)__ conda environment. You may now switch to a HEP relevant environment by executing: conda activate __codas-hep__.
