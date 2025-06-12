from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServicenowLookupIncidentIDTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)

    def get_descriptor(self, tool):
        descriptor = {
            "description": "This tool can be used to search for a incident on this ServiceNow instance. The input to this tool is a dictionary containing at least one known detail about the incident to lookup, e.g. '{'email':'john.doe@example.com'}' or '{'user_name':'john.doe'}'",
            "inputSchema": {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Lookup Servicenow incident tool",
                "type": "object",
                "properties": {
                    "description_contains": {
                        "type": "string",
                        "decription": "Contain search terms for the incident, for instance 'cannot login' "
                    },
                    "number": {
                        "type": "string",
                        "decription": "Contains the effective number of the incident to look up. It should start with INC folowed by sevent digits, for instance 'INC0010022'"
                    }
                }
            }
        }
        return descriptor

    def invoke(self, input, trace):
        logger.info("servicenow tool invoked with {}".format(input))
        args = input.get("input", {})

        # Log inputs and config to trace
        trace.span["name"] = "SERVICENOW_LOOKUP_CALLER_ID_TOOL_CALL"
        for key, value in args.items():
            trace.inputs[key] = value
        trace.attributes["config"] = {"servicenow_server_url": self.client.server_url}

        description_contains = args.get("description_contains")
        number = args.get("number")

        # https://www.servicenow.com/community/developer-forum/get-the-user-sys-id-by-usrname-in-rest-api/m-p/1448992
        # https://<INSTNACE>.service-now.com/api/now/table/sys_user?sysparm_query%3Duser_name=<USERNAME>&sysparm_fields=sys_id&sysparm_limit=1
        # sysparm_query=descriptionCONTAINSunable+to+connect

        try:
            incidents = self.client.lookup_incident(
                description_contains=description_contains,
                number=number
            )
        except Exception as error:
            logger.error("There was an error '{}' while creating the issue".format(error))
            return {
                "output": "There was a problem while looking up the user: {}".format(error)
            }

        # Log outputs to trace
        trace.outputs["output"] = incidents

        return {
            "output": incidents
        }
