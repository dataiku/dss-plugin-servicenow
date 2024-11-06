from servicenow_commons import get_user_password_server_from_config
from servicenow_pagination import ServiceNowPagination
from safe_logger import SafeLogger
from api_client import APIClient


MAX_NUMBER_OR_RETRIES = 3


logger = SafeLogger("service-now client", ["password"])


ENDPOINTS_DETAILS = {
    "concoursepicker": {
        "endpoint": "api/now/ui/concoursepicker/application",
        "data_path": ["result", "list"]
    },
    "incident": {
        "endpoint": "api/now/table/incident",
        "data_path": ["result"]
    },
    "change": {
        "endpoint": "api/sn_chg_rest/v1/change",
        "data_path": ["result"]
    },
    "catalogmanagement": {
        "endpoint": "api/sn_sc/v1/servicecatalog/cart",
        "data_path": ["result"]
    },
}
DEFAULT_ENDPOINT_DETAILS = ENDPOINTS_DETAILS.get("incident")


def get_sn_endpoint_details(endpoint_name):
    return ENDPOINTS_DETAILS.get(endpoint_name, DEFAULT_ENDPOINT_DETAILS).get("endpoint"), \
           ENDPOINTS_DETAILS.get(endpoint_name, DEFAULT_ENDPOINT_DETAILS).get("data_path")


class ServiceNowClient():
    def __init__(self, config):
        user, password, server_url = get_user_password_server_from_config(config)
        self.client = APIClient(
            server_url=server_url,
            auth=(user, password),
            pagination=ServiceNowPagination(),
            max_number_of_retries=MAX_NUMBER_OR_RETRIES
        )

    def get_next_row(self, endpoint_name):
        endpoint, data_path = get_sn_endpoint_details(endpoint_name)
        for row in self.client.get_next_row(endpoint, data_path=data_path):
            yield row

    def get_next_incident_row(self):
        for row in self.get_next_row("incident"):
            yield row

    def post_incident(self, short_description=None, description=None, caller_id=None):
        #  https://INSTANCENAME.service-now.com/api/now/table/incident
        logger.info("post_incident:short_description={}, caller_id={}".format(short_description, caller_id))
        response = self.client.post(
            "api/now/table/incident",
            json={
                "short_description": short_description,
                "description": description,
                "caller_id": caller_id
            }
        )
        return response
