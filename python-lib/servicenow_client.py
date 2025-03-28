from servicenow_commons import get_user_password_server_from_config, is_valid_level
from servicenow_pagination import ServiceNowPagination
from safe_logger import SafeLogger
from api_client import APIClient


MAX_NUMBER_OR_RETRIES = 3


logger = SafeLogger("servicenow client", ["password"])


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
    "problem": {
        "endpoint": "api/now/table/problem",
        "data_path": ["result"]
    },
}
DEFAULT_ENDPOINT_DETAILS = ENDPOINTS_DETAILS.get("incident")


def get_sn_endpoint_details(endpoint_name):
    return ENDPOINTS_DETAILS.get(endpoint_name, DEFAULT_ENDPOINT_DETAILS).get("endpoint"), \
           ENDPOINTS_DETAILS.get(endpoint_name, DEFAULT_ENDPOINT_DETAILS).get("data_path")


class ServiceNowClient():
    def __init__(self, config):
        user, password, self.server_url = get_user_password_server_from_config(config)
        self.client = APIClient(
            server_url=self.server_url,
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

    def post_incident(self, short_description=None, description=None, caller_id=None, impact=None, urgency=None, can_raise=False):
        logger.info("post_incident:short_description={}, caller_id={}".format(short_description, caller_id))
        json = {
            "short_description": short_description,
            "description": description,
            "caller_id": caller_id
        }
        if is_valid_level(impact):
            json["impact"] = impact
        if is_valid_level(urgency):
            json["urgency"] = urgency
        response = self.client.post(
            "api/now/table/incident",
            json=json,
            can_raise=can_raise
        )
        return response

    def attach_document(self, sys_id, file_name, data_to_attach):
        response = self.client.post(
            "api/now/attachment/file",
            data=data_to_attach,
            params={
                "table_name": "incident",
                "table_sys_id": sys_id,
                "file_name": file_name
            },
            headers={
                "Content-Type": "text/plain"
            }
        )
        return response

    def get_issue_url(self, response):
        sys_id = response.get("result", response).get("sys_id")
        return "/".join(
            [
                self.server_url,
                "now/nav/ui/classic/params/target/incident.do?sys_id={}".format(
                    sys_id
                )
            ]
        )
