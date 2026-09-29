# Cisco Device Discovery

Read-only Ansible collection of Cisco IOS/IOS XE device information as JSON.
All tasks and the 14 show commands are in `playbooks/collect.yml`; no roles.

## Setup

Run from this folder on Linux/WSL with Python 3.12+ and trusted device SSH host keys.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
mkdir -p input
cp sample_input/devices.csv input/devices.csv
```

## Input

Edit `input/devices.csv` with real device addresses:

```csv
hostname,management_ip,device_type,store_type,site
store-a-sw01,192.0.2.11,,type_a,STORE-A
```

Store types: `type_a`, `type_b`, `type_c`. Blank or omitted `device_type` defaults
to `IOS`. Label NX-OS devices `NXOS`; non-IOS types are recorded as `unsupported`
and skipped. The OS is not detected automatically.

## Run

```bash
ansible-playbook playbooks/collect.yml -u YOUR_USERNAME --ask-pass
```

For enable mode, append `--become --become-method enable --ask-become-pass`.
The same TACACS username/password is used for all input devices.
Optional structured VLAN/interface facts can be enabled by editing
`discovery_resources` in the playbook.

## Older-device SSH compatibility

Use the repo-local [ssh_config](ssh_config) explicitly with libssh.
From the repo root on the Linux/WSL controller:

```bash
ansible-playbook playbooks/collect.yml -u YOUR_USERNAME --ask-pass \
  -e "ansible_libssh_config_file=$PWD/ssh_config"
```

The file enables legacy KEX, RSA host keys, AES-CBC, and SHA-1 MACs for this run.
Replace `Host *` with affected management IPs to narrow its scope. Host-key
verification stays enabled; trusted keys must exist on the controller.
OpenSSH `-o` flags in `ansible_ssh_common_args` do not configure libssh algorithms.
Algorithm availability depends on the controller's libssh build and crypto policy.
If negotiation still fails, inspect `facts_error` in the output JSON and check
`ansible-galaxy collection list ansible.netcommon` and `pip show ansible-pylibssh`.
The config-file option requires `ansible.netcommon` 5.1.0 or newer.

## Output

JSON files: `output/<store_type>/<site>/<hostname>.json`.
Includes structured device facts and text output/status for each show command.
CLI text is stored inside JSON, not parsed into individual policy fields.
Command errors are recorded while collection continues; inspect `status` for
`collected`, `partial`, or `unsupported`. See [sample output](sample_output/store-a-sw01.json).

Output includes running configuration and may contain secrets. Files use mode
`0600`, are Git-ignored, and device output is hidden from Ansible console logs.
