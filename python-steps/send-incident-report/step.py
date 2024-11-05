import dataiku
from dataiku.customstep import get_plugin_config
from dataiku.customstep import get_step_config
from servicenow_client import ServiceNowClient
from dataiku.scenario import Scenario
from servicenow_commons import (
    get_failed_steps_outputs, extract_faulty_datasets_from_failed_steps, 
)


plugin_config = get_plugin_config()
config = plugin_config.get("config", {})

current_scenario = Scenario()
scenario_variables = current_scenario.get_all_variables()
print("ALX:scenario_variables={}".format(scenario_variables))
project_key = scenario_variables.get("projectKey")
failed_steps = get_failed_steps_outputs(scenario_variables)

step_config = get_step_config()
print("ALX:step_config={}".format(step_config))

trigger_params = current_scenario.get_trigger_params()
print("ALX:trigger_params={}".format(trigger_params))

client = dataiku.api_client()
project = client.get_project(project_key)
faulty_datasets = extract_faulty_datasets_from_failed_steps(failed_steps)
print("ALX:faulty_datasets={}".format(faulty_datasets))
for faulty_dataset in faulty_datasets:
    print("ALX:faulty_dataset={}".format(faulty_dataset))
    dataset = project.get_dataset(faulty_dataset)
    settings = dataset.get_settings()
    current_status = settings.custom_fields.get("servicenow_incident_status")
    print("ALX:current_status={}".format(current_status))
    if current_status not in ["1", "2"]:
        client = ServiceNowClient(config)
        response = client.post_incident(
            short_description=config.get("short_description"),
            description=config.get("description"),
            caller_id=config.get("caller_id")
        )
        print("ALX:response={}".format(response))
        print("ALX:response.content={}".format(response.content))
        json_response = response.json()
        print("ALX:json_response={}".format(json_response))
        result = json_response.get("result", {})
        sys_id = result.get("sys_id", "")
        opened_at = result.get("opened_at")
        state = result.get("state")
        number = result.get("number")

        print('ALX:1:dir={}'.format(dir(settings)))
        settings.custom_fields["servicenow_incident_status"] = state
        settings.custom_fields["servicenow_sys_id"] = sys_id
        settings.custom_fields["servicenow_number"] = number
        settings.custom_fields["servicenow_opened_at"] = opened_at
        print('ALX:2:custom_fields={}'.format(settings.custom_fields))
        settings.save()
        print('ALX:3')

'''
{
    'dip.home': '/Users/abourret/devenv/dss-home',
    'dku.install.dir': '/Users/abourret/devenv/dip',
    'global_var': '42',
    'projectKey': 'SERVICENOWTESTS',
    'scenarioTriggerParams': {},
    'scenarioTriggerTime': 1730192517671,
    'scenarioTriggerRunId': '2024-10-29-10-01-57-674',
    'stepResults': {
        'noken': {
            'type': 'STEP_DONE',
            'target': {
                'type': 'SCENARIO_STEP',
                'projectKey': 'SERVICENOWTESTS',
                'scenarioId': 'FAULTYSCENARIO2',
                'stepId': 'build_0_true_d_Source_dataset_copy'
            },
            'start': 1730192517845,
            'end': 1730192526353,
            'outcome': 'FAILED'
        }
    },
    'stepResult_noken': {
        'type': 'STEP_DONE',
        'target': {
            'type': 'SCENARIO_STEP',
            'projectKey': 'SERVICENOWTESTS',
            'scenarioId': 'FAULTYSCENARIO2',
            'stepId': 'build_0_true_d_Source_dataset_copy'
        },
        'start': 1730192517845,
        'end': 1730192526353,
        'outcome': 'FAILED'
    },
    'scenarioRunURL': 'http://localhost:8082/projects/SERVICENOWTESTS/scenarios/FAULTYSCENARIO2/runs/list/2024-10-29-10-01-57-686',
    'dssURL': 'http://localhost:8082',
    'stepOutcomes': {
        'noken': 'FAILED'
    },
    'stepOutcome_noken': 'FAILED',
    'outcome': 'FAILED'
}
'''

