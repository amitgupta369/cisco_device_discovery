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

`store_type` accepts any value; there is no allowed-value validation. Blank, whitespace-only, or
missing `site` and `store_type` values each default to `other`; if both are blank,
output is saved under `output/other/other/`. Blank or omitted `device_type` defaults
to `IOS`. Label NX-OS devices `NXOS`; non-IOS types are recorded as `unsupported`
and skipped. The OS is not detected automatically.

## Run

```bash
ansible-playbook playbooks/collect.yml -u YOUR_USERNAME --ask-pass
```

For enable mode, append `--become --become-method enable --ask-become-pass`.
The same TACACS username/password is used for all input devices.
Supply the username with `-u` and enter the TACACS password at `SSH password:`.
Automatic SSH-key lookup is disabled in `ansible.cfg` for this password workflow.
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
The audit disables connection-rate testing and waits 10 seconds before login.
For devices with longer SSH throttling windows, use `-e ssh_post_audit_delay=30`.
The audit has a 90-second overall limit and a 10-second socket timeout. If an
`ASYNC FAILED` message specifically reports a timeout, increase the overall limit
with `-e ssh_audit_timeout=180`. Other async failures need their exact error checked.
Failed audits are recorded as `unknown` and skipped; see `ssh_assessment.error`
in the device JSON for details.

| SSH class | Meaning | Default action |
| --- | --- | --- |
| `modern` | The device offers up-to-date SSH connection methods recognized by our checks, so collection can proceed. | Collect |
| `legacy` | The device needs an older SSH connection method, so collection is skipped by default. | Skip |
| `very_old` | The device needs a severely outdated SSH connection method, so collection is blocked. | Skip |
| `unknown` | The check could not determine the device's SSH compatibility, so collection is skipped. | Skip |

Classification uses the best offered option per family, not simply the presence
of an old algorithm. It describes SSH compatibility, not hardware age, the actual
negotiated algorithms, or full security compliance. AEAD ciphers need no separate
MAC. Skipped devices get JSON with the assessment and do not run login/show tasks.
To permit legacy devices, set `ssh_allowed_classes: [modern, legacy]` in the
playbook. Very old and unknown devices remain blocked.

JSON files: `output/<store_type>/<site>/<hostname>.json`. Special characters in
store-type folder names are URL-encoded; JSON and HTML retain the trimmed CSV label.
Includes structured device facts and text output/status for each show command.
CLI text is stored inside JSON, not parsed into individual policy fields.
Command errors are recorded while collection continues; inspect `status` for
`collected`, `partial`, `skipped`, or `unsupported`. See [sample output](sample_output/store-a-sw01.json).

Output includes running configuration and may contain secrets. Files use mode
`0600`, are Git-ignored, and device output is hidden from Ansible console logs.

## HTML report

Generate a standalone summary from existing JSON files (no device connections):

```bash
ansible-playbook playbooks/report.yml
```

Open `output/report.html`. Includes device details, SSH class, collection status,
and command names/statuses. Full command output and raw errors are excluded.
To use another input folder, append `-e output_root=/absolute/path/to/output`.
To choose the HTML destination, append `-e report_file=/absolute/path/report.html`.

Click an inventory hostname in the report to open its device JSON. To view on
Windows, copy the entire `output` folder from RHEL, preserving this structure:

```text
output/
  report.html
  type_a/STORE-A/store-a-sw01.json
  other/other/store-other-sw01.json
```

Links are relative, so the Windows drive/folder can differ. Copying only the HTML
breaks the device links. With a custom `report_file`, preserve its position relative
to the JSON folders too. Browsers may display or download JSON; linked files contain
the full device output, unlike the HTML summary.

## CSV batches

Split the input into batches of 100 devices, preserving headers and row order:

```bash
python3 scripts/split_csv.py input/devices.csv --batch-size 100 --output-dir input/batches
```

Run one batch using the existing playbook:

