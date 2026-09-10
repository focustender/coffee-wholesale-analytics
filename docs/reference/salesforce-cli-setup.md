# Connecting a project to Salesforce (reusable setup)

This is a general-purpose runbook, not specific to this project. Copy it (and
`integrations/salesforce_client.py`) into any future project that needs real
Salesforce data access.

## Why this approach, not the claude.ai Salesforce Beta connector

The built-in "claude.ai Salesforce - Beta" MCP connector only exposes two
tools (`authenticate`, `complete_authentication`) and its OAuth flow
currently fails with `redirect_uri_mismatch` against a personal Developer
Edition org — a bug on the connector's side, not something fixable from the
Salesforce org's settings. This setup bypasses that connector entirely and
uses Salesforce's own CLI, which is the standard, actively-maintained way
developers connect scripts to Salesforce anyway.

## One-time setup

**1. Install the Salesforce CLI.**

If a plain `npm install -g @salesforce/cli` fails with `EACCES`, your global
npm directory is root-owned (usually from an old `sudo npm install -g`
somewhere in the past). Don't use `sudo` to force it — instead give npm a
user-owned global prefix:

```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
npm install -g @salesforce/cli
```

Add it to your shell so `sf` works in every terminal (already done in this
machine's `~/.zshrc`):

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
```

(The Homebrew cask `salesforce-cli` is currently disabled for failing
Gatekeeper checks — don't bother trying that route.)

**2. Log in to your org.**

```bash
sf org login web -a <alias> -d
```

- `-a <alias>` gives the connection a memorable name (e.g. `wholesale-dev`) —
  every future command references the org by this alias, not by username.
- `-d` sets it as your default org.
- No custom Connected App is needed for this. The `sf` CLI ships with its
  own pre-registered Salesforce Connected App (`clientId: PlatformCLI`) —
  creating your own Connected App only matters later if you want fully
  headless/unattended access (see "Going further" below).

**Run this in a real terminal window, not through an AI coding assistant's
`!`-prefixed shell passthrough.** That passthrough has its own command
timeout (around 2 minutes) and will move the login to a background process
before you've finished the browser consent screen, which then makes
Salesforce's own OAuth session time out. Just open Terminal/iTerm directly.

**3. Verify the connection.**

```bash
sf org list                                          # confirms it's connected
sf data query -q "SELECT Id, Name FROM Account LIMIT 5" --target-org <alias>
```

If `sf org list` shows nothing, the login didn't actually complete — rerun
step 2 and watch for a browser tab opening and a success message printed in
the terminal.

## Using it from a script

`sf org display --json` intentionally redacts the access token now (a
recent CLI change); the real token only comes from
`sf org auth show-access-token --json`, and instance URL comes from
`org display`. `integrations/salesforce_client.py` already handles both
calls and the split between them — import it directly rather than
re-deriving this:

```python
from integrations.salesforce_client import query, create, update

accounts = query("SELECT Id, Name FROM Account LIMIT 5", target_org="wholesale-dev")
create("Account", {"Name": "Test Account"}, target_org="wholesale-dev")
```

**Security note:** never ask an AI assistant to run
`sf org auth show-access-token` directly and read the output — that's a live
credential and shouldn't pass through a chat transcript. The client module
solves this by shelling out to the CLI *inside your own script's process*;
the token only ever exists in your local Python process, never in
conversation context. If an agent tries to fetch it directly, Claude Code's
own permission classifier blocks it — that block is correct behavior, not a
bug to work around.

## Current org

- Alias: `wholesale-dev`
- Org: "focustender studio" (Developer Edition)
- Instance: `orgfarm-b217050b30-dev-ed.develop.my.salesforce.com`

Developer Edition limits worth remembering before seeding data: 5MB data
storage (roughly a couple thousand records), 20MB file storage, 5,000 API
calls/24hr, 2 full user licenses.

## Going further (not set up yet)

If a future project needs unattended access (a script running on a schedule
with no human to click through a browser login), that requires:
1. Creating a real Connected App in Setup → App Manager with a self-signed
   certificate, for the JWT Bearer OAuth flow.
2. `sf org login jwt --username <user> --jwt-key-file <key> --client-id <id>`

That's meaningfully more setup (cert generation, Connected App
configuration, pre-authorizing the app in the org) and hasn't been needed
for anything built so far — don't build it preemptively.
