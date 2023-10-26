#!/usr/bin/env python

from ansible_vault import Vault
from getpass import getpass
import os, sys, json, yaml, argparse, tempfile

parser = argparse.ArgumentParser(
    prog='ansible-vault-util',
    description='Ansible Vault Utility')

parser.add_argument('filename')
parser.add_argument('-o', help='output file (default: %(default)s)', dest='output')
parser.add_argument('-m', default='clear', choices=['clear', 'mixed', 'vault'], help='output mode', dest='mode')
parser.add_argument('-u', help='in-place vault edit: -u foo.bar "something here"')
parser.add_argument('-y', action='store_true', help='print yaml when clear mode is used', dest='yaml')
parser.add_argument('-e', action='store_true', help='open decrypted in default $EDITOR', dest='edit')


# FIX YAML MULTILINE VALUES
def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data"""
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def process_data(items, password, encrypt=False):
    vault = Vault(password)
    output = {}
    for key, value in items.items():
        if type(value) == dict:
            output[key] = process_data(value, password, encrypt) if encrypt else process_data(value, password, encrypt)
        else:
            output[key] = vault.dump_raw(value) if encrypt else vault.load(value)
    return output


# READ / WRITE fully encrypted files
def read_secure_vault(filename, password):
    output = {}
    try:
        vault = Vault(password)
        output = vault.load(open(filename).read())
    finally:
        return output


def write_secure_vault(filename, password, output, return_only=False):
    vault = Vault(password)
    if return_only:
        return vault.dump_raw(output)

    vault.dump_raw(output, open(filename, 'w'))


# READ / WRITE clear text files
def read_clear_text_yaml(filename):
    with open(filename, 'r') as file:
        input = file.read()
        file.close()
        return yaml.safe_load(input.replace(': !vault |', ': |'))


def write_clear_text_yaml(filename, output):
    with open(filename, 'w') as file:
        print(yaml.dump(output, file))
        file.close()


# READ / WRITE mixed text/encrypted files
def read_mixed_vault(filename, password):
    try:
        return process_data(read_clear_text_yaml(filename), password, encrypt=False)
    finally:
        return {}


def write_mixed_vault(filename, password, output, return_only=False):
    output = process_data(output, password, encrypt=True)
    if return_only:
        return yaml.dump(output).replace(': |', ': !vault |')

    write_clear_text_yaml(filename, output)

    # Fix Vault yaml entries
    with open(filename, 'r') as file:
        input = file.read()
        file.close()

        with open(filename, 'w') as file:
            file.write(input.replace(': |', ': !vault |'))
            file.close()


def auto_read(filename):
    vault_pass = getpass(prompt="Enter vault password: ")

    input = read_secure_vault(filename, vault_pass)
    if len(input) > 0:
        return input, vault_pass, "vault"

    input = read_mixed_vault(filename, vault_pass)
    if len(input) > 0:
        return input, vault_pass, "mixed"

    input = read_clear_text_yaml(filename)
    if len(input) > 0:
        return input, vault_pass, "clear"


if __name__ == '__main__':
    args = parser.parse_args()

    yaml.add_representer(str, str_presenter)
    yaml.representer.SafeRepresenter.add_representer(str, str_presenter) # to use with safe_dum

    # read existing vault
    input, vault_pass, detected_mode = auto_read(args.filename)

    if args.edit:
        fd, path = tempfile.mkstemp()
        try:
            # write to temporary file
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(yaml.dump(input))
                tmp.close()
            # open default shell editor
            os.system("$EDITOR " + path)
        finally:
            # read temp file and push to open file
            with open(path, 'r') as file:
                input = yaml.safe_load(file)
                file.close()

                # allow override target mode - when editor exists
                if args.mode:
                    detected_mode = args.mode

                if detected_mode == 'clear':
                    write_clear_text_yaml(args.filename, input)

                if detected_mode == 'mixed':
                    write_mixed_vault(args.filename, vault_pass, input)

                if detected_mode == 'vault':
                    write_secure_vault(args.filename, vault_pass, input)

        sys.exit()

    if not args.mode:
        args.mode = "clear"

    if args.output:
        # default output mode
        if args.mode == 'clear':
            print("writing clear text to file", args.output)
            write_clear_text_yaml(args.output, input)

        if args.mode == 'mixed':
            print("writing mixed vault/text to file", args.output)
            write_mixed_vault(args.output, vault_pass, input)

        if args.mode == 'vault':
            print("writing fully encrypted vault to file", args.output)
            write_secure_vault(args.output, vault_pass, input)
    else:
        if args.mode == 'clear':
            if args.yaml:
                print(yaml.dump(input))
            else:
                print(json.dumps(input))

        if args.mode == 'mixed':
            print(write_mixed_vault(args.output, vault_pass, input, return_only=True))

        if args.mode == 'vault':
            print(write_secure_vault(args.output, vault_pass, input, return_only=True))
