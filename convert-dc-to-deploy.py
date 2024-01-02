#!/usr/bin/python3

import sys, argparse, yaml, json

def replace_keys(yaml_dict):
    if isinstance(yaml_dict, dict):
        new_dict = {}
        for key, value in yaml_dict.items():
            new_key = key.replace('deploymentconfig', 'deployment')
            new_dict[new_key] = replace_keys(value)
        return new_dict
    elif isinstance(yaml_dict, list):
        return [replace_keys(item) for item in yaml_dict]
    else:
        return yaml_dict

def print_summary(deployment_config, deployment, use_json=False):
    print("Summary:")
    print_details(deployment_config, deployment, use_json)

def print_details(deployment_config, deployment, use_json=False, indent=2):
    for key in deployment_config:
        if key not in deployment:
            print(f"{' ' * indent}Deleted: {key}")
        elif deployment_config[key] != deployment[key]:            
            print(f"{' ' * indent}Modified: {key}")
            if key == 'spec':
                print_details(deployment_config[key], deployment[key], use_json, indent + 2)
            else:
                print(f"{' ' * (indent + 2)}Details:") 
                print(f"{' ' * (indent + 4)}Old Value:",end= " ")
                if use_json:
                    print(json.dumps(deployment_config[key], indent=2))
                else:
                    print(deployment_config[key])
                print(f"{' ' * (indent + 4)}New Value:",end= " ")
                if use_json:
                    print(json.dumps(deployment[key], indent=2))
                else:
                    print(deployment[key])
        elif key == 'spec.template':
            print(f"{' ' * indent}Details:")
            print(f"{' ' * (indent + 2)}Spec.Template:")
            if use_json:
                print(json.dumps(deployment[key], indent=2))
            else:
                print(deployment[key])

def get_dict_diff(dict1, dict2):
    diff = {}
    for key, value in dict1.items():
        if key not in dict2 or dict2[key] != value:
            diff[key] = value
    return diff

def convert_deploymentconfig_to_deployment(yaml_file_path, print_summary_flag=False, use_json=False):
    try:
        #with open(yaml_file_path, 'r') as file:
        dc_yaml = yaml.safe_load(yaml_file_path)
    except FileNotFoundError:
        print(f"Error: File not found - {yaml_file_path}")
        sys.exit(1)

    # Replace "deploymentconfig" with "deployment" in the keys of the YAML structure
    dc_yaml_modified = replace_keys(dc_yaml)

    # Convert 'Rolling' to 'RollingUpdate' in strategy field
    strategy = dc_yaml_modified['spec'].get('strategy', {})
    strategy_type = strategy.get('type', None)
    if strategy_type == 'Rolling':
        strategy['type'] = 'RollingUpdate'

    # List of keys to replace in rollingParams
    rolling_params_keys = ['activeDeadlineSeconds', 'intervalSeconds', 'timeoutSeconds', 'updatePeriodSeconds']

    # Omit specified fields in rollingParams if present in source
    for key in rolling_params_keys:
        if key in strategy.get('rollingParams', {}):
            strategy['rollingParams'].pop(key)

    # Omit resources
    strategy.pop('resources', None)

    # Omit test
    dc_yaml_modified.pop('test', None)

    # Omit 'paused' in destination if it's not present in source
    paused = dc_yaml_modified['spec'].get('paused', None)
    deployment_paused = {'paused': paused} if paused is not None else {}

    # Keys to include directly in the new Deployment spec
    keys_to_include = ['replicas', 'template', 'strategy']# 'selector']

    dc_yaml_modified

    # Create a new Deployment YAML
    deployment_yaml = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': dc_yaml_modified['metadata'],
        'spec': {key: dc_yaml_modified['spec'].get(key, {}) for key in keys_to_include},        
        **deployment_paused
    }
    deployment_yaml['spec']['selector'] = {'matchLabels': dc_yaml_modified['spec'].get('selector', {})}

    # Print the summary if requested
    if print_summary_flag:
        print_summary(dc_yaml, deployment_yaml, use_json)

    # Convert the Deployment YAML to a string
    deployment_yaml_str = yaml.dump(deployment_yaml, default_flow_style=False)

    if not print_summary_flag:
        print(deployment_yaml_str)

if __name__ == "__main__":
    # Create argparser
    parser = argparse.ArgumentParser(description="Convert DeploymentConfig to Deployment")

    # Add arguments
    parser.add_argument("--file_path", "-f", help="Path to the DeploymentConfig YAML file", type = argparse.FileType('r'), default = '-')
    parser.add_argument("--summary", action="store_true", help="Print a summary of changes")
    parser.add_argument("--use-json", action="store_true", help="Use json.dumps for printing")
    
    # Parse arguments
    args = parser.parse_args()

    # Convert dc to deploy
    convert_deploymentconfig_to_deployment(args.file_path, args.summary, args.use_json)
