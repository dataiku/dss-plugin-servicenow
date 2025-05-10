from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServicenowCreateIssueTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)

    def get_descriptor(self, tool):
        return {
            "description": "This tool is a wrapper around Servicenow issue_create API, useful when you need to create a Servicenow issue. The input to this tool is a dictionary containing the new issue summary and description, e.g. '{'summary':'new issue summary', 'description':'new issue description'}'",
            "inputSchema": {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Create Servicenow issue tool",
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The issue summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "The issue description"
                    },
                    "impact": {
                        "type": "int",
                        "description": "The impact code. Should be 1, 2 or 3, and is set according to specific rules to follow. Optional."
                    },
                    "urgency": {
                        "type": "int",
                        "description": "The urgency code. Should be 1, 2 or 3, and is set according to specific rules to follow. Optional."
                    }
                },
                "required": ["summary", "description"]
            }
        }

    def invoke(self, input, trace):
        logger.info("servicenow tool invoked with {}".format(input))
        args = input.get("input", {})

        # Log inputs and config to trace
        trace.span["name"] = "SERVICENOW_CREATE_ISSUE_TOOL_CALL"
        for key, value in args.items():
            trace.inputs[key] = value
        trace.attributes["config"] = {"servicenow_server_url": self.client.server_url}

        summary = args.get("summary")
        description = args.get("description")
        impact = args.get("impact")
        urgency = args.get("urgency")

        try:
            response = self.client.post_incident(
                short_description=summary,
                description=description,
                impact=impact,
                urgency=urgency,
                can_raise=True
            )
            json_response = response.json()
        except Exception as error:
            logger.error("There was an error '{}' while creating the issue".format(error))
            return {
                "output": "There was a problem while creating the issue ticket: {}".format(error)
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
