"""
setup_cloud_sync.py — one-time cloud setup for PsyClick sync.

    python scripts/setup_cloud_sync.py [--owner-url postgresql://postgres.<ref>:<pw>@host:5432/postgres]

Run once by the project owner. It uses the owner connection (from
--owner-url, or "database_url" in %APPDATA%\\PsyClick\\config.json) to:

  * create the private schema "psyclick" (not exposed by Supabase's REST API)
    with the accounts and sessions tables the app syncs,
  * create the login role "psyclick_app", which can read and write only those
    two tables — not the rest of the project (normative data, auth, storage),
  * write that role's connection string to psyclick-secure/config.json as
    "sync_url". config.json is git-ignored; the installer ships it so every
    copy of the app can sync.

Running it again keeps the data and issues the role a new password.
"""

import argparse
import json
import os
import secrets
import sys
from urllib.parse import quote, urlparse, urlunparse

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
ROLE = "psyclick_app"

DDL = """
CREATE SCHEMA IF NOT EXISTS psyclick;
CREATE SEQUENCE IF NOT EXISTS psyclick.change_seq;
CREATE TABLE IF NOT EXISTS psyclick.accounts (
    clinician_id  integer PRIMARY KEY,
    account_uid   text NOT NULL UNIQUE,
    name          text NOT NULL,
    password_hash text NOT NULL,
    role          text NOT NULL,
    status        text NOT NULL,
    created_at    text,
    updated_at    text NOT NULL,
    server_seq    bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS psyclick.sessions (
    session_uid   text PRIMARY KEY,
    clinician_id  integer,
    data          jsonb NOT NULL,
    deleted_at    timestamptz,
    server_seq    bigint NOT NULL
);
CREATE INDEX IF NOT EXISTS accounts_seq ON psyclick.accounts (server_seq);
CREATE INDEX IF NOT EXISTS sessions_seq ON psyclick.sessions (server_seq);
"""


def owner_url(arg):
    if arg:
        return arg
    path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PsyClick", "config.json")
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)["database_url"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-url")
    args = ap.parse_args()
    import psycopg2  # type: ignore

    url = owner_url(args.owner_url)
    password = secrets.token_urlsafe(24)
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(DDL)
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,))
    verb = "ALTER" if cur.fetchone() else "CREATE"
    cur.execute(f"{verb} ROLE {ROLE} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD %s",
                (password,))
    cur.execute(f"""
        GRANT USAGE ON SCHEMA psyclick TO {ROLE};
        GRANT SELECT, INSERT, UPDATE ON psyclick.accounts, psyclick.sessions TO {ROLE};
        GRANT USAGE, SELECT ON SEQUENCE psyclick.change_seq TO {ROLE};
        REVOKE ALL ON SCHEMA psyclick FROM PUBLIC;
    """)
    conn.close()

    # Supabase's pooler addresses a role as <role>.<project-ref>
    u = urlparse(url)
    user = u.username or ""
    pool_user = f"{ROLE}.{user.split('.', 1)[1]}" if "." in user else ROLE
    netloc = f"{quote(pool_user)}:{quote(password)}@{u.hostname}" + (f":{u.port}" if u.port else "")
    sync_url = urlunparse(u._replace(netloc=netloc))

    # Prove the restricted role works and cannot see anything else
    check = psycopg2.connect(sync_url, connect_timeout=10)
    c = check.cursor()
    c.execute("SELECT count(*) FROM psyclick.accounts")
    c.execute("""SELECT count(*) FROM information_schema.table_privileges
                 WHERE grantee=%s AND table_schema <> 'psyclick'""", (ROLE,))
    outside = c.fetchone()[0]
    c.execute("SELECT has_schema_privilege(%s, 'public', 'USAGE')", (ROLE,))
    public_usage = c.fetchone()[0]
    check.close()

    cfg_path = os.path.join(APP_DIR, "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
    cfg["sync_url"] = sync_url
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)

    print("Cloud sync is set up.")
    print(f"  schema psyclick, role {ROLE} (table grants outside psyclick: {outside}; "
          f"public schema usage: {public_usage})")
    print(f"  connection written to {cfg_path} (git-ignored)")


if __name__ == "__main__":
    sys.exit(main())
