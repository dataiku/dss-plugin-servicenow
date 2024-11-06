from safe_logger import SafeLogger


logger = SafeLogger("servicenow pagination", ["password"])
DEFAULT_PAGE_SIZE = 10000


class ServiceNowPagination():
    def __init__(self, batch_size=None):
        self.batch_size = batch_size or DEFAULT_PAGE_SIZE
        self.number_of_tries = None
        self.page_offset = None

    def has_next_page(self, response, items_retrieved):
        if response is None:
            logger.info("ServiceNowPagination:has_next_page:initialisation")
            self.page_offset = 0
            return True
        self.page_offset += self.batch_size
        if items_retrieved < self.batch_size:
            logger.info("ServiceNowPagination:has_next_page:retrieved {} on this run, stopping".format(items_retrieved))
            return False
        logger.info("ServiceNowPaginationhas_next_page:retrieved {} on this run, carrying on".format(items_retrieved))
        return True

    def get_paging_parameters(self):
        logger.info("ServiceNowPagination:get_paging_parameters")
        headers = {
            "sysparm_limit": self.batch_size,
            "sysparm_offset": self.page_offset,
            "sysparm_query": "ORDERBYDESCsys_created_on"
        }
        return headers
