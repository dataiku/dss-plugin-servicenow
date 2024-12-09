import dataiku
from dataiku.customstep import get_plugin_config
from servicenow_client import ServiceNowClient
from dataiku.scenario import Scenario
from servicenow_commons import (
    get_servicenow_incident_status,
    has_no_incident,
)
from safe_logger import SafeLogger
import json
from servicenow_commons import template_dict
import copy


logger = SafeLogger("servicenow plugin", ["password"])

plugin_config = get_plugin_config()
config = plugin_config.get("config", {})

datasets_to_tag = config.get("datasets_to_tag", [])
attach_scenario_variables = config.get("attach_scenario_variables", False)

current_scenario = Scenario()
scenario_variables = current_scenario.get_all_variables()
project_key = scenario_variables.get("projectKey")

client = dataiku.api_client()
project = client.get_project(project_key)

variables_source = copy.deepcopy(scenario_variables)
for dataset_to_tag in datasets_to_tag:
    logger.info("Creating a ServiceNow ticker for dataset {}".format(dataset_to_tag))
    variables_source['dataset'] = dataset_to_tag
    updated_config = template_dict(config, **variables_source)
    dataset = project.get_dataset(dataset_to_tag)
    settings = dataset.get_settings()
    current_status = settings.custom_fields.get("servicenow_incident_status", "")
    if has_no_incident(current_status):
        # No incident ticket on this dataset at this point, let's create one
        logger.warning("Dataset {} current incident state is {}. Creating a new incident.".format(
                dataset_to_tag,
                get_servicenow_incident_status(current_status)
            )
        )
        servicenow_client = ServiceNowClient(config)
        response = servicenow_client.post_incident(
            short_description=updated_config.get("short_description"),
            description=updated_config.get("description"),
            caller_id=updated_config.get("caller_id")
        )
        json_response = response.json()
        result = json_response.get("result", {})
        sys_id = result.get("sys_id", "")
        opened_at = result.get("opened_at")
        state = result.get("state")
        number = result.get("number")
        settings.custom_fields["servicenow_incident_status"] = state
        settings.custom_fields["servicenow_sys_id"] = sys_id
        settings.custom_fields["servicenow_number"] = number
        settings.custom_fields["servicenow_opened_at"] = opened_at
        settings.save()
        if attach_scenario_variables:
            response = servicenow_client.attach_document(
                sys_id,
                "scenario_variables.txt",
                "{}".format(json.dumps(scenario_variables, indent=4))
            )
    else:
        logger.warning(
            "Dataset {} already has an incident opened in state '{}'. Nothing else to do.".format(
                dataset_to_tag,
                get_servicenow_incident_status(current_status)
            )
        )
