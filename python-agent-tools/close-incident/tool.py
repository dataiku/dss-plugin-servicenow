from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient, is_sys_id
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServicenowCloseIncidentTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)
        self.status_labels = []
        self.close_codes = []
        for row in self.client.get_next_row(
            "sys_choice",
            search_parameters={
                "element": "state",
                "name": "incident"
            }
        ):
            self.status_labels.append(row.get("label"))
        for row in self.client.get_next_row(
            "sys_choice",
            search_parameters={
                "element": "close_code",
                "name": "incident"
            }
        ):
            self.close_codes.append(row.get("label"))

    def get_descriptor(self, tool):
        properties = {
            "sys_id": {
                "type": "string",
                "description": "The sys_id of the issue to update. sys_id are 32 hexadecimal strings. Other ID types will first require to use the incident lookup tool to find the corresponding sys_id."
            },
            "close_notes": {
                "type": "string",
                "description": "The closing comment explaining how the incident was solved."
            },
            "comments": {
                "type": "string",
                "description": ""
            }
        }
        if self.status_labels:
            properties["status"] = {
                "type": "string",
                "description": "The status of the issue. It can be one of the following: {}. Optional.".format(
                    ", ".join(self.status_labels)
                )
            }
        if self.close_codes:
            properties["close_code"] = {
                "type": "string",
                "description": "The closing code of the issue. It can be one of the following: {}.".format(
                    ", ".join(self.close_codes)
                )
            }
        descriptor = {
            "description": "This tool can be used to update the status and add a note to Servicenow issues. The input to this tool is a dictionary containing the new status of the issue and / or the note to add to the issue, e.g. '{'status':'In Progress', 'note':'new note content'}'",
            "inputSchema": {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Update Servicenow issue tool",
                "type": "object",
                "properties": properties,
                "required": ["sys_id"]
            }
        }
        return descriptor

    def load_sample_query(self, tool):
        return {
            "sys_id": "The sys_id of the issue to update. sys_id are 32 hexadecimal strings. Other ID types will first require to use the incident lookup tool to find the corresponding sys_id."
        }
    
    def invoke(self, input, trace):
        logger.info("servicenow close incident tool invoked with {}".format(input))
        args = input.get("input", {})

        # Log inputs and config to trace
        trace.span["name"] = "SERVICENOW_CLOSE_ISSUE_TOOL_CALL"
        for key, value in args.items():
            trace.inputs[key] = value
        trace.attributes["config"] = {"servicenow_server_url": self.client.server_url}

        sys_id = args.get("sys_id")
        if not is_sys_id(sys_id):
            return {"error": "{} is not a sys_id. Use the incident lookup tool first to find the incident sys-id.".format(sys_id)}
        close_notes = args.get("close_notes")
        close_code = args.get("close_code")
        comments = args.get("comments")

        try:
            response = self.client.update_incident(
                issue_id=sys_id,
                status="Resolved",  # <- there is also Closed, Canceled
                close_code=close_code,
                close_notes=close_notes,
                comments=comments,
                can_raise=True
            )
            json_response = response.json()
        except Exception as error:
            logger.error("There was an error '{}' while closing the issue".format(error))
            return {
                "output": "There was a problem while closing the issue ticket: {}".format(error)
            }
        created_issue = json_response.get("result", {})
        output = 'Issue {} has been closed. It is available at {}'.format(
            created_issue.get("number"),
            self.client.get_issue_url(json_response)
        )
        logger.info("servicenow tool output: {}".format(output))

        # Log outputs to trace
        trace.outputs["output"] = output

        return {
            "output": output
        }
