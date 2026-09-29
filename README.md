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

## SSH and local host keys

The playbook uses repo-local `ssh_config` and `known_hosts` automatically.
Legacy KEX, RSA host keys, AES-CBC, and SHA-1 MACs are enabled in `ssh_config`.
It renders `.ssh_config.runtime` with an absolute host-key path for libssh.
Local keys and runtime configuration are Git-ignored; existing keys are preserved.

Before the first run, enroll each device from the repo root on Linux/WSL:

```bash
ssh -F "$PWD/ssh_config" -o UserKnownHostsFile="$PWD/known_hosts" \
  -o StrictHostKeyChecking=ask -o BatchMode=no USERNAME@IPAddress
```

Use the exact `management_ip` value from your CSV (IP or hostname). Verify the
prompted fingerprint against device records before accepting, then exit SSH.
This stores the key locally. The playbook keeps strict verification enabled and
will reject unknown or changed keys; it does not automatically trust devices.

Run the normal playbook command above; no SSH config argument is needed.
Do not pass the previous `ansible_libssh_config_file` override: the playbook now
selects the rendered configuration. Algorithm support still depends on your
libssh build and controller crypto policy. Requires `ansible.netcommon` 5.1.0+.

## Output

JSON files: `output/<store_type>/<site>/<hostname>.json`.
Includes structured device facts and text output/status for each show command.
CLI text is stored inside JSON, not parsed into individual policy fields.
Command errors are recorded while collection continues; inspect `status` for
`collected`, `partial`, or `unsupported`. See [sample output](sample_output/store-a-sw01.json).

Output includes running configuration and may contain secrets. Files use mode
`0600`, are Git-ignored, and device output is hidden from Ansible console logs.
