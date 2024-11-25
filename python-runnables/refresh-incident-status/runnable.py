# This file is the actual code for the Python runnable refresh-incident-status
import dataiku
from dataiku.runnables import Runnable
from safe_logger import SafeLogger
from servicenow_commons import (
    get_servicenow_incident_status,
)
from servicenow_client import ServiceNowClient


logger = SafeLogger("servicenow plugin", ["password"])


class MyRunnable(Runnable):
    """The base interface for a Python runnable"""

    def __init__(self, project_key, config, plugin_config):
        """
        :param project_key: the project in which the runnable executes
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """
        self.project_key = project_key
        self.config = config
        self.plugin_config = plugin_config

    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Do stuff here. Can return a string or raise an exception.
        The progress_callback is a function expecting 1 value: current progress
        """
        report = []
        client = dataiku.api_client()
        project = client.get_project(self.project_key)
        datasets = project.list_datasets()
        for dataset in datasets:
            comment = None
            dataset_name = dataset.get("name")
            if dataset_name:
                dataset_handle = project.get_dataset(dataset_name)
                settings = dataset_handle.get_settings()
                status = get_servicenow_incident_status(settings.custom_fields.get('servicenow_incident_status'))
                if status != "No incident":
                    logger.info("Dataset {} has an incident currently on status {}".format(dataset_name, status))
                    comment = "Dataset '{}' had a '{}' ticket. ".format(dataset_name, status)
                    servicenow_sys_id = settings.custom_fields.get('servicenow_sys_id')
                    servicenow_client = ServiceNowClient(self.config)
                    incidents = servicenow_client.client.get_next_row(
                        "api/now/v1/table/incident/{}".format(servicenow_sys_id),
                        ["result"]
                    )
                    last_update = None
                    new_status = None
                    for incident in incidents:
                        last_update = incident.get("sys_updated_on")
                        logger.info("updated on {}".format(last_update))
                        new_status = incident.get("state")
                    if new_status:
                        comment += " It has beed updated to '{}'.".format(
                            get_servicenow_incident_status(new_status)
                        )
                        settings.custom_fields['servicenow_incident_status'] = new_status
                        settings.save()
            if comment:
                report.append(comment)
        return "\n".join(report)
