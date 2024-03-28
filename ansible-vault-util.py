#!/usr/bin/env python

import ansible
import argparse
import json
import os
import re
import sys
import tempfile
import yaml
from ansible_vault import Vault
from getpass import getpass

parser = argparse.ArgumentParser(
    prog='ansible-vault-util',
    description='Ansible Vault Utility')

parser.add_argument('filename')
# parser.add_argument('-o', help='output file (default: %(default)s)', dest='output')
parser.add_argument('-m', help='output mode', choices=['clear', 'mixed', 'vault'], dest='mode', default='')
parser.add_argument('-u', help='edit file in place using item key path: -u foo.bar "something here"', dest='update')
parser.add_argument('-o', help='output format', choices=['yaml', 'json'], dest='output_format', default='')
parser.add_argument('-e', help='open decrypted in default $EDITOR', dest='edit', action='store_true')
parser.add_argument('-p', help='change vault password', dest='new_password', action='store_true')
parser.add_argument('-i', help='edit file in place (write back to original file)', dest='edit_in_place',
                    action='store_true')


# Fix yaml multiline values
def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def inject_vault_indicator(yaml_string):
    pattern = r'(\w+:\s*)\|\n(\s*)(\$ANSIBLE_VAULT;[^\n]*)'
    replaced_string = re.sub(pattern, r'\1!vault |\n\2\3', yaml_string)

    return replaced_string


# Wrap strings with quotes
def preprocess_yaml_content(yaml_content):
    lines = yaml_content.split("\n")
    for i, line in enumerate(lines):
        if ": " in line and not line.strip().startswith("-"):
            key, value = line.split(": ", 1)
            # TODO: not sure, should evaluate 'False' as actual False?
            if value.strip()[0] not in ['|', '>', '-', '!', '"', "'"]:
                # if value.strip()[0] not in ['|', '>', '-', '!']:
                # Check if the value can be converted to a number, float, or boolean
                if value.strip() == "true":
                    value = True
                elif value.strip() == "false":
                    value = False
                else:
                    try:
                        value = eval(value.strip())
                    except (ValueError, SyntaxError, NameError):
                        # If not, wrap it in double quotes
                        value = f'"{value.strip()}"'

            lines[i] = f"{key}: {value}"
    return "\n".join(lines)


yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)  # to use with safe_dump


class VaultUtil:

    def __init__(self, filename=None, password=None):
        self.filename = filename
        self.password = password
        self.vault = None
        self.dict = {}

        yaml.add_multi_constructor('!vault', self.vault_ctor)
        # yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))

    def change_password(self):
        password1 = getpass(prompt="Enter new vault password: ")
        password2 = getpass(prompt="Repeat new vault password: ")
        if password1 == password2:
            if password2 == self.password:
                print("New vault password is the same as current password", file=sys.stderr)
                sys.exit(1)
            self.password = password2
            self.vault = Vault(self.password)
        else:
            print("Passwords don't match", file=sys.stderr)
            sys.exit(1)

    def vault_ctor(self, loader, tag_suffix, node):
        plain = ""

        if node.value.strip().startswith('$ANSIBLE_VAULT'):
            if not self.vault:
                self.password = getpass(prompt="Enter vault password: ")
                self.vault = Vault(self.password)

        # TODO: skip decryption when in append mode - do not reencrypt existing items
        try:
            plain = self.vault.load(node.value)
        except yaml.scanner.ScannerError:
            plain = self.vault.load_raw(node.value).decode()

        except ansible.parsing.vault.AnsibleVaultError:
            print("Invalid Vault password or no secrets available", file=sys.stderr)
            sys.exit(1)

        return plain

    def detect_content_mode(self):
        with open(self.filename, 'r') as file:
            content = file.read()
            file.close()

            if content.strip().startswith('$ANSIBLE_VAULT'):
                return content, 'vault'

            if '$ANSIBLE_VAULT' in content.strip():
                return content, 'mixed'

        return content, 'clear'

    def load(self):
        content, mode = self.detect_content_mode()

        if mode != "vault":
            self.dict = yaml.load(preprocess_yaml_content(content), Loader=yaml.FullLoader)
        else:
            if not self.vault:
                self.password = getpass(prompt="Enter vault password: ")
                self.vault = Vault(self.password)

            try:
                self.dict = self.vault.load(content)
            except ansible.parsing.vault.AnsibleVaultError:
                print("Invalid Vault password or not secrets available", file=sys.stderr)
                sys.exit(1)

        return self.dict, mode

    def encrypt_full(self, content):
        if not self.vault:
            self.password = getpass(prompt="Enter vault password: ")
            self.vault = Vault(self.password)

        return self.vault.dump_raw(content)

    def encrypt(self, node=None):
        output = {}

        if not self.vault:
            self.password = getpass(prompt="Enter vault password: ")
            self.vault = Vault(self.password)

        for key, value in node.items():
            if type(value) == dict:
                output[key] = self.encrypt(value)
            else:
                output[key] = self.vault.dump_raw(value)

        return output


