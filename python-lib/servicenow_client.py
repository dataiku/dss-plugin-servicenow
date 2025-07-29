import datetime
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
    "caller_id": {
        "endpoint": "api/now/table/sys_user",
        "data_path": ["result"]
    },
    "sys_db_object": {
        "endpoint": "api/now/table/sys_db_object",
        "data_path": ["result"]
    },
    "sys_app_category": {
        "endpoint": "api/now/table/sys_app_category",
        "data_path": ["result"]
    },
    "catalog_category_request": {
        "endpoint": "api/now/table/catalog_category_request",
        "data_path": ["result"]
    },
}
DEFAULT_ENDPOINT_DETAILS = ENDPOINTS_DETAILS.get("incident")


def get_sn_endpoint_details(endpoint_name):
    endpoint_details = ENDPOINTS_DETAILS.get(endpoint_name)
    if endpoint_details:
        return endpoint_details.get("endpoint"), endpoint_details.get("data_path")
    else:
        return "api/now/table/{}".format(endpoint_name), ["result"]


class ServiceNowClient():
    def __init__(self, config):
        user, password, self.server_url = get_user_password_server_from_config(config)
        self.client = APIClient(
            server_url=self.server_url,
            auth=(user, password),
            pagination=ServiceNowPagination(),
            max_number_of_retries=MAX_NUMBER_OR_RETRIES
        )

    def get_next_row(self, endpoint_name, search_parameters=None):
        endpoint, data_path = get_sn_endpoint_details(endpoint_name)
        params = sys_parm_search_params(search_parameters)
        for row in self.client.get_next_row(endpoint, data_path=data_path, params=params):
            yield row

    def get_next_incident_row(self):
        for row in self.get_next_row("incident"):
            yield row

    def post_incident(self, short_description=None, description=None,
                      caller_id=None, impact=None, urgency=None, category=None, can_raise=False):
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
        if category:
            json["category"] = category
        response = self.client.post(
            "api/now/table/incident",
            json=json,
            can_raise=can_raise
        )
        return response

    def update_incident(self, issue_id=None, note=None, status=None, can_raise=False):
        logger.info("update_incident:issue_id={}, note={}, status={}".format(issue_id, note, status))
        json = {}
        if status:
            json["state"] = status
        if note:
            response = self.client.get("api/now/table/incident/{}".format(issue_id))
            work_notes = response.get("work_notes", "")
            json["work_notes"] = redact_note(work_notes, note)
        response = self.client.put(
            "api/now/table/incident/{}".format(issue_id),
            json=json,
            can_raise=can_raise
        )
        return response

    def lookup_user(self, user_name=None, sys_id=None, name=None, email=None):
        # user_name: john.doe
        # name: John Doe
        users = []
        if sys_id:
            param = "sys_id={}".format(sys_id)
        elif email:
            param = "email={}".format(email)
        elif user_name:
            param = "user_name={}".format(user_name)
        elif name:
            param = "name={}".format(name)
        else:
            return
        endpoint, data_path = get_sn_endpoint_details("sys_user")
        for row in self.client.get_next_row("{}?sysparm_query={}".format(endpoint, param), data_path=["result"]):
            user = {
                "email": row.get("email"),
                "user_name": row.get("user_name"),
                "sys_id": row.get("sys_id"),
                "name": row.get("name"),
            }
            users.append(user)
        return users

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


def sys_parm_search_params(search_parameters):
    params = {}
    if not search_parameters:
        return params
    search_items = []
    for search_parameter in search_parameters:
        search_items.append("{}={}".format(
            search_parameter,
            search_parameters.get(search_parameter)
        ))
    params["sysparm_query"] = "^".join(search_items)
    return params


def redact_note(previous_note, new_note):
    # 2025-06-11 02:59:12 - System Administrator (Work notes)\nsecond note\n\n2025-06-11 02:58:57 - System Administrator (Work notes)\nAdding a note\n\n
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d %H:%M:%S")
    return "{} - System Administrator (Work notes)\n{}\n\n{}".format(date, new_note, previous_note)
