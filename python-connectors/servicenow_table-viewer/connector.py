from dataiku.connector import Connector
from servicenow_client import ServiceNowClient
from servicenow_commons import RecordsLimit
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServiceNowConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info("Starting ServiceNow plugin v0.0.6 with config:{}".format(logger.filter_secrets(config)))
        self.client = ServiceNowClient(config)
        self.endpoint = config.get("endpoint", "incident")

    def get_read_schema(self):
        """
        Returns the schema that this connector generates when returning rows.

        The returned schema may be None if the schema is not known in advance.
        In that case, the dataset schema will be infered from the first rows.

        If you do provide a schema here, all columns defined in the schema
        will always be present in the output (with None value),
        even if you don't provide a value in generate_rows

        The schema must be a dict, with a single key: "columns", containing an array of
        {'name':name, 'type' : type}.

        Example:
            return {"columns" : [ {"name": "col1", "type" : "string"}, {"name" :"col2", "type" : "float"}]}

        Supported types are: string, int, bigint, float, double, date, boolean
        """

        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        for row in self.client.get_next_row(self.endpoint):
            yield only_display_value(row)
            if limit.is_reached():
                break

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        """
        Returns a writer object to write in the dataset (or in a partition).

        The dataset_schema given here will match the the rows given to the writer below.

        Note: the writer is responsible for clearing the partition, if relevant.
        """
        raise NotImplementedError

    def get_partitioning(self):
        """
        Return the partitioning schema that the connector defines.
        """
        raise NotImplementedError

    def list_partitions(self, partitioning):
        """Return the list of partitions for the partitioning scheme
        passed as parameter"""
        return []

    def partition_exists(self, partitioning, partition_id):
        """Return whether the partition passed as parameter exists

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError


class CustomDatasetWriter(object):
    def __init__(self):
        pass

    def write_row(self, row):
        """
        Row is a tuple with N + 1 elements matching the schema passed to get_writer.
        The last element is a dict of columns not found in the schema
        """
        raise NotImplementedError

    def close(self):
        pass


def only_display_value(row):
    output_row = {}
    for key in row:
        raw_value = row.get(key)
        if isinstance(raw_value, dict):
            if "display_value" in raw_value:
                output_row[key] = raw_value.get("display_value")
            else:
                output_row[key] = raw_value
        else:
            output_row[key] = raw_value
    return output_row
