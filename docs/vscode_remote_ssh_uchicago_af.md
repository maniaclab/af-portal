
# Using VS Code Remote - SSH to Connect to UChicago AF (`login.af.uchicago.edu`)

This guide will walk you through installing the **Remote - SSH** plugin in **Visual Studio Code (VS Code)** and using it to connect to UChicago AF's login node (`login.af.uchicago.edu`).

---

## 🧩 Step 1: Install Remote - SSH Extension in VS Code

1. Open **VS Code**.
2. Go to the **Extensions** view:
   - Click on the square icon on the left sidebar (or press `Ctrl+Shift+X`).
3. In the search bar, type: `Remote - SSH`.
4. Locate the extension developed by **Microsoft** and click **Install**.

Alternatively, you can install it directly via this link:  
👉 [Remote - SSH Extension on Marketplace](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)

---

## 🔐 Step 2: Set Up SSH Access to UChicago AF

Before connecting, make sure:
- You have an account on **UChicago AF**.
- You can SSH into `login.af.uchicago.edu` from a terminal using:  
  ```bash
  ssh yourusername@login.af.uchicago.edu
  ```
- You have your **SSH private key** available locally (if using key-based authentication).

---

## ⚙️ Step 3: Configure SSH in VS Code

1. Press `F1` or `Ctrl+Shift+P` to open the **Command Palette**.
2. Type: `Remote-SSH: Open SSH Configuration File...`
3. Select the file to edit, typically:
   - `~/.ssh/config` (recommended)

4. Add the following block (replace `yourusername` with your actual AF username):

   ```ssh
   Host uchicago-af
       HostName login.af.uchicago.edu
       User yourusername
       IdentityFile ~/.ssh/id_rsa  # Adjust if you're using a different key file
       ForwardAgent yes
   ```

> 💡 If you use password authentication, you can omit the `IdentityFile` line.

---

## 🔌 Step 4: Connect to UChicago AF via Remote - SSH

1. Press `F1` or `Ctrl+Shift+P`, then type:
   ```
   Remote-SSH: Connect to Host...
   ```
2. Select `uchicago-af` (or the alias you used in the `Host` line of your SSH config).
3. VS Code will establish a connection and install the necessary server components on the remote host.
4. Once connected, you'll be in a **remote VS Code environment**, working directly on `login.af.uchicago.edu`.

---

## 📁 Step 5: Open or Create Remote Projects

- Once connected, you can:
  - Use **File → Open Folder** to open a directory on the remote machine.
  - Open terminals, run scripts, and edit files as if you're working locally.

---

## 🛠 Troubleshooting Tips

- **Connection fails**: Try testing the SSH command manually in a terminal.
- **Key permissions issue**: Run `chmod 600 ~/.ssh/id_rsa`
- **Host key verification failed**: Try deleting old entries from `~/.ssh/known_hosts` if the remote host has changed.

---

## ✅ Summary

| Step | Description |
|------|-------------|
| 1 | Install **Remote - SSH** extension |
| 2 | Ensure SSH access to `login.af.uchicago.edu` |
| 3 | Configure `~/.ssh/config` |
| 4 | Connect via **Remote-SSH: Connect to Host** |
| 5 | Work on files and terminals remotely |

---

Enjoy a seamless coding experience on UChicago AF using the power of **VS Code Remote Development**! 🚀
