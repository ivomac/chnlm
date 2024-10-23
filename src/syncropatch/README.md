
## Syncropatch scripts

A python module to convert Syncropatch data to NWB formats, with dagster integration.

See the .env file for the required environment variables/configuration.

## How to use

After installion of the channelome package, the provided scripts will be available in the terminal
as `sync_<script_name>`, as shown below:

For create rcells from one exp:
```bash
$ sync_rcell_create 240507_001 --overwrite
```
For create protocol plots from one exp:
as `sync_<script_name>`, as shown below:
```bash
$ sync_plot_exp 240507_001 --overwrite
```
For create pharma plots from one exp:
as `sync_<script_name>`, as shown below:
```bash
$ sync_plot_pharma_exp 240507_001 --overwrite
```
