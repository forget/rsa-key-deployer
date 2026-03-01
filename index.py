"""
Deploy an SSH public key to multiple remote servers in parallel.

Reads target servers from a JSON config file (servers.json) and appends
the local RSA public key to each server's authorized_keys file over SFTP.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from sys import exit
from json import load
from typing import Optional
from paramiko import AutoAddPolicy, SSHClient


def load_servers(config_path: Path) -> list[dict]:
    """Load server connection details from a JSON config file."""
    # read and parse the json array of server objects
    with config_path.open() as fh:
        return load(fh)


def load_public_key(key_path: Optional[Path] = None) -> str:
    """Read the local RSA public key from disk and return it as a single line."""
    # default to ~/.ssh/id_rsa.pub when no explicit path is given
    if key_path is None:
        key_path = Path.home() / ".ssh" / "id_rsa.pub"

    # strip surrounding whitespace and normalise line endings
    return key_path.read_text().strip().replace("\r", "").replace("\n", "")


def deploy(
    host: str,
    port: int,
    user: str,
    password: str,
    pub_key: str,
) -> tuple[str, bool, Optional[str]]:
    """
    Connect to a remote server and append pub_key to authorized_keys.

    Returns a tuple of (host, success, error_message).  error_message is
    None on success and a string description on failure.
    """
    
    try:
        # establish the ssh connection with a short timeout
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(host, port=port, username=user, password=password, timeout=10)

        sftp = client.open_sftp()

        # read existing authorized_keys content, tolerating a missing file
        try:
            with sftp.open("/root/.ssh/authorized_keys", "r") as fh:
                existing = fh.read().decode()
        except FileNotFoundError:
            existing = ""

        # deduplicate existing entries then append the new key if it is absent
        lines = [line.strip() for line in existing.splitlines() if line.strip()]
        if pub_key not in lines:
            lines.append(pub_key)

        # write the updated key list back to the remote file
        with sftp.open("/root/.ssh/authorized_keys", "w") as fh:
            fh.write("\n".join(lines) + "\n")

        sftp.close()

        # enforce correct permissions on the .ssh directory and key file
        client.exec_command("chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys")
        client.close()

        return host, True, None

    except Exception as exc:
        return host, False, str(exc)


def main() -> None:
    """Load config, read the public key, then deploy to all servers in parallel."""
    config_path = Path("servers.json")

    if not config_path.exists():
        print(f"config file not found: {config_path}")
        print("copy servers.example.json to servers.json and fill in your server details.")
        exit(1)

    servers = load_servers(config_path)
    pub_key = load_public_key()

    # submit one deploy task per server and collect results as they finish
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(deploy, s["host"], s["port"], s["user"], s["password"], pub_key)
            for s in servers
        ]

        for future in as_completed(futures):
            host, ok, err = future.result()
            status = "OK" if ok else "FAIL"
            suffix = f" - {err}" if err else ""
            print(f"[{status}] {host}{suffix}")


if __name__ == "__main__":
    main()
