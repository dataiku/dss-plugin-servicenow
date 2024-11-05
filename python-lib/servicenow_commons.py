def get_user_password_server_from_config(config):
    auth_type = config.get("auth_type", "basic_per_user")
    credentials = config.get(auth_type, {})
    return credentials.get("user_name", ""), credentials.get("password", ""), credentials.get("server_url", "")


def get_failed_steps(scenario_variables):
    failed_steps = []
    if isinstance(scenario_variables, dict):
        for key in scenario_variables:
            if key.startswith("stepOutcome_"):
                value = scenario_variables.get(key)
                if value == "FAILED":
                    step_name = key.split("stepOutcome_")[1]
                    failed_steps.append(step_name)
    return failed_steps


def get_failed_steps_outputs(scenario_variables):
    failed_steps = get_failed_steps(scenario_variables)
    # ['noken']
    failed_steps_outputs = {}
    for step in scenario_variables:
        if step.startswith("stepOutput_"):
            step_name = step.split("stepOutput_")[1]
            if step_name in failed_steps:
                failed_steps_outputs[step_name] = scenario_variables.get(step)
    return failed_steps_outputs


def get_step_results(scenario_variables, failed_steps_names):
    step_ids = []
    if "stepResults" in scenario_variables:
        step_results = scenario_variables.get("stepResults", {})
        for failed_step_name in failed_steps_names:
            failed_step = step_results.get(failed_step_name, {})
            target = failed_step.get("target", {})
            step_id = target.get("stepId", "")
            step_ids.append(step_id)
    return step_ids


def extract_faulty_datasets_from_failed_steps(failed_steps):
    faulty_datasets = []
    for failed_step_name in failed_steps:
        failed_step = failed_steps.get(failed_step_name)
        faulty_datasets += extract_faulty_datasets_from_failed_step(failed_step)
    return faulty_datasets


def extract_faulty_datasets_from_failed_step(failed_step):
    faulty_datasets = []
    for dataset_full_name in failed_step:
        failed_step_definition = failed_step.get(dataset_full_name)
        partition = failed_step_definition.get("partition")
        dataset_name = dataset_full_name.split(".")[1]
        dataset_name = dataset_name.split("_{}".format(partition))[0]
        results = failed_step_definition.get("results", [])
        dataset_is_faulty = False
        for result in results:
            value = result.get("value", {})
            outcome = value.get("outcome")
            if outcome in ["WARNING", "FAILED"]:
                dataset_is_faulty = True
        if dataset_is_faulty:
            faulty_datasets.append(dataset_name)
    return faulty_datasets


class RecordsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self):
        if self.has_no_limit:
            return False
        self.counter += 1
        return self.counter > self.records_limit
