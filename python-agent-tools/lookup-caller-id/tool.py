from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient
from safe_logger import SafeLogger


logger = SafeLogger("servicenow plugin", ["password"])


class ServicenowLookupCallerIDTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)

    def get_descriptor(self, tool):
        descriptor = {
            "description": "This tool can be used to search for a user of this ServiceNow instance. The input to this tool is a dictionary containing at least one known detail about the user to lookup, e.g. '{'email':'john.doe@example.com'}' or '{'user_name':'john.doe'}'",
            "inputSchema": {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Create Servicenow issue tool",
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "decription": "The email address of the user to lookup, for instance 'john.doe@example.com' "
                    },
                    "name": {
                        "type": "string",
                        "decription": "The full name of the user to search, for instance 'John Doe'"
                    },
                    "user_name": {
                        "type": "string",
                        "decription": "The system user name of the user to lookup, for instance 'john.doe'"
                    },
                    "user_id": {
                        "type": "string",
                        "decription": "The system ID of the user to lookup, for instance '9ee1b13dc6112271007f9d0efdb69cd0'"
                    },
                }
            }
        }
        return descriptor

    def load_sample_query(self, tool):
        return {
            "name": "The full name of the user to search, for instance 'John Doe'"
        }

    def invoke(self, input, trace):
        logger.info("servicenow tool invoked with {}".format(input))
        args = input.get("input", {})

        # Log inputs and config to trace
        trace.span["name"] = "SERVICENOW_LOOKUP_CALLER_ID_TOOL_CALL"
        for key, value in args.items():
            trace.inputs[key] = value
        trace.attributes["config"] = {"servicenow_server_url": self.client.server_url}

        email = args.get("email")
        name = args.get("name")
        user_name = args.get("user_name")
        user_id = args.get("user_id")
        # user_name, sys_id, name, email

        # https://www.servicenow.com/community/developer-forum/get-the-user-sys-id-by-usrname-in-rest-api/m-p/1448992
        # https://<INSTNACE>.service-now.com/api/now/table/sys_user?sysparm_query%3Duser_name=<USERNAME>&sysparm_fields=sys_id&sysparm_limit=1

        try:
            users = self.client.lookup_user(
                email=email,
                name=name,
                user_name=user_name,
                sys_id=user_id
            )
        except Exception as error:
            logger.error("There was an error '{}' while creating the issue".format(error))
            return {
                "output": "There was a problem while looking up the user: {}".format(error)
            }

        # Log outputs to trace
        trace.outputs["output"] = users

        return {
            "output": users
        }
