# GovernAI Beginner Setup Guide
### Foundry Local + Qwen 3.5-2B + Kiji Privacy Proxy

This guide is written for beginners. Follow the steps in order. Do not skip any section. Replace placeholders such as `<WindowsUsername>` and `<LinuxUsername>` with your own usernames.

## Prerequisites

- Windows 10/11
- Internet connection
- VS Code
- Administrator access
- At least 10 GB free disk space

## Part 1 — Install WSL

1. Open PowerShell as Administrator.
2. Run:

   ```powershell
   wsl --install
   ```

3. Restart your computer if prompted.
4. Verify installation:

   ```powershell
   wsl -l -v
   ```

   Ubuntu should appear with VERSION 2.

## Part 2 — Install Ubuntu

If Ubuntu is missing:

```powershell
wsl --install -d Ubuntu
```

Launch Ubuntu:

```powershell
wsl
```

The first launch asks you to create:

- Linux username
- Linux password

Remember this password because `sudo` commands require it.

## Part 3 — Install Microsoft Foundry Local

Open a normal Windows PowerShell.

Install:

```powershell
winget install -e --id Microsoft.FoundryLocal
```

Close and reopen the terminal.

Verify:

```powershell
foundry --version
```

Start the service:

```powershell
foundry service start
```

Check status:

```powershell
foundry service status
```

## Part 4 — Download the Qwen Model

Download the project model:

```powershell
foundry model run qwen3.5-2b
```

Verify downloaded models:

```powershell
foundry model list
```

Keep Foundry Local installed. Future sessions only require:

```powershell
foundry service start
foundry model run qwen3.5-2b
```

## Part 5 — Clone Kiji

Open Ubuntu (WSL).

Run:

```bash
cd ~
git clone https://github.com/dataiku/kiji-proxy.git
cd kiji-proxy
ls
```

## Part 6 — Download the Kiji Package

Visit:

```
https://github.com/dataiku/kiji-proxy/releases
```

Download:

```
kiji-privacy-proxy_1.3.1_amd64.deb
```

Save it to the Windows Downloads folder.

## Part 7 — Install Kiji

Go to Downloads:

```bash
cd /mnt/c/Users/<WindowsUsername>/Downloads
```

Install:

```bash
sudo dpkg -i kiji-privacy-proxy_1.3.1_amd64.deb
```

If dependencies fail:

```bash
sudo apt-get install -f
```

Run the install command again.

## Part 8 — Verify Kiji

Check version:

```bash
kiji-proxy --version
```

Expected output:

```
Dataiku's Kiji Privacy Proxy version 1.3.1
```

## Part 9 — Start Kiji

Run:

```bash
kiji-proxy
```

The first run may show warnings such as:

- `.env` not found
- API keys not configured

These are normal.

> **IMPORTANT:** Leave this terminal running while testing your application.

## Part 10 — Run GovernAI

Open a **new** Windows PowerShell terminal.

Navigate to your project:

```powershell
cd <GovernAI Project Folder>
```

Run:

```powershell
streamlit run app.py
```

Do **NOT** run Streamlit from Ubuntu unless you have installed Python packages there.

## Application Flow

```
Streamlit UI
      ↓
Backend (llm_service.py)
      ↓
Kiji Privacy Proxy
      ↓
Foundry Local
      ↓
Qwen 3.5-2B
```

## Forgot WSL Password?

Open PowerShell:

```powershell
wsl -u root
```

Reset password:

```bash
passwd <LinuxUsername>
```

Exit:

```bash
exit
```

Launch Ubuntu again:

```powershell
wsl
```

## Common Problems

| Problem | Solution |
|---|---|
| `streamlit: command not found` | Run Streamlit from Windows PowerShell. |
| `sudo` password incorrect | Reset it using `wsl -u root` |
| `kiji-proxy` not found | Verify installation using `kiji-proxy --version` |
| Foundry command not found | Restart the terminal after installation. |

## Final Checklist

- [ ] WSL installed
- [ ] Ubuntu installed
- [ ] Linux username/password created
- [ ] Foundry Local installed
- [ ] Foundry service running
- [ ] Qwen 3.5-2B downloaded
- [ ] Kiji installed
- [ ] Kiji running
- [ ] Streamlit running
- [ ] Backend ready for Kiji integration
