## Ecobee Prometheus Exporter

### Requirements
You will need a developer account from ecobee and need to generate an API key. [Follow the documentation](https://ecobee.atlassian.net/wiki/spaces/APIFAQ/pages/272204398/How+do+I+create+ecobee+applications+or+get+an+API+key+so+I+can+start+using+the+ecobee+API) from ecobee to create an account and generate an API key. Create an app and use the ecobee PIN authorization method.

### Install

Install `ecobee_exporter` script:
```
> python setup.py install_scripts
>
```

### Usage
```
> ecobee_exporter --api_key [your_api_key] --port [optional_port] --bind_address [optional_bind_address]
```
At first run, you will see a message to authorize the app with a PIN at https://www.ecobee.com/consumer/portal/index.html. The app will wait for 60 seconds for authorization. By default, this will begin serving metrics at http://localhost:9756

### Credits
Based on [ecobee_exporter by sbrudenell](https://github.com/sbrudenell/ecobee_exporter/).
