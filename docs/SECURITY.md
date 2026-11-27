# Operational security for Inspector Rabbit

Inspector Rabbit talks directly to the services and people you investigate.
Without precautions, **every lookup carries your real IP address**. This guide
covers the three layers the app supports, from least to most effort.

| Layer | Hides your IP | Protects your machine from hostile files | Effort |
|-------|---------------|------------------------------------------|--------|
| 1. Tor / proxy + kill switch (built in) | ✅ | ❌ | 2 min |
| 2. Hardened container (`run-container.sh`) | ✅ (built-in Tor) | ✅ (partly) | 10 min |
| 3. Dedicated VM | ✅ | ✅ (strongly) | 30 min |

---

## 1. Built-in Tor / proxy routing

**Settings → Network Privacy**

| Option | What it does |
|--------|--------------|
| Tor service (127.0.0.1:9050) | Every HTTP(S) request goes through Tor (`sudo apt install tor`) |
| Tor Browser (127.0.0.1:9150) | Uses a running Tor Browser's SOCKS port instead |
| Custom proxy | Any `socks5h://`, `socks4://` or `http://` proxy (a VPN's SOCKS endpoint, for example) |
| Kill switch | If the proxy is down, **every lookup is refused** instead of falling back to your real IP |
| Allow direct traffic when proxied | Off by default. Ping, traceroute, SMTP mailbox probes, port-43 WHOIS and local DNSBL queries cannot be proxied, so they are blocked unless you tick this |

While proxied:

* DNS lookups use DNS-over-HTTPS **through the proxy** (Cloudflare, then Google), so the
  local resolver and your ISP never see the names you investigate.
* SSL certificate grabs, banner grabs and port checks are tunnelled through SOCKS.
* `socks5://` is automatically upgraded to `socks5h://` so hostnames are resolved by the proxy.

Use **Test connection** after saving. It reports the exit IP and whether it is a Tor exit.

Expect some sources to block Tor exit nodes (Bing, Reddit, some breach APIs).
The app reports those as *blocked*. It never reports them as *not found*.

### Tailscale

Tailscale on its own does **not** hide your IP: it only links your own devices.
Only an **exit node** changes your public IP:

* a **Mullvad exit node** (Tailscale add-on) gives you VPN-grade exit IPs
* an exit node on **another device you own** only moves the traffic to that device's IP

Tor and Tailscale coexist. With a Mullvad exit node active, Tor's own traffic
leaves through Mullvad, so your ISP doesn't see you using Tor.

The DNS Leak Monitor recognises MagicDNS (`100.100.100.100`, `fd7a:115c:a1e0::53`).
Connection Guard treats tailnet peers (`100.64.0.0/10`) as your own network.

---

## 2. Hardened container

```bash
sudo apt install podman        # rootless containers (Docker also works)
./run-container.sh             # builds on first run, then launches the GUI
```

What the container enforces:

* rootless Podman, so the container's "root" is your unprivileged user
* app runs as uid 1000 with **all Linux capabilities dropped** and `no-new-privileges`
* **read-only root filesystem**, with `/tmp` as a size-limited tmpfs
* your home directory is **not mounted**. Settings, cases and evidence live in
  the private volume `inspector-rabbit-data`. Only `~/InspectorRabbit-exports` is
  shared (save reports there).
* a **container-private Tor client** starts automatically. On first run the app
  defaults to Tor with the kill switch on. Set `IR_TOR=0` to disable it.
* **Wayland only** by default. X11 forwarding gives the container access to the
  whole display, including keystrokes typed into other windows, so it requires
  explicitly setting `IR_ALLOW_X11=1`.

Limitations:

* The counter-surveillance modules (Traffic Monitor, Connection Guard, Scan
  Detector, DNS Leak Monitor) only see the **container's** network inside a
  container. Run those natively.
* A container shares the host kernel. A kernel exploit escapes it. For strong
  isolation, use a VM.

Manage the data volume:

```bash
podman volume inspect inspector-rabbit-data
podman volume rm inspector-rabbit-data      # wipe all settings/cases/evidence
```

---

## 3. Dedicated VM (strongest)

1. Install a hypervisor: `sudo apt install virt-manager` (KVM/QEMU) or VirtualBox.
2. Create a VM from a fresh Ubuntu/Debian ISO with 2 vCPU, 4 GB RAM and 25 GB disk.
   Use **NAT networking** and do not enable shared folders or clipboard sharing.
3. Inside the VM, install a VPN client (or Tor) and enable its kill switch.
   Then install Inspector Rabbit from the `.deb` or from source.
4. In Inspector Rabbit, set **Settings → Network Privacy → Tor + kill switch**.
5. Take a clean snapshot. Revert to it after investigations that touched
   untrusted files.
6. Move reports out with a one-way method (export, then copy over a
   temporarily enabled shared folder, or `scp` from the host).

For maximum anonymity, use **Whonix** (all VM traffic is forced through a Tor
gateway VM), or **Qubes OS** with a disposable Whonix qube.

---

## Local data hygiene

* `~/.inspector_rabbit_settings.json` holds your API keys. The app writes it
  atomically with `0600` permissions and re-tightens permissions if they were loosened.
* The settings file, cases, evidence folders and exported reports are gitignored. Never commit them.
* Evidence captures include `SHA256SUMS`. Verify them with `sha256sum -c SHA256SUMS`.
* Generated HTML reports escape all scraped content, so a hostile page title cannot
  inject script into your report.
