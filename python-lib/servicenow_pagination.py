import requests
from servicenow_safe_logger import SafeLogger


logger = SafeLogger("servicenow pagination", ["password", "client_secret", "access_token"])
DEFAULT_PAGE_SIZE = 10000


class ServiceNowPagination():
    def __init__(self, batch_size=None):
        self.batch_size = batch_size or DEFAULT_PAGE_SIZE
        self.number_of_tries = None
        self.page_offset = None

    def get_paging_parameters(self, params=None):
        logger.info("ServiceNowPagination:get_paging_parameters")
        headers = {
            "sysparm_limit": self.batch_size,
            "sysparm_offset": self.page_offset,
            "sysparm_query": "ORDERBYDESCsys_created_on"
        }
        if params:
            headers.update(params)
        return headers

    def get_next_url_from_response(self, response):
        next_url = None
        if isinstance(response, requests.Response):
            next_url = response.links.get("next")
            if isinstance(next_url, dict):
                next_url = next_url.get("url")
        return next_url
