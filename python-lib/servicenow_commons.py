import requests
from functools import partial
from threading import Lock
from time import monotonic
from servicenow_safe_logger import SafeLogger
from urllib.parse import urlparse

logger = SafeLogger("servicenow plugin", ["password", "client_secret"])


def get_server_from_config(config):
    auth_type = config.get("auth_type", "basic_per_user")
    credentials = config.get(auth_type, {})
    server_url = server_url_normalization(credentials.get("server_url", ""))
    return server_url


def get_auth_from_config(config):
    auth_type = config.get("auth_type", "basic_per_user")
    credentials = config.get(auth_type, {})
    if auth_type == "basic_per_user":
        basic_per_user = credentials.get("basic_per_user")
        return (basic_per_user.get("user", ""), basic_per_user.get("password", ""))
    elif auth_type == "oauth_service_account":
        return BearerTokenAuth(
            token_provider=partial(
                get_access_token_from_service_account,
                credentials.get("server_url", ""),
                credentials.get("client_id"),
                credentials.get("client_secret")
            )
        )
    elif auth_type == "oauth_password_grant":
        basic_per_user = credentials.get("basic_per_user", {})
        if not basic_per_user:
            raise Exception("The username / password is not set for this preset x Dataiku user")
        return BearerTokenAuth(
            token_provider=partial(
                get_access_token_from_password_grant,
                credentials.get("server_url", ""),
                credentials.get("client_id"),
                credentials.get("client_secret"),
                basic_per_user.get("user", ""),
                basic_per_user.get("password", "")
            ),
            token_refresher=partial(
                get_access_token_from_refresh_token,
                credentials.get("server_url", ""),
                credentials.get("client_id"),
                credentials.get("client_secret")
            )
        )
    else:
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        if client_id and client_secret:
            return BearerTokenAuth(
                token_provider=partial(
                    get_access_token_from_password_grant,
                    credentials.get("server_url", ""),
                    credentials.get("client_id"),
                    credentials.get("client_secret"),
                    credentials.get("user", ""),
                    credentials.get("password", "")
                ),
                token_refresher=partial(
                    get_access_token_from_refresh_token,
                    credentials.get("server_url", ""),
                    credentials.get("client_id"),
                    credentials.get("client_secret")
                )
            )
        else:
            return (credentials.get("user", ""), credentials.get("password", ""))


def server_url_normalization(raw_server_url):
    if not raw_server_url:
        raise Exception("The server URL is empty")
    server_url = raw_server_url
    if not server_url.startswith("http"):
        server_url = "https://{}".format(server_url)
    parsed_url = urlparse(server_url)
    server_url = parsed_url.scheme + "://" + parsed_url.netloc
    return server_url


def get_failed_steps(scenario_variables):
    failed_steps = []
    if isinstance(scenario_variables, dict):
        for key in scenario_variables:
            if key.startswith("stepOutcome_"):
                value = scenario_variables.get(key)
                if value == "FAILED":
                    step_name = key.split("stepOutcome_")[1]
                    failed_steps.append(step_name)
    return failed_steps


def get_failed_steps_outputs(scenario_variables):
    failed_steps = get_failed_steps(scenario_variables)
    # ['noken']
    failed_steps_outputs = {}
    for step in scenario_variables:
        if step.startswith("stepOutput_"):
            step_name = step.split("stepOutput_")[1]
            if step_name in failed_steps:
                failed_steps_outputs[step_name] = scenario_variables.get(step)
    return failed_steps_outputs


def get_step_results(scenario_variables, failed_steps_names):
    step_ids = []
    if "stepResults" in scenario_variables:
        step_results = scenario_variables.get("stepResults", {})
        for failed_step_name in failed_steps_names:
            failed_step = step_results.get(failed_step_name, {})
            target = failed_step.get("target", {})
            step_id = target.get("stepId", "")
            step_ids.append(step_id)
    return step_ids


def extract_faulty_datasets_from_failed_steps(failed_steps):
    faulty_datasets = []
    for failed_step_name in failed_steps:
        failed_step = failed_steps.get(failed_step_name)
        faulty_datasets += extract_faulty_datasets_from_failed_step(failed_step)
    return faulty_datasets


def extract_faulty_datasets_from_failed_step(failed_step):
    faulty_datasets = []
    for dataset_full_name in failed_step:
        failed_step_definition = failed_step.get(dataset_full_name)
        partition = failed_step_definition.get("partition")
        dataset_name = dataset_full_name.split(".")[1]
        dataset_name = dataset_name.split("_{}".format(partition))[0]
        results = failed_step_definition.get("results", [])
        dataset_is_faulty = False
        for result in results:
            value = result.get("value", {})
            outcome = value.get("outcome")
            if outcome in ["WARNING", "FAILED"]:
                dataset_is_faulty = True
        if dataset_is_faulty:
            faulty_datasets.append(dataset_name)
    return faulty_datasets


