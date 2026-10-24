# Sarce Nodes: more machines searching for one Sarce

A Sarce Node is a helper computer that runs Stockfish for your Sarce server ([ADR 0010](./adr/0010-paired-sarce-nodes.md)).
It leases one pending game at a time and searches every position with the server's own code. The server then
analyses that game from its cache in seconds. Nodes talk only to the **node gateway**, a small token-protected
server with nothing but node routes. They never touch the database.

## The setup this was built for

- **Server:** the laptop, `DESKTOP-K5KC76C`. On the Ethernet cable it is `192.168.137.1`, because Windows
  Internet Connection Sharing is on, so the desktop also gets internet through it.
- **Node:** the desktop, `desktop-fuer0cc` (`192.168.137.2`). i7-3770, 4 cores / 8 threads, 8 GB, and prone to
  power cuts.

Any network works the same way: point the node at the gateway's address. Keep the gateway on a private link (a
cable, your LAN, or a private overlay such as Tailscale), never on a public address.

## 1. On the server (once)

1. Check the server reads the engine cache: `POSITION_EVALS_ENABLED=true` in its `.env` (the Chaos Lens pass).
   With it off, the server does its own depth-based searches and ignores everything a node stores, so nodes wait
   and say why.
2. Put a pairing token in the server's `.env`: `NODE_TOKEN=<a long random string>`. Every node needs it.
3. Allow the gateway's port through the firewall, from the cable only. In PowerShell **as Administrator**:

   ```powershell
   New-NetFirewallRule -DisplayName "Sarce node gateway" -Direction Inbound -Protocol TCP -LocalPort 8002 `
     -RemoteAddress 192.168.137.0/24 -InterfaceAlias Ethernet -Action Allow
   ```

4. Run the gateway next to the API, bound to the cable's address only (the API stays on localhost):

   ```bash
   cd apps/api
   NODE_TOKEN=... uvicorn app.node_gateway:app --host 192.168.137.1 --port 8002
   ```

## 2. On the node (once)

In PowerShell **as Administrator** on the desktop, with the token in `$t`:

```powershell
$t = "<NODE_TOKEN>"
iwr http://192.168.137.1:8002/nodes/bundle.zip -Headers @{ "X-Sarce-Node" = $t } -OutFile $env:TEMP\sarce.zip
Expand-Archive $env:TEMP\sarce.zip $env:TEMP\sarce -Force
& $env:TEMP\sarce\node\install.ps1 -Server http://192.168.137.1:8002 -Token $t -Workers 4
```

The installer puts Python 3.12, the code and Stockfish 18 under `C:\SarceNode`. On an i7-3770 that's the
SSE4.1 build, the same version as the server, so it gives the same results. It then registers a **Sarce Node**
scheduled task that starts at boot, before anyone logs in. The log is `C:\SarceNode\node.log`.

**No internet on the node?** Build an offline kit on the server once: a folder with the Python 3.12.10 installer,
the node's wheels (`pip download -r apps/node/requirements-node.txt pip --only-binary=:all: --platform win_amd64
--python-version 3.12 -d wheels`), the Stockfish zip, and a `SHA256SUMS.txt` listing all of them. Share the folder
and add `-Kit \\SERVER\SarceNodeKit` to the install command. The installer checks every file against the sums and
installs with nothing from the internet. It keeps the wheels in `C:\SarceNode\wheels`, so updates stay offline
too. The node needs only four small packages: python-chess, pydantic, pydantic-settings, python-dotenv.

**Power cuts:** set the desktop's BIOS to *Restore on AC power loss → Power On*. After an outage, the desktop
boots, the task starts the node, and the node waits until the laptop's gateway answers. It then re-leases the
game it was on and carries on from the positions it already sent. A lease with no heartbeat for 5 minutes goes
back to the pool, so the laptop picks that game up if the desktop stays off.

**Workers:** 4 engines (one per physical core) leaves the desktop responsive. 6 uses hyper-threading for
roughly 15–20% more throughput. Change `WORKERS` in `C:\SarceNode\node.env` and restart the task.

## Updates

When the server's code or its search settings change, the node notices within 5 minutes and downloads the new
bundle from the gateway. It checks the bundle's signature (an HMAC with the pairing token), swaps it in only once
it's complete, and restarts. There's nothing to do on the desktop.

## Finishing games

The main API (with `NODE_TOKEN` set) analyses every 20 seconds the games nodes have finished searching. Every
position is cached by then, so each takes seconds, even with automatic sync off.

## Checking

- `GET /nodes/status` on the gateway (with the token) lists each node, its games in the last hour, and whether
  it's searching now.
- In the database, `node_leases` shows each node's current game and how many positions it has sent.
