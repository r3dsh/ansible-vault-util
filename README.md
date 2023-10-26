
# Simple Ansible Vault helper utility

Usage:
```shell
./ansible-vault-util.py --help
usage: ansible-vault-util [-h] [-o OUTPUT] [-m MODE] filename

Ansible Vault Utility

positional arguments:
  filename

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
  -m MODE, --mode MODE
```

Supported output modes:
- clear - plain text output
- mixed - mixed plain keys and ecnrypted values
- vault - full file encryption

