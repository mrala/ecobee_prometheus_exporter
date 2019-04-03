FROM python:3-slim

WORKDIR /usr/src/app

COPY . .

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

RUN python setup.py install
RUN python setup.py install_scripts

CMD [ "ecobee_exporter", "-v" ]
