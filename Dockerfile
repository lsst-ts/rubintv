# This Dockerfile is used to build the Rubintv on a commit basis.
# The GH action will build the image and push it to the registry.
# The image will be used to deploy the application on dev servers.
# Note:
# I was not able to use the conda recipe to build the image,
# faced several issues which at the end I was not able to resolve
# and decided to use the python image instead.
# This is a temporary solution, and I will work on a better approach
# to build the image using conda.
# TODO: DM-43222.

FROM python:3.11.1-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

USER root

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    libsasl2-dev \
    python-dev \
    libldap2-dev \
    inetutils-ping \
    vim \
    nano \
    procps \
    findutils \
    libssl-dev \
    # below installs are for Flutter 
    git curl unzip xz-utils zip libglu1-mesa && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/rubintv/
COPY . .

# Install dependencies
RUN pip install -r requirements.txt && \
    python setup.py install

# download Flutter SDK from Flutter Github repo
RUN git clone https://github.com/flutter/flutter.git /usr/local/flutter

# Set flutter environment path
ENV PATH="/usr/local/flutter/bin:/usr/local/flutter/bin/cache/dart-sdk/bin:${PATH}"

# Run flutter doctor
RUN flutter doctor

# Enable flutter web
RUN flutter channel master
RUN flutter upgrade

# Download rubin_chart
RUN git clone --single-branch --branch deploy_slac https://github.com/lsst-sitcom/rubin_chart

# Download rubin_visualization
RUN git clone --single-branch --branch deploy_slac https://github.com/lsst-ts/rubin_visualization \
    /usr/local/rubintv/ddv

RUN 
# Adjust permissions for executable
RUN chmod +x /usr/src/rubintv/start-daemon.sh

# Expose the port.
EXPOSE 8000

CMD ["/usr/src/rubintv/start-daemon.sh"]
