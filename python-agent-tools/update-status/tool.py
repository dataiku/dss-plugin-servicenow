from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServicenowUpdateStatusTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)
        self.status_labels = []
        for row in self.client.get_next_row(
            "sys_choice",
            search_parameters={
                "element": "state",
                "name": "incident"
            }
        ):
            self.status_labels.append(row.get("label"))

    def get_descriptor(self, tool):
        properties = {
            "issue_id": {
                "type": "string",
                "description": "ID of the issue to update"
            },
            "note": {
                "type": "string",
                "description": "The note to add to the issue. Optional"
            }
        }
        if self.status_labels:
            properties["status"] = {
                "type": "string",
                "description": "The status of the issue. It can be one of the following: {}. Optional.".format(
                    ", ".join(self.status_labels)
                )
            }
        descriptor = {
            "description": "This tool can be used to update the status and add a note to Servicenow issues. The input to this tool is a dictionary containing the new status of the issue and / or the note to add to the issue, e.g. '{'status':'In Progress', 'note':'new note content'}'",
            "inputSchema": {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Update Servicenow issue tool",
                "type": "object",
                "properties": properties,
                "required": ["issue_id"]
            }
        }
        return descriptor

    def invoke(self, input, trace):
        logger.info("servicenow update status tool invoked with {}".format(input))
        args = input.get("input", {})

        # Log inputs and config to trace
        trace.span["name"] = "SERVICENOW_UPDATE_ISSUE_TOOL_CALL"
        for key, value in args.items():
            trace.inputs[key] = value
        trace.attributes["config"] = {"servicenow_server_url": self.client.server_url}

        issue_id = args.get("issue_id")
        note = args.get("note")
        status = args.get("status")

        try:
            response = self.client.update_incident(
                issue_id=issue_id,
                note=note,
                status=status,
                can_raise=True
            )
            json_response = response.json()
        except Exception as error:
            logger.error("There was an error '{}' while updating the issue".format(error))
            return {
                "output": "There was a problem while updating the issue ticket: {}".format(error)
            }
        created_issue = json_response.get("result", {})
        output = 'Issue created: {} available at {}'.format(
            created_issue.get("number"),
            self.client.get_issue_url(json_response)
        )
        logger.info("servicenow tool output: {}".format(output))

        # Log outputs to trace
        trace.outputs["output"] = output

        return {
            "output": output
        }
