from dataiku.llm.agent_tools import BaseAgentTool
from servicenow_client import ServiceNowClient
import logging


class ServicenowCreateIssueTool(BaseAgentTool):
        
    def set_config(self, config, plugin_config):
        self.config = config
        self.client = ServiceNowClient(config)

    def get_descriptor(self, tool):
        return {
            "description": "This tool is a wrapper around Servicenow issue_create API, useful when you need to create a Servicenow issue. The input to this tool is a dictionary containing the new issue summary and description, e.g. '{'summary':'new issue summary', 'description':'new issue description'}'",            
            "inputSchema" : {
                "$id": "https://dataiku.com/agents/tools/search/input",
                "title": "Create Servicenow issue tool",
                "type": "object",
                "properties" : {
                    "summary" : {
                        "type": "string",
                        "description": "The issue summary"
                    },
                    "description" : {
                        "type": "string",
                        "description": "The issue description"
                    }
                    
                },
                "required": ["summary", "description"]            
            }
        }
        
    def invoke(self, input, trace):
        args = input.get("input", {})
        summary = args.get("summary")
        description = args.get("description")

        response = self.client.post_incident(
            short_description=summary,
            description=description
        )
        json_response = response.json()
        created_issue = json_response.get("result", {})

        if isinstance(created_issue, dict):
            return { 
                "output" : 'Issue created: {} available at {}'.format(
                    created_issue.get("number"),
                    self.client.get_issue_url(json_response)
                )
            }
        else:
            return {
                "output": created_issue
            }