def get_servicenow_incident_status(incident_level):
    incident_levels = {
        None: "No incident", "": "No incident", "None": "No incident",
        "1": "New", "2": "Assigned", "12": "Referred", "4": "Awaiting User Info",
        "5": "Awaiting Evidence", "10": "Awaiting Change", "8": "Awaiting Vendor", "11": "Awaiting Vendor Change", "6": "Resolved", "7": "Closed"
    }
    return incident_levels.get(incident_level, "Unknown")


def has_no_incident(current_status):
    if current_status in [None, "None", "", "6", "7"]:
        return True
    return False


class RecordsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self):
        if self.has_no_limit:
            return False
        self.counter += 1
        return self.counter > self.records_limit


def template_dict(dictionnary, **kwargs):
    """ Recurses into dictionnary and replace template {{keys}} with the matching values present in the kwargs dictionnary"""
    ret = dict.copy(dictionnary)
    for key in ret:
        if isinstance(ret[key], dict):
            ret[key] = template_dict(ret[key], **kwargs)
        if is_string(ret[key]):
            ret[key] = format_template(ret[key], **kwargs)
    return ret


def format_template(template, **kwargs):
    """ Replace {{keys}} elements in template with the matching value in the kwargs dictionnary"""
    if template is None:
        return None
    formated = template
    for key in kwargs:
        replacement = kwargs.get(key, "")
        formated = formated.replace("{{{{{}}}}}".format(key), str(replacement))
    return formated


def is_string(data):
    data_type = type(data).__name__
    return data_type in ["str", "unicode"]


def is_valid_level(string_level):
    # Check that:
    # - Not None
    # - Valid int
    # - Value between 1-3
    if string_level:
        if isinstance(string_level, str) and not string_level.isdigit():
            return False
        try:
            level = int(string_level)
            if 0 < level < 4:
                return True
        except Exception as error:
            logger.error("Could not convert level '{}' into int: {}".format(string_level, error))
    return False


def get_parameters_from_config(config):
    endpoint = config.get("endpoint", "incident")
    if endpoint == "_dku_manual_setting":
        endpoint = config.get("table_name", "incident")
    display_values = config.get("display_values", False)  # True for new dataset, false for existing ones
    sysparm_query = None
    sysparm_fields = None
    if config.get("advanced_parameters", False) is True:
        sysparm_query = config.get("sysparm_query")
        sysparm_fields = config.get("sysparm_fields")
    return endpoint, display_values, sysparm_query, sysparm_fields


def get_batch_size_from_config(config):
    batch_size = None
    if config.get("advanced_parameters", False) is True:
        batch_size = config.get("page_size", None)
    return batch_size


def get_access_token_from_service_account(server_url, client_id, client_secret):
    return request_access_token(server_url, {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
    )


def get_access_token_from_password_grant(server_url, client_id, client_secret, username, password):
    return request_access_token(server_url, {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password
    })


def get_access_token_from_refresh_token(server_url, client_id, client_secret, refresh_token):
    return request_access_token(server_url, {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    })


def request_access_token(server_url, data):
    server_url = server_url_normalization(server_url)
    token_url = "/".join([server_url, "oauth_token.do"])
    response = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data
    )
    if response.status_code >= 400:
        logger.error("Error while retrieving access token: {}".format(response.content))
        raise Exception("Error {}, could not retrieve the access token".format(response.status_code))
    json_response = response.json()
    assert_no_error(json_response)
    access_token = json_response.get("access_token")
    expires_in = json_response.get("expires_in")
    refresh_token = json_response.get("refresh_token")
    return access_token, expires_in, refresh_token


def assert_no_error(json_response):
    if "error" in json_response:
        raise Exception("Error while login in: {} {}".format(json_response.get("error_description", ""), json_response.get("error", "")))


class BearerTokenAuth(requests.auth.AuthBase):
    MAX_REFRESH_MARGIN_SECONDS = 60
    REFRESH_MARGIN_RATIO = 0.1

    def __init__(self, access_token=None, token_provider=None, token_refresher=None):
        self.access_token = access_token
        self.token_provider = token_provider
        self.token_refresher = token_refresher
        self.refresh_token = None
        self.refresh_at = None
        self.lock = Lock()
        if self.token_provider is not None:
            self.refresh_access_token()

    def refresh_access_token(self):
        requested_at = monotonic()
        if self.refresh_token and self.token_refresher is not None:
            access_token, expires_in, refresh_token = self.token_refresher(self.refresh_token)
        else:
            access_token, expires_in, refresh_token = self.token_provider()
        refresh_at = None
        if expires_in is not None:
            lifetime = float(expires_in)
            refresh_margin = min(self.MAX_REFRESH_MARGIN_SECONDS, lifetime * self.REFRESH_MARGIN_RATIO)
            refresh_at = requested_at + lifetime - refresh_margin
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        self.refresh_at = refresh_at

    def __call__(self, request):
        with self.lock:
            if self.token_provider is not None and self.refresh_at is not None and monotonic() >= self.refresh_at:
                self.refresh_access_token()
            request.headers["Authorization"] = "Bearer {}".format(
                self.access_token
            )
        return request
