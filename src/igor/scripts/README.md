# Igor to rCell Conversion

#### A python module to convert Igor data to H5/NWB formats

## How to use

The module can be run as a standalone script as:

`python -m /path/to/igor_folder <script_name>`

After installation of the channelome package, it can also be run from anywhere in the (virtual) environment as:

`igor <script_name>`

as shown below. For example, we can check if a job ID has raw/meta data issues:

For create rcells from one exp:
```bash
$ igor rcell_create HA240701_A_1.h5xp --overwrite
```