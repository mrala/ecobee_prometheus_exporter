FROM python:3-slim

WORKDIR /usr/src/app

COPY . .

RUN python setup.py install
RUN python setup.py install_scripts

CMD [ "ecobee_exporter", "-v" ]