if __name__ == '__main__':
    args = parser.parse_args()

    vu = VaultUtil(args.filename)
    text, mode = vu.load()

    output_data = ''

    if args.output_format and args.edit_in_place:
        print("Arguments -i and -o are not supported together", file=sys.stderr)
        sys.exit(1)

    if args.edit and args.edit_in_place:
        print("Arguments -i and -e are not supported together", file=sys.stderr)
        sys.exit(1)

    if args.new_password and mode == 'clear':
        print("Password change was requested but input file is not encrypted", file=sys.stderr)
        sys.exit(1)

    if args.new_password and args.mode == 'clear':
        print("Password change was requested but output mode is clear text", file=sys.stderr)
        sys.exit(1)

    if args.new_password:
        vu.change_password()
        args.edit_in_place = True

        # when changing password we don't change mode if not explicitly set
        if args.mode == '':
            args.mode = 'clear'


    if args.edit:
        # print("Opening editor for:", yaml.dump(text, sort_keys=False))
        temp = tempfile.NamedTemporaryFile(delete=False)

        # write to temporary file
        with open(temp.name, 'w') as tmp:
            tmp.write(yaml.dump(text, sort_keys=False))
            tmp.close()
        # open default shell editor
        print("starting editor", temp.name, file=sys.stderr)

        if os.environ.get("EDITOR") is None:
            os.environ["EDITOR"] = "/usr/bin/vi"
        os.system("$EDITOR " + temp.name)

        orig_pass = vu.password
        orig_vault = vu.vault

        vu = VaultUtil(temp.name)
        vu.password = orig_pass
        vu.vault = orig_vault

        text, mode = vu.load()
        # vu.filename = args.filename

        args.edit_in_place = True

    # PROCESSING DECRYPTED CONTENT

    # TODO: I think this one is valid chain?
    print(args)
    print(mode)
    # if args.mode == '' and not args.edit_in_place:
    #     args.mode = 'clear'
    #     args.output_format = 'yaml'

    # if no output mode was selected input mode == output mode
    if args.mode == '':
        args.mode = 'clear'

    if args.mode == 'vault':
        if args.output_format != "":
            print("Vault mode doesn't work with -o argument, remove -o or add -m to adjust output", file=sys.stderr)
            sys.exit(1)
        output_data = vu.encrypt_full(yaml.dump(text, sort_keys=False))

    if args.mode == 'mixed':
        if args.output_format == '':
            args.output_format = 'yaml'

        enc = vu.encrypt(vu.dict)

        if args.output_format == 'yaml':
            output_data = inject_vault_indicator(yaml.dump(enc, sort_keys=False))
        if args.output_format == 'json':
            output_data = json.dumps(enc)

    if args.mode == 'clear':
        if args.output_format == '':
            args.output_format = 'yaml'

        if args.output_format == 'yaml':
            output_data = yaml.dump(text, sort_keys=False)
        if args.output_format == 'json':
            output_data = json.dumps(text)

    # write back to original file
    if args.edit_in_place:
        with open(args.filename, 'w') as file:
            file.write(output_data)
            file.close()

    if not args.edit_in_place:
        print(output_data)
