import requests
from safe_logger import SafeLogger


logger = SafeLogger("api-client")


class APIClient():
    def __init__(self, server_url, auth, pagination=None, max_number_of_retries=None, should_fail_silently=False):
        self.session = requests.Session()
        self.server_url = server_url
        self.session.auth = auth
        self.number_of_retries = None
        self.page_offset = None
        self.pagination = pagination or DefaultPagination()
        self.max_number_of_retries = max_number_of_retries or 1
        self.should_fail_silently = should_fail_silently

    def get(self, endpoint, params=None):
        full_url = self.get_full_url(endpoint)
        response = None
        while self.should_try_again(response):
            try:
                logger.info("geting url={}, params={}".format(full_url, params))
                response = self.session.get(full_url, params=params)
            except Exception as error:
                error_message = "Error on get: {}".format(error)
                logger.error(error_message)
                self.raise_if_necessary(error_message)
        display_response_error(response)
        json_response = response.json()
        return json_response

    def post(self, endpoint, params=None, json=None, data=None, headers=None, files=None, can_raise=False):
        full_url = self.get_full_url(endpoint)
        response = self.session.post(
            full_url,
            headers=headers,
            params=params,
            json=json,
            data=data,
            files=files
        )
        display_response_error(response, can_raise=can_raise)
        return response

    def get_full_url(self, endpoint):
        full_url = "{}/{}".format(self.server_url, endpoint)
        return full_url

    def get_next_row(self, endpoint, data_path=None):
        response = None
        items_retrieved = 0
        while self.pagination.has_next_page(response, items_retrieved):
            response = self.get(endpoint, params=self.pagination.get_paging_parameters())
            items_retrieved = 0
            for row in get_next_row_from_response(response, data_path):
                items_retrieved += 1
                yield row

    def should_try_again(self, response):
        if response is not None:
            self.number_of_retries = None
            return False
        if self.number_of_retries is None:
            logger.warning("Retrying")
            self.number_of_retries = 1
        else:
            logger.warning("Retry {}".format(self.number_of_retries))
            self.number_of_retries += 1
        if self.number_of_retries > self.max_number_of_retries:
            self.number_of_retries = None
            logger.error("Max number of retries")
            return False
        return True

    def raise_if_necessary(self, error_message):
        if self.should_fail_silently:
            return
        else:
            if self.max_number_of_retries == self.max_number_of_retries:
                raise Exception(error_message)
            else:
                return


def get_next_row_from_response(response, data_path=None):
    if not data_path:
        return response
    data = []
    if isinstance(data_path, str):
        data = response.get(data_path)
    elif isinstance(data_path, list):
        data = response
        for data_path_token in data_path:
            data = data.get(data_path_token, {})
    else:
        raise Exception("get_next_row_from_response: data_path can only be string or list")
    if isinstance(data, list):
        for row in data:
            yield row
    else:
        yield data


class DefaultPagination():
    def __init__(self):
        # No pagination, just stops after the first page
        logger.info("Single page pagination used")
        pass

    def has_next_page(self, response, items_retrieved):
        logger.info("DefaultPagination:has_next_page")
        if response is None:
            logger.info("DefaultPagination:has_next_page initialisation")
            return True
        logger.info("DefaultPagination:has_next_page Stop here")
        return False

    def get_paging_parameters(self):
        logger.info("DefaultPagination:get_paging_parameters")
        return None


def display_response_error(response, can_raise=False):
    if response is None:
        logger.error("Empty response")
    elif isinstance(response, requests.Response):
        status_code = response.status_code
        logger.info("status_code={}".format(status_code))
        if status_code >= 400:
            logger.error("Error {}. Dumping response:{}".format(status_code, response.content))
            if can_raise:
                raise Exception("Error {}".format(response.status_code))
    else:
        logger.error("Not a requests.Response object")