'''
{
    'dip.home': '/Users/abourret/devenv/dss-home',
    'dku.install.dir': '/Users/abourret/devenv/dip',
    'global_var': '42',
    'projectKey': 'SERVICENOWTESTS',
    'scenarioTriggerParams': {},
    'scenarioTriggerTime': 1729860684765,
    'scenarioTriggerRunId': '2024-10-25-14-51-24-768',
    'stepResults': {
        'build dataset service-now_concourse-picker_copy2': {
            'type': 'STEP_DONE',
            'target': {
                'type': 'SCENARIO_STEP',
                'projectKey': 'SERVICENOWTESTS',
                'scenarioId': 'TEST',
                'stepId': 'build_0_true_d_service-now_concourse-picker_copy2'
            },
            'start': 1729860684950,
            'end': 1729860686350,
            'outcome': 'SUCCESS'
        },
        'Step #2': {
            'type': 'STEP_DONE',
            'target': {
                'type': 'SCENARIO_STEP',
                'projectKey': 'SERVICENOWTESTS',
                'scenarioId': 'TEST',
                'stepId': 'comp_metrics_d_service-now_concourse-picker_copy2'
            },
            'start': 1729860686453,
            'end': 1729860687267,
            'outcome': 'SUCCESS'
        },
        'Step #3': {
            'type': 'STEP_DONE',
            'target': {
                'type': 'SCENARIO_STEP',
                'projectKey': 'SERVICENOWTESTS',
                'scenarioId': 'TEST',
                'stepId': 'check_WARNING_d_service-now_concourse-picker_copy2'
            },
            'start': 1729860687286,
            'end': 1729860687906,
            'outcome': 'FAILED'
        }
    },
    'scenarioRunURL': 'http://localhost:8082/projects/SERVICENOWTESTS/scenarios/TEST/runs/list/2024-10-25-14-51-24-794',
    'dssURL': 'http://localhost:8082',
    'stepOutcomes': {
        'build dataset service-now_concourse-picker_copy2': 'SUCCESS',
        'Step #2': 'SUCCESS',
        'Step #3': 'FAILED'
    },
    'stepResult_Step #3': {
        'type': 'STEP_DONE',
        'target': {
            'type': 'SCENARIO_STEP',
            'projectKey': 'SERVICENOWTESTS',
            'scenarioId': 'TEST',
            'stepId': 'check_WARNING_d_service-now_concourse-picker_copy2'
        },
        'start': 1729860687286,
        'end': 1729860687906,
        'outcome': 'FAILED'
    },
    'stepOutcome_build dataset service-now_concourse-picker_copy2': 'SUCCESS',
    'stepResult_Step #2': {
        'type': 'STEP_DONE',
        'target': {
            'type': 'SCENARIO_STEP',
            'projectKey': 'SERVICENOWTESTS',
            'scenarioId': 'TEST',
            'stepId': 'comp_metrics_d_service-now_concourse-picker_copy2'
        },
        'start': 1729860686453,
        'end': 1729860687267,
        'outcome': 'SUCCESS'
    },
    'stepResult_build dataset service-now_concourse-picker_copy2': {
        'type': 'STEP_DONE',
        'target': {
            'type': 'SCENARIO_STEP',
            'projectKey': 'SERVICENOWTESTS',
            'scenarioId': 'TEST',
            'stepId': 'build_0_true_d_service-now_concourse-picker_copy2'
        },
        'start': 1729860684950,
        'end': 1729860686350,
        'outcome': 'SUCCESS'
    },
    'stepOutput_Step #2': {
        'SERVICENOWTESTS.service-now_concourse-picker_copy2_NP': {
            'target': {
                'type': 'DATASET_PARTITION',
                'projectKey': 'SERVICENOWTESTS',
                'datasetName': 'service-now_concourse-picker_copy2',
                'partition': 'NP'
            },
            'partition': 'NP',
            'startTime': 1729860686505,
            'endTime': 1729860687120,
            'skipped': [],
            'computed': [{
                'metric': {
                    'metricType': 'SIZE',
                    'type': 'basic',
                    'id': 'basic:SIZE',
                    'dataType': 'BIGINT'
                },
                'metricId': 'basic:SIZE',
                'dataType': 'BIGINT',
                'value': '11930'
            }, {
                'metric': {
                    'metricType': 'COUNT_COLUMNS',
                    'type': 'basic',
                    'id': 'basic:COUNT_COLUMNS',
                    'dataType': 'BIGINT'
                },
                'metricId': 'basic:COUNT_COLUMNS',
                'dataType': 'BIGINT',
                'value': '107'
            }, {
                'metric': {
                    'metricType': 'COUNT_FILES',
                    'type': 'basic',
                    'id': 'basic:COUNT_FILES',
                    'dataType': 'BIGINT'
                },
                'metricId': 'basic:COUNT_FILES',
                'dataType': 'BIGINT',
                'value': '1'
            }, {
                'metric': {
                    'metricType': 'COUNT_RECORDS',
                    'type': 'records',
                    'id': 'records:COUNT_RECORDS',
                    'dataType': 'BIGINT'
                },
                'metricId': 'records:COUNT_RECORDS',
                'dataType': 'BIGINT',
                'value': '68'
            }, {
                'metric': {
                    'metricType': 'METRICS_COMPUTATION_DURATION',
                    'type': 'reporting',
                    'id': 'reporting:METRICS_COMPUTATION_DURATION',
                    'dataType': 'BIGINT'
                },
                'metricId': 'reporting:METRICS_COMPUTATION_DURATION',
                'dataType': 'BIGINT',
                'value': '615'
            }],
            'runs': [{
                'engine': 'Basic'
            }, {
                'engine': 'Basic'
            }]
        }
    },
    'stepOutput_Step #3': {
        'SERVICENOWTESTS.service-now_concourse-picker_copy2_NP': {
            'partition': 'NP',
            'metricsRuns': [{
                'engine': 'Basic'
            }],
            'results': [{
                'check': {
                    'type': 'ColumnCountInRangeRule',
                    'minimum': 1.0,
                    'minimumEnabled': True,
                    'maximum': 0.0,
                    'maximumEnabled': False,
                    'softMinimum': 0.0,
                    'softMinimumEnabled': True,
                    'softMaximum': 3.0,
                    'softMaximumEnabled': True,
                    'id': 'ReTSZvhO',
                    'displayName': 'Column count is between 1 and 3',
                    'computeOnBuildMode': 'PARTITION',
                    'autoRun': True,
                    'enabled': True
                },
                'value': {
                    'outcome': 'WARNING',
                    'message': '107 (> 3.0)'
                }
            }],
            'startTime': 1729860687315,
            'endTime': 1729860687731,
            'description': 'dataset:SERVICENOWTESTS.service-now_concourse-picker_copy2 partition:NP',
            'runs': [{
                'name': 'ReTSZvhO',
                'partition': 'NP'
            }]
        }
    },
    'stepOutcome_Step #3': 'FAILED',
    'stepOutcome_Step #2': 'SUCCESS',
    'outcome': 'FAILED'
}
'''