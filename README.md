# rsa-key-deployer

A Python script that deploys your local RSA public key to one or more remote servers in parallel over SSH. Once deployed, you can log in to each server without a password.

## Requirements

- Python 3.10+
- [paramiko](https://www.paramiko.org/)

Install dependencies:

```
pip install paramiko
```

## Setup

1. Copy the example config file and fill in your server details:

```
cp servers.example.json servers.json
```

2. Edit `servers.json` with the host, port, user, and password for each target server.

3. Make sure you have an RSA key pair at `~/.ssh/id_rsa.pub`. If you do not have one, generate it:

```
ssh-keygen -t rsa -b 4096
```

## Usage

```
python index.py
```

The script connects to all servers concurrently and appends your public key to `/root/.ssh/authorized_keys` on each one. Example output:

```
[OK] 192.168.1.10
[OK] 192.168.1.11
[FAIL] 192.168.1.12 - Authentication failed.
```

## Config format

`servers.json` is a JSON array where each object describes one server:

```json
[
    {"host": "192.168.1.10", "port": 22, "user": "root", "password": "yourpassword"},
    {"host": "192.168.1.11", "port": 22, "user": "root", "password": "yourpassword"}
]
```

This file is listed in `.gitignore` and will not be committed to the repository.

## Notes

- The script is idempotent. Running it multiple times will not duplicate the key.
- After writing the key, permissions are set to `700` on `~/.ssh` and `600` on `authorized_keys`.
- Deployment tasks run in parallel using a thread pool, so large server lists complete quickly.
