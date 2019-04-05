"""Export Ecobee metrics for Prometheus."""
import logging
import re
import shelve
from datetime import datetime
from time import sleep

import pytz

from prometheus_client import Gauge # type: ignore
from pyecobee import * # type: ignore

class EcobeeAuth():
    """Authorize Ecobee token."""
    def __init__(self, ecobee_service, auth_file):
        self.auth_file = auth_file
        self.ecobee_service = ecobee_service
        self.thermostat_name = "thermostat"
        self.metrics = []
        self._log = logging.getLogger(__name__)

    def persist_to_shelf(self, file_name):
        """Store token data."""
        pyecobee_db = shelve.open(file_name, writeback=True)
        pyecobee_db[self.thermostat_name] = self.ecobee_service
        self._log.debug(pyecobee_db[self.thermostat_name].access_token)
        pyecobee_db.close()

    def refresh_tokens(self):
        """Refresh tokens."""
        token_response = self.ecobee_service.refresh_tokens()
        self._log.debug("TokenResponse returned from "
                        "ecobee_service.refresh_tokens():"
                        "\n%s", token_response.pretty_format())
        self.persist_to_shelf(self.auth_file)

    def request_tokens(self):
        """Request tokens."""
        token_response = self.ecobee_service.request_tokens()
        self._log.debug("TokenResponse returned from "
                        "ecobee_service.request_tokens():"
                        "\n%s", token_response.pretty_format())
        self.persist_to_shelf(self.auth_file)

    def authorize(self):
        """Get authorization token."""
        authorize_response = self.ecobee_service.authorize()
        self._log.debug("AutorizeResponse returned from "
                        "ecobee_service.authorize():"
                        "\n%s", authorize_response.pretty_format())
        self.persist_to_shelf(self.auth_file)
        self._log.info("Please authorize this app at https://www.ecobee.com/"
                       "consumer/portal/index.html with pin code:\n%s\n",
                       authorize_response.ecobee_pin)
        sleep(60)

    def check_token(self):
        """Is this token valid?"""
        if not self.ecobee_service.authorization_token:
            self.authorize()

        if not self.ecobee_service.access_token:
            self.request_tokens()

        now_utc = datetime.now(pytz.utc)
        self._log.debug("Current UTC time: %s\n", now_utc)
        self._log.debug("Access Token expires: %s\n", self.ecobee_service.access_token_expires_on)
        self._log.debug("Refresh Token expires: %s\n", self.ecobee_service.refresh_token_expires_on)

        self._log.debug("Authorization Token: %s\n", self.ecobee_service.authorization_token)
        self._log.debug("Access Token: %s", self.ecobee_service.access_token)
        self._log.debug("Refresh Token: %s", self.ecobee_service.refresh_token)

        if now_utc > self.ecobee_service.refresh_token_expires_on:
            self._log.debug("REFRESH TOKEN EXPIRED, AUTHORIZE AND REQUEST TOKENS")
            self.authorize()
            self.request_tokens()
        elif now_utc > self.ecobee_service.access_token_expires_on:
            self._log.debug("ACCESS TOKEN EXPIRED, REFRESHING TOKENS")
            self.refresh_tokens()


