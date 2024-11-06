# ServiceNow Plugin

This Dataiku DSS plugin provides a read connector to interact with [ServiceNow](https://www.servicenow.com/) tables.

## Setup

### Create service accounts

As a DSS admin, go to *Applications > Plugins > Installed > ServiceNow > Settings > Service accounts > + Add preset*. Add the URL to the ServiceNow instance to reach. Add the user name and password of the ServiceNow account that will be used to interact with the instance. Finally, share the preset with the relevant groups.

### Create an instance preset for user accounts

As a DSS admin, go to *Applications > Plugins > Installed > ServiceNow > Settings > User accounts > + Add preset*. Add the URL to the ServiceNow instance to reach. Share the preset with everyone.
Once this preset is create, each DSS user that requires accessing to the ServiceNow instance will have to go to their own *profile page > Credentials > created preset > Edit symbol*, and add their own user name and password. 

## Read a ServiceNow table

In the flow, click on +Dataset > Plugins/ServiceNow > ServiceNow table to dataset. Select the appropriate authentication type and preset and the table to retrieve. Press `Test & get schema` and `Create`

## Create a incident ticket on faulty scenario

In the scenario building the target dataset, add a final step with *Add step > ServiceNow / Send a ServiceNow incident*. Select the appropriate authentication type and preset, and fill in the standard message template to be sent to the ServiceNow operator. This template can contain variables such as ${projectKey}.

## Check incident resolution from within DSS

As soon as an incident has been sent to ServiceNow, it is linked to all the datasets declared in the scenario step. The incident is now visualized by a red ticket, which reveals the incident number, date and current status.
![](images/incident_status_in_dss_flow.jpg)

## Refresh incident status

From the project, click *... > Macros > servicenow > Refresh incidents status*, select the appropriate authentication type and preset, and press `Run macro`. This will refresh the ticket status for all the datasets present in the project. This macro can be run periodically by using a scenario and running the macro from within a step.

### License

Copyright 2024 Dataiku SAS

This plugin is distributed under the Apache License version 2.0
