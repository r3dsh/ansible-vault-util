
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

### Examples

Printing fully encrypted file
```shell
x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11
❯ cat test-file.vault.yaml
$ANSIBLE_VAULT;1.1;AES256
63613666353761646237626562323332336630346630326562356430626630663138333662626638
3436366235323235633263396362336139646434656664390a636434363932626237303337323463
62393237393136643235363762386466323963323438633339363166643639363338613437376462
6635386438333463610a386438656362333037633063363034393136306261656631653133343039
66306531363862323930646536653936343565636630306566386636613631373965666233356331
6236653964623532366365373562376661386436643738306235                                                                                                                                                        /0.0s

x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11
❯ ./ansible-vault-util.py test-file.vault.yaml
Enter vault password:
{'foo': 'bar', 'bam': 'bap', 'baz': {'wep': 'test'}}
```

Converting fully encrypted file to mixed
```shell
x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11 took 2s
❯ ./ansible-vault-util.py test-file.vault.yaml -o test-file.mixed.yaml -m mixed
Enter vault password:
writing mixed vault/text to file test-file.mixed.yaml                                                                                                                                                       /2.1s

x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11 took 2s
❯ cat test-file.mixed.yaml
bam: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  65363830333138343734653331653539376638643735613964643063646262626432363732393639
  3936396536656564646364336530633534336537376566360a316636303934303535303466623739
  33353364346664386135383535303138356635646362383864646463366233353962643137666434
  3833613834363532660a633664353431393531376437393064646538343865613365396161356133
  3837
baz: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  34336134633939386266646162636665316331653863343437376537343031396662616234623035
  3764396663363638663561353430633436336639613931360a336334633538613365353631316464
  33373465383265386537663464393435656336373438306661316332346363363966343465643536
  3862636235353436610a666138633966376138343837346366643039393535393362396539303938
  3464
foo: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  31373232613537386237666537323136326563316539303461346236313937373639653062326332
  3462636463383765643565323732376263386535396561610a316266666534316463343832343762
  35353862346466386434373938326133383730336338333034633431346362306435646239323133
  3939663330303065630a356532323663646633353435333961303331626230623963363034656163
  3766
```

Printing mixed content file:
```shell
x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11
❯ ./ansible-vault-util.py test-file.mixed.yaml
Enter vault password:
{'bam': 'bap', 'baz': {'wep': 'test'}, 'foo': 'bar'}
```

Converting mixed content file to clear text:
```shell
x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11
❯ ./ansible-vault-util.py test-file.mixed.yaml -o test-file.clear.yaml -m clear
Enter vault password:
writing clear text to file test-file.clear.yaml                                                                                                                                                             /1.5s

x in 🌐 maze1 in ansible-vault on  main [!] via 🐍 v3.10.11
❯ cat test-file.clear.yaml
bam: bap
baz:
  wep: test
foo: bar
```