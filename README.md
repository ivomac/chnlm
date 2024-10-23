# channelome_etl

This is a ETL pipeline based on [Dagster](https://dagster.io/).

## Getting started locally

First, install the required packages in the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

Then, install channelome_etl as a Python package. By using the --editable flag, pip will install your Python package in ["editable mode"](https://pip.pypa.io/en/latest/topics/local-project-installs/#editable-installs) so that as you develop, local code changes will automatically apply.
```bash
pip install -e ".[dev]"
```
Then you need to install [postgresql](https://www.postgresql.org/). And setup a database.

Then you need to fill a .env file using the .env_template (see section [below](#List-of-environment-variable))

Finally, start the Dagster UI web server:

```bash
dagster dev
```

Open http://localhost:3000 with your browser to see the project.

You can start writing assets in `channelome_etl/assets.py`. The assets are automatically loaded into the Dagster code location as you define them.

## Using Docker

With the docker compose file it will create all the necessary container as well as postgres db.
```bash
docker-compose -up
```

## On k8s

.gitlab-ci.yml will automatically create a new image and will push to k8s. (the config of dagster helm chart can be found [here](https://bbpgitlab.epfl.ch/msg/kubernetes/flux-configuration/-/tree/main/dev/channelome-etl?ref_type=heads).)

The dagster webserver is that [url](https://channelome-etl.kcpdev.bbp.epfl.ch/)

For production db:
host: postgresql14-users.bbp.epfl.ch
database: channelome_etl
user: channelome_etl
password: ask Adrien

## List of environment variable

list of environment variable in .env that you can copy from .env_template:

### Postgres DB
- `DAGSTER_PG_DB`: Postgres db name. (both locally and on docker, in k8s it will soon be on EPFL postgres).
- `DAGSTER_PG_USERNAME`: Postgres username. (both locally and on docker, in k8s it will soon be on EPFL postgres).
- `DAGSTER_PG_PASSWORD`: Postgres pwd. (both locally and on docker, in k8s it will soon be on EPFL postgres).
- `DAGSTER_PG_HOST`: Postgres host. locally => `localhost`, docker => `postgresql`

### SYNCROPATCH Data path
- `SYNCROPATCH_RAW_DATA_PATH`: Where new SYNCROPATCH experiment should be placed.
- `SYNCROPATCH_NWB_PATH`: Where nwb file will be saved.
- `SYNCROPATCH_PLOT_PATH`: Where plots will be saved.

### QPC Data path
- `QPC_RAW_DATA_PATH`: Where new QPC experiment should be placed.
- `QPC_NWB_PATH`: Where nwb file will be saved.
- `QPC_GOOGLE_SHEET_PATH` path where google sheet will be saved.
- `QPC_GOOGLE_SHEET_URL`: url of google sheet default to https://docs.google.com/spreadsheets/d/1GREHQVkxEUD7rHG3DB4IzR1om7H5cdOb

### Igor Data path
- `IGOR_RAW_DATA_PATH`: Where new IGOR experiment should be placed.
- `IGOR_NWB_PATH`: Where nwb file will be saved.

### Notification
- `NOTIFICATION`: How channelome_etl notify the user. Either `email` or `slack`.
- `SLACK_CHANNEL`: if slack is chose, in which channel it will sent it. locally,docker => `dagster_dev`, k8s => `dagster` (you can also create a new channel and add the app).
- `SLACK_CHANNEL_HERVE`: if slack is chose, in which channel it will sent QPC and Igor conversion notification. locally,docker => `dagster_dev`, k8s => `herve-notification` (you can also create a new channel and add the app).
- `EMAIL_ADRESS`: if mail is chose, to whome it will sent it. locally,docker => `your_email_adress`, k8s => `bbp.channelpedia@epfl.ch`.
- `SLACK_TOKEN`: Secret token (ask adrien to get it)
- `EMAIL_PWD`: Secret pwd (ask adrien to get it)


### others
- `BASE_URL`: Notification will send the url of the run, It needs then te base_url. locally => `http://127.0.0.1:3000`, locally => `http://localhost:3000`, k8s => `https://channelome-etl.kcpdev.bbp.epfl.ch`.

## How data should be organize per robot


### SYNCROPATCH

- `Raw data`: SYNCROPATCH_RAW_DATA_PATH / year-month-day / exp_name (SYNCROPATCH_RAW_DATA_PATH/240507/240507_001)
- `Nwb`: SYNCROPATCH_NWB_PATH / year-month-day / exp_name / exp_name_cellLine/ exp_name_cellLine_wellId.nwb (SYNCROPATCH_NWB_PATH/240507/240507_001/240507_001_CL1/240507_001_CL1_A1.nwb)
- `Plots`: SYNCROPATCH_PLOT_PATH / year-month-day / year-month-day_exp_id / year-month-day_exp_id_cellline (SYNCROPATCH_PLOT_PATH/240507/240507_001/240507_001_CL1/240507_001_CL1_A1.nwb)

### QPC is an implementation for Herve only (but could be with minor change used for others)

- `Raw data`: QPC_RAW_DATA_PATH / year-month / exp_id (QPC_RAW_DATA_PATH/2024-01/Exp243)
- `Nwb`: QPC_NWB_PATH / exp_id.nwb (QPC_NWB_PATH/Exp243.nwb)

### Igor is an implementation for Herve only (but could be with minor change used for others)

- `Raw data`: IGOR_RAW_DATA_PATH / year / day-month / experimentname.h5xp (IGOR_RAW_DATA_PATH/Year2023/2301/exp0.h5xp)
- `Nwb`: IGOR_NWB_PATH / exp_id//1000 / experimentname_0.nwb (IGOR_NWB_PATH/0/exp0_0.nwb)
