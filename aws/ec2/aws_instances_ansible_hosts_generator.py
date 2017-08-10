#!/usr/bin/python

import json
import os

import boto3

CONFIG = 'aws_instances_ansible_hosts_generator.config.default'

ANSIBLE_FOLDER_NAME = 'ansible'
HOSTS_FILENAME = 'hosts'

HOME_DIR = os.path.expanduser('~')
PATH = os.path.join(HOME_DIR, ANSIBLE_FOLDER_NAME)
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

GROUP_TYPE_ACCOUNT_NAME = 'account_name'
GROUP_TYPE_REGION = 'region'
GROUP_TYPE_TAG = 'tag'
GROUP_TYPE_INSTANCE_TYPE = 'instance_type'
GROUP_TYPE_INSTANCE_STATE = 'state'

KNOWN_EC2_TAGS = [
    'OS Platform',
    'OS Version',
    'Project',
]


def __tag_finder(tags, key):
    for tag in tags:
        if tag['Key'] == key:
            return tag['Value']


def get_config():
    with open(os.path.join(SCRIPT_PATH, CONFIG), 'r') as opened_file:
        content = opened_file.read()
    return json.loads(content)


def generate_account_ec2_info():
    return [
        {
            "account_name": config['account_name'],
            "ec2_objects": [
                {
                    "region": region,
                    "ec2_object": boto3.resource(
                        'ec2',
                        aws_access_key_id=config['aws_access_key'],
                        aws_secret_access_key=config['aws_secret_key'],
                        region_name=region
                    )
                }
                for region in config['regions']
            ]
        }
        for config in get_config()
    ]


def group_instances_by_tag(ec2_object, seperator=','):
    group = {}

    for instance in ec2_object.instances.all():
        if instance.state['Name'] == 'running':
            tags = instance.tags
            for tag_dict in tags:
                key = tag_dict['Key']
                value = tag_dict['Value']
                if key in KNOWN_EC2_TAGS and value:
                    for tag in value.split(seperator):
                        tag = tag.strip()

                        if tag in group:
                            group[tag].append(instance)
                        else:
                            group[tag] = [instance]
    return group


def __group_instances_by_instance_attribute(ec2_object, attribute):
    group = {}

    for instance in ec2_object.instances.all():
        if instance.state['Name'] == 'running':
            result = getattr(instance, attribute)
            if result in group:
                group[result].append(instance)
            else:
                group[result] = [instance]
    return group


def group_instances_by_instance_type(ec2_object):
    return __group_instances_by_instance_attribute(ec2_object, 'instance_type')


def group_instances(account_ec2_list, group_type):
    group_info = {}

    group_key = 'group'

    for account_ec2 in account_ec2_list:
        account_name = account_ec2['account_name']
        for ec2 in account_ec2['ec2_objects']:
            region = ec2['region']
            ec2_object = ec2['ec2_object']

            if group_type == GROUP_TYPE_ACCOUNT_NAME:
                group_info['group_type'] = GROUP_TYPE_ACCOUNT_NAME
                temp_group_dict = {
                    account_name: [instance for instance in ec2_object.instances.all() if instance.state['Name'] == 'running']
                }
            elif group_type == GROUP_TYPE_REGION:
                group_info['group_type'] = GROUP_TYPE_REGION
                temp_group_dict = group_instances_by_region(ec2_object)
            elif group_type == GROUP_TYPE_TAG:
                group_info['group_type'] = GROUP_TYPE_TAG
                temp_group_dict = group_instances_by_tag(ec2_object)
            elif group_type == GROUP_TYPE_INSTANCE_TYPE:
                group_info['group_type'] = GROUP_TYPE_INSTANCE_TYPE
                temp_group_dict = group_instances_by_instance_type(ec2_object)
            elif group_type == GROUP_TYPE_INSTANCE_STATE:
                group_info['group_type'] = GROUP_TYPE_INSTANCE_STATE
                temp_group_dict = group_instances_by_instance_state(ec2_object)
            else:
                raise RuntimeError('No group type "{}"'.format(group_type))

            if group_key not in group_info:
                group_info[group_key] = temp_group_dict
            else:
                if temp_group_dict:
                    for key, instance_list in temp_group_dict.items():
                        if key in group_info[group_key]:
                            group_info[group_key][key].extend(temp_group_dict[key])
    return group_info


def to_ansible_hosts(group_info):
    result = ''

    group_type = group_info['group_type']
    group = group_info['group']

    for group_key, instance_list in group.items():
        result += '# Grouped by "{group_type}:{group_key}"'.format(group_type=group_type, group_key=group_key)
        result += '\n'
        result += '[{group_key}]'.format(group_key=group_key)
        result += '\n'
        for instance in instance_list:
            result += '{name} ansible_port=2073 ansible_host={ip_address}'.format(name=__tag_finder(instance.tags, 'Name'), ip_address=instance.public_ip_address)
            result += '\n'
        result += '\n'
    return result


def to_file(*args, **kwargs):
    ansible_host_filename = os.path.join(PATH, HOSTS_FILENAME)
    if not os.path.exists(PATH):
        os.makedirs(PATH)
    if not os.path.exists(ansible_host_filename) or ('force' in kwargs and kwargs['force']):
        with open(ansible_host_filename, 'w') as opened_file:
            opened_file.write('---')
            opened_file.write('\n')
            for result in args:
                opened_file.write(result)
            opened_file.write('...')
    else:
        raise Exception('host file exists.')
    return ansible_host_filename
    

def main():
    account_ec2_info_list = generate_account_ec2_info()
    
    group_instance_tag_info = group_instances(account_ec2_info_list, GROUP_TYPE_TAG)
    group_instance_type_info = group_instances(account_ec2_info_list, GROUP_TYPE_INSTANCE_TYPE)
    group_account_name_info = group_instances(account_ec2_info_list, GROUP_TYPE_ACCOUNT_NAME)
    group_region_info = group_instances(account_ec2_info_list, GROUP_TYPE_REGION)

    # to_ansible_hosts(group_instance_tag_info)
    # to_ansible_hosts(group_instance_type_info)
    # to_ansible_hosts(group_account_name_info)

    print to_file(
        to_ansible_hosts(group_account_name_info),
        to_ansible_hosts(group_instance_tag_info),
        to_ansible_hosts(group_instance_type_info)
        to_ansible_hosts(group_region_info)
    )


if __name__ == '__main__':
    main()
    
