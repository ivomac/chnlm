FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y \
        python3-tk \
        pkg-config \
        libhdf5-dev \
        gcc \
        iputils-ping \
        curl \
        git \
        libxml-simple-perl \
        libwww-perl \
        libnet-perl \
        build-essential



COPY root-ca.crt /usr/local/share/ca-certificates/root-ca.crt
RUN cat /usr/local/share/ca-certificates/root-ca.crt >> /etc/ssl/certs/ca-certificates.crt
ENV NODE_EXTRA_CA_CERTS /usr/local/share/ca-certificates/root-ca.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN apt-get install apt-utils
RUN apt-get update && apt-get install -y \
    python3-pil \
    python3-tk \
    python3-pil.imagetk
# The bbpappchannelpedia  account is mapped in LDAP and NetApp.
# We need this specific UID/GID in order to read the files
# from the icproject share of nfs4.bbp.epfl.ch with NFS.
RUN  groupadd -g 10067 bbpappchannelpedia
RUN  useradd -u 905684 -g 10067 bbpappchannelpedia 
RUN mkdir /home/bbpappchannelpedia
RUN chown -R bbpappchannelpedia:bbpappchannelpedia /home/bbpappchannelpedia
USER bbpappchannelpedia


# Checkout and install dagster libraries needed to run the gRPC server
# exposing your repository to dagster-webserver and dagster-daemon, and to load the DagsterInstance
# All packages are hard-pinned to `dagster`, so setting the version on just `DAGSTER` will ensure
# compatible versions.


RUN pip install --user --index-url https://bbpteam.epfl.ch/repository/devpi/simple lnmc_api
WORKDIR /opt/dagster/dagster_home

ENV PATH=/home/bbpappchannelpedia/.local/bin:$PATH

# Add repository code
COPY --chown=bbpappchannelpedia /src src/
COPY --chown=bbpappchannelpedia pyproject.toml .
COPY --chown=bbpappchannelpedia README.md .

RUN pip install -e .

RUN sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"
RUN echo "export PATH=/home/bbpappchannelpedia/edirect:\${PATH}" >> ${HOME}/.bashrc

#COPY repo.py /opt/dagster/app

# Run dagster gRPC server on port 4000

# CMD allows this to be overridden from run launchers or executors that want
# to run other commands against your repository
#CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", "-m", "channelome_etl"]