class EcobeeCollector(): # pylint: disable=too-few-public-methods
    """Collect and format metrics from Ecobee."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, api_key, auth_file):
        self.api_key = api_key
        self.auth_file = auth_file
        self.metrics = []
        self.thermostat_name = "thermostat"
        self.summary_selection = Selection(
            selection_type=SelectionType.REGISTERED.value,
            selection_match="",
            include_equipment_status=True)
        # self.metrics = []
        self._prefix = "ecobee_"
        self._log = logging.getLogger(__name__)
        self.init_metrics()

    def init_metrics(self):
        """Initialize metric objects."""
        namespace = "ecobee"
        sensor_labels = ["thermostat_name", "sensor_name"]
        runtime_labels = ["thermostat_name", "type"]

        self.metric_temperature_actual = Gauge(
            name="temperature_actual",
            documentation="Actual temperature",
            labelnames=sensor_labels,
            namespace=namespace
        )

        self.metric_humidity = Gauge(
            name="humidity",
            documentation="Humidity",
            labelnames=sensor_labels,
            namespace=namespace
        )

        self.metric_occupancy = Gauge(
            name="occupancy",
            documentation="Detected occupancy",
            labelnames=sensor_labels,
            namespace=namespace
        )

        self.metric_desired_cool_range = Gauge(
            name="desired_cool_range",
            documentation="Desired cool range",
            labelnames=runtime_labels,
            namespace=namespace
        )

        self.metric_desired_heat_range = Gauge(
            name="desired_heat_range",
            documentation="Desired heat range",
            labelnames=runtime_labels,
            namespace=namespace
        )

        self.heat_status = Gauge(
            name="heat_status",
            documentation="Indicates whether HVAC system is actively heating",
            labelnames=runtime_labels,
            namespace=namespace
        )

        self.cool_status = Gauge(
            name="cool_status",
            documentation="Indicates whether HVAC system is actively cooling",
            labelnames=runtime_labels,
            namespace=namespace
        )

        self.fan_status = Gauge(
            name="fan_status",
            documentation="Indicates whether HVAC system is running the fan",
            labelnames=runtime_labels,
            namespace=namespace
        )

    @staticmethod
    def convert_string(string_value):
        """Convert a string value to bool."""
        if string_value.lower() == "true":
            return True
        if string_value.lower() == "false":
            return False
        return string_value

    def running_equipment(self, thermostat):
        """Gather running equipment."""
        for equipment in thermostat.equipment_status.split(","):
            self.fan_status.labels(
                thermostat_name=thermostat.name,
                type="fan").set(1 if re.search("fan", equipment, re.IGNORECASE) else 0)
            self.heat_status.labels(
                thermostat_name=thermostat.name,
                type="heat").set(1 if re.search("heat", equipment, re.IGNORECASE) else 0)
            self.cool_status.labels(
                thermostat_name=thermostat.name,
                type="cool").set(1 if re.search("cool", equipment, re.IGNORECASE) else 0)

    def runtime_data(self, thermostat):
        """Gather runtime data."""
        cool_range = {}
        cool_range["low"], cool_range["high"] = thermostat.runtime.__getattribute__(
            "desired_cool_range")

        heat_range = {}
        heat_range["low"], heat_range["high"] = thermostat.runtime.__getattribute__(
            "desired_heat_range")

        for range_type in ["low", "high"]:
            self.metric_desired_cool_range.labels(
                thermostat_name=thermostat.name,
                type=range_type).set(cool_range[range_type] / 10.0)
            self.metric_desired_heat_range.labels(
                thermostat_name=thermostat.name,
                type=range_type).set(heat_range[range_type] / 10.0)

    def sensor_data(self, thermostat):
        """Gather sensor data."""
        for sensor in thermostat.remote_sensors:
            self._log.debug(sensor)
            for capability in sensor.capability:
                if capability.type == "temperature":
                    self.metric_temperature_actual.labels(
                        thermostat_name=thermostat.name,
                        sensor_name=sensor.name).set(
                            float(capability.value) / 10.0)
                if capability.type == "humidity":
                    self.metric_humidity.labels(
                        thermostat_name=thermostat.name,
                        sensor_name=sensor.name).set(
                            float(capability.value))
                if capability.type == "occupancy":
                    self.metric_occupancy.labels(
                        thermostat_name=thermostat.name,
                        sensor_name=sensor.name).set(
                            float(self.convert_string(capability.value)))

    def settings_data(self, thermostat, thermostat_id):
        """Gather settings data."""
        raise NotImplementedError
    #     for setting, value_type in thermostat.settings.attribute_type_map.items():
    #         labels = dict(thermostat_id)
    #         try:
    #             value = float(thermostat.settings.__getattribute__(setting))
    #         except ValueError:
    #             pass
    #         if value_type == "six.text_type":
    #             labels["value"] = setting
    #             value = 1.0
    #         elif value_type == "bool":
    #             labels["value"] = setting
    #             value = float(thermostat.settings.__getattribute__(setting))

    #         self._log.debug("gathering setting %s = %r",
    #                         setting,
    #                         thermostat.settings.__getattribute__(setting))
    #         self.metrics.append(make_metric(
    #             self._prefix + "setting_" + setting,
    #             "Ecobee Settings",
    #             value,
    #             **labels))


    def collect(self):
        """Collect metrics."""
        try:
            pyecobee_db = shelve.open(self.auth_file, writeback=True)
            ecobee_service = pyecobee_db[self.thermostat_name]
        except KeyError:
            ecobee_service = EcobeeService(
                thermostat_name=self.thermostat_name,
                application_key=self.api_key)
        finally:
            pyecobee_db.close()

        ecobee_auth = EcobeeAuth(ecobee_service=ecobee_service,
                                 auth_file=self.auth_file)
        ecobee_auth.check_token()

        thermostat_summary_response = ecobee_service.request_thermostats_summary(
            self.summary_selection)
        self._log.debug("Response from "
                        "ecobee_service.request_thermostats_summary:\n%s",
                        thermostat_summary_response.pretty_format())

        thermostat_ids = [i.replace(":", "") for i in thermostat_summary_response.status_list]
        self._log.debug("Found thermostat(s):\n%s", thermostat_ids)

        for thermostat_id in thermostat_ids:
            assert thermostat_id.isdigit(), "Invalid thermostat ID."
            thermostat_response = ecobee_service.request_thermostats(
                selection=Selection(
                    selection_type="thermostats",
                    selection_match=thermostat_id,
                    include_equipment_status=True,
                    include_runtime=True,
                    include_sensors=True,
                    include_weather=True))
            self._log.debug("Response from "
                            "ecobee_service.request_thermostats:\n%s",
                            thermostat_response)

            for thermostat in thermostat_response.thermostat_list:
                self._log.debug("Gathering data for thermostat:\n%s",
                                thermostat.name)
                thermostat_id = {
                    "thermostat_id": thermostat.identifier,
                    "thermostat_name": thermostat.name
                }
                try:
                    self.running_equipment(thermostat)
                    self.runtime_data(thermostat)
                    self.sensor_data(thermostat)
                    # self.settings_data(thermostat, thermostat_id)
                except (AttributeError, ValueError) as error:
                    self._log.error("ERROR: %s", error)
        return self.metrics