```bash
ansible-playbook playbooks/collect.yml -u agupta10 --ask-pass --forks 10 \
  -e "csv_input=$PWD/input/batches/batch_001.csv"
```

The script assumes valid CSV input and a positive batch size. It only splits CSV;
it does not execute batches. Use a new output directory for each run.
The final batch may contain fewer devices.

## Separate SSH connectivity test

Tests modern, legacy, and very old Cisco IOS devices using `network_cli` with
libssh, independently of `collect.yml`. Run from the repo root on the Linux controller:

```bash
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/ssh_connectivity.yml -u agupta10 --ask-pass
```

Use `-u` for the shared username and `--ask-pass` to prompt once for the shared
SSH/TACACS password, just like `collect.yml`. For unattended runs, supply
`ansible_user` and `ansible_password` through an Ansible Vault extra-vars file
(`-e @credentials.yml --ask-vault-pass`) instead of `-u` and `--ask-pass`.
Use `-e csv_input=/path/to/batch.csv` for a batch.

The playbook audits each device and writes its offered algorithms, strongest first,
to `connectivity_output/ssh_configs/`. Libssh uses these per-device settings;
old classes are attempted. Algorithms unavailable in libssh or blocked by RHEL
crypto policy can still fail. An inconclusive assessment tries libssh defaults.

Success means login **and the IOS CLI prompt** work. The test sends a newline;
Ansible may also send terminal setup commands. It does not run the discovery command list
or include command output in the report. A successful OpenSSH login alone does not
guarantee this test succeeds.

The repo's `ansible.cfg` enables libssh host-key auto-add and disables searching
for private keys. New keys go to repo-local `known_hosts`; changed keys are rejected.
Keep host-key checking enabled. Connections run one at a time (`serial: 1`).

To reuse a matching saved collection assessment instead of rescanning:

```bash
ansible-playbook playbooks/ssh_connectivity.yml -u agupta10 --ask-pass -e reuse_assessment=true
```

Fresh scans are the default. Each run overwrites `connectivity_output/report.html`
and `results.json`. Use `-e connectivity_output=/path/to/run` to retain separate
runs. Copy the standalone HTML to Windows to view it. Results show SSH class,
success/failure, a sanitized reason, and configured algorithms, without credentials
or SSH transcripts. Configured algorithms are not proof of the negotiated algorithm.

## Paramiko comparison test

This separate playbook tests the same CSV using `network_cli` with Paramiko.
It leaves the libssh playbook and system crypto policy unchanged. Install Paramiko
in the Python environment that runs Ansible, then run from the repository root:

```bash
python -m pip install "paramiko>=3.5.1,<4"
ANSIBLE_CONFIG="$PWD/ansible-paramiko.cfg" ansible-playbook \
  playbooks/ssh_connectivity_paramiko.yml -u agupta10 --ask-pass \
  -e "csv_input=$PWD/input/devices.csv"
```

Start with a one-device CSV. Reports are written to
`paramiko_connectivity_output/report.html` and `results.json`.
Success requires login and an IOS CLI prompt. The assessment is informational:
Paramiko uses its own algorithm defaults, not the generated libssh configurations.
Legacy and very old devices are attempted, but unavailable algorithms still fail.

Unlike the libssh test, the native Paramiko plugin uses the controller user's
`~/.ssh/known_hosts`, not the repo-local file. The separate config accepts new keys
and retains host-key checking; changed keys fail. Tests are sequential.

Use a separate test virtual environment if this would downgrade an installed Paramiko.
The 3.x constraint retains DSA support for very old devices; it does not guarantee
compatibility with every legacy cipher. Do not downgrade the system installation. Paramiko support is deprecated
and depends on your installed Ansible/ansible.netcommon versions. If the connection
plugin is missing, use a separate virtual environment with a compatible Ansible
release rather than downgrading the working collection environment. Older Paramiko
is not a general fix for RHEL crypto restrictions. Devices offering only `ssh-dss`
need special consideration because Paramiko 4 removed DSA support.
