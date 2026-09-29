# Cisco Device Discovery

Read-only Ansible collection of Cisco IOS/IOS XE device information as JSON.
All tasks and the 14 show commands are in `playbooks/collect.yml`; no roles.

## Setup

Run from this folder on Linux/WSL with Python 3.12+ and SSH access to devices.

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

Unknown host keys are automatically accepted on first connection and saved to
repo-local `known_hosts`. This is enabled by `host_key_auto_add = True` under
`[libssh_connection]` in `ansible.cfg`. Existing-key verification stays enabled;
changed keys are not automatically replaced. No manual SSH enrollment is needed.

Run from the repo root so Ansible loads this `ansible.cfg`. To require manual
verification for new devices, set `host_key_auto_add = False` again. This setting
controls Ansible/libssh; standalone `ssh` still uses strict checking in `ssh_config`.

Run the normal playbook command above; no SSH config argument is needed.
Do not pass the previous `ansible_libssh_config_file` override: the playbook now
selects the rendered configuration. Algorithm support still depends on your
libssh build and controller crypto policy. Requires `ansible.netcommon` 5.1.0+.

## Output

Before login, `ssh-audit` inspects the device's advertised SSH algorithms without
credentials. Install the updated dependencies with `pip install -r requirements.txt`.
All classification rules are in `playbooks/collect.yml`.

| SSH class | Meaning | Default action |
| --- | --- | --- |
| `modern` | Each family offers a modern option (SHA-2/curve KEX, modern host signature, AES-CTR/GCM or ChaCha20, SHA-2 MAC or AEAD) | Collect |
| `legacy` | At least one family needs SHA-1, `ssh-rsa`, or AES-CBC | Skip |
| `very_old` | At least one family needs group1, DSA, 3DES/RC4, or obsolete MACs | Skip |
| `unknown` | Scan failed or an algorithm family cannot be classified | Skip |

Classification uses the best offered option per family, not simply the presence
of an old algorithm. It describes SSH compatibility, not hardware age, the actual
negotiated algorithms, or full security compliance. AEAD ciphers need no separate
MAC. Skipped devices get JSON with the assessment and do not run login/show tasks.
To permit legacy devices, set `ssh_allowed_classes: [modern, legacy]` in the
playbook. Very old and unknown devices remain blocked.

JSON files: `output/<store_type>/<site>/<hostname>.json`.
Includes structured device facts and text output/status for each show command.
CLI text is stored inside JSON, not parsed into individual policy fields.
Command errors are recorded while collection continues; inspect `status` for
`collected`, `partial`, `skipped`, or `unsupported`. See [sample output](sample_output/store-a-sw01.json).

Output includes running configuration and may contain secrets. Files use mode
`0600`, are Git-ignored, and device output is hidden from Ansible console logs.
