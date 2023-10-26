#!/usr/bin/env python

from ansible_vault import Vault
from getpass import getpass
import sys, yaml, argparse

parser = argparse.ArgumentParser(
    prog='ansible-vault-util',
    description='Ansible Vault Utility')

parser.add_argument('filename')
parser.add_argument('-o', '--output')
parser.add_argument('-m', '--mode')
# TODO: add support for nested secrets


# FIX YAML MULTILINE VALUES
def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data"""
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def read_vault_full(filename, password):
    output = {}
    try:
        vault = Vault(password)
        output = vault.load(open(filename).read())
    finally:
        return output


def read_vault_mixed(filename, password):
    vault = Vault(password)
    input = read_clear_yaml(filename)
    output = {}
    try:
        for key, value in input.items():
            output[key] = vault.load(value)
    finally:
        return output


def read_clear_yaml(filename):
    with open(filename, 'r') as file:
        input = file.read()
        file.close()
        return yaml.safe_load(input.replace(': !vault |', ': |'))


def write_clear_yaml(filename, output):
    with open(filename, 'w') as file:
        yaml.dump(output, file)
        file.close()


def write_vault_full(filename, password, output):
    vault = Vault(password)
    vault.dump_raw(output.encode("utf-8"), open(filename, 'w'))


def write_vault_mixed(filename, password, output):
    vault = Vault(password)
    for key, value in output.items():
        output[key] = vault.dump_raw(value)

    write_clear_yaml(filename, output)

    # Fix Vault yaml entries
    with open(filename, 'r') as file:
        input = file.read()
        file.close()

        with open(filename, 'w') as file:
            file.write(input.replace(': |', ': !vault |'))
            file.close()


def read_auto(filename):
    vault_pass = getpass(prompt="Enter vault password: ")

    input = read_vault_full(filename, vault_pass)
    if len(input) > 0:
        return input, vault_pass

    input = read_vault_mixed(filename, vault_pass)
    if len(input) > 0:
        return input, vault_pass

    input = read_clear_yaml(filename)
    if len(input) > 0:
        return input, vault_pass


if __name__ == '__main__':
    args = parser.parse_args()

    yaml.add_representer(str, str_presenter)
    yaml.representer.SafeRepresenter.add_representer(str, str_presenter) # to use with safe_dum

    # read existing vault
    input, vault_pass = read_auto(args.filename)

    if args.output:
        # default output mode
        if not args.mode:
            args.mode = "clear"

        if args.mode == 'clear':
            print("writing clear text to file", args.output)
            write_clear_yaml(args.output, input)

        if args.mode == 'mixed':
            print("writing mixed vault/text to file", args.output)
            write_vault_mixed(args.output, vault_pass, input)

        if args.mode == 'vault':
            print("writing fully encrypted vault to file", args.output)
            write_vault_full(args.output, vault_pass, input)

    else:
        print(input)
