# SSH + OCC Setup Guide (Fastest Method)

Since you have SSH access via Cloudflare and your servers are on different machines, you can use SSH to execute OCC commands directly on the Nextcloud server. This will be **MUCH faster** than WebDAV (typically <1 second vs 60 seconds).

**Important**: Your ERPNext is hosted on **Frappe Cloud** (`bms.alkhora.com`), which means you don't have direct shell access to the ERPNext server. This guide includes Frappe Cloud-specific instructions.

## Step-by-Step Configuration

### Step 0: Configure Cloudflare Access Policy (CRITICAL - Must Do First!)

**IMPORTANT**: If Cloudflare requires email authentication for SSH, automated commands will fail. You MUST configure Cloudflare Access to allow your ERPNext server IP to bypass email authentication.

#### Option A: IP-Based Bypass (Recommended for Automation)

1. **Find Your ERPNext Server's Public IP** (Frappe Cloud):
   
   Since you're on Frappe Cloud, you can't SSH into the server directly. **Important**: If `bms.alkhora.com` is behind Cloudflare (proxied), pinging it or checking DNS will show Cloudflare IPs, not the actual server IP.
   
   **Method 1: Use System Console** (Easiest - Recommended):
   - In ERPNext, go to **Setup > System Console**
   - Run this Python code:
     ```python
     import requests
     ip = requests.get('https://api.ipify.org').text
     print(f"ERPNext Server IP: {ip}")
     ```
   - This shows the actual outbound IP of your Frappe Cloud server
   - Note the IP address shown
   
   **Method 2: Contact Frappe Cloud Support**:
   - Contact Frappe Cloud support and ask for the public IP address of your site (`bms.alkhora.com`)
   - They can provide the exact IP that your ERPNext instance uses for outbound connections
   
   **Method 3: Use Cloudflare Access Logs**:
   - Go to Cloudflare Dashboard > Zero Trust > Access > Logs
   - Look for connection attempts from your ERPNext site to `ssh.alkhora.com`
   - The source IP in the logs is your ERPNext server IP
   - Note: You may need to trigger a connection first (try creating a folder)
   
   **Method 4: Check from Nextcloud Server**:
   - If you have access to Nextcloud server logs, check for connections from ERPNext
   - The IP making requests to Nextcloud is your ERPNext server IP
   - Check access logs or firewall logs on your Nextcloud server
   
   **Method 5: Check Domain DNS** (May not work if proxied):
   - If `bms.alkhora.com` is NOT proxied through Cloudflare (gray cloud), check your DNS records
   - The A record will show the server IP
   - **Note**: If it shows Cloudflare IPs (like `104.x.x.x` or `172.x.x.x`), the domain is proxied and this won't work
   
   **Why pinging won't work**:
   - If `bms.alkhora.com` is proxied through Cloudflare (orange cloud in DNS), `ping bms.alkhora.com` will return Cloudflare IPs
   - You need the actual Frappe Cloud server IP, not Cloudflare's proxy IPs
   
   Note this IP address - you'll need it for the Cloudflare Access policy.

2. **Configure Cloudflare Access Policy**:
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - Navigate to **Zero Trust** > **Access** > **Applications**
   - Find the application for `ssh.alkhora.com` (or create one if it doesn't exist)
   - Click on the application to edit policies
   - Add a new policy with these settings:
     - **Policy Name**: "ERPNext Server Bypass" (or similar)
     - **Action**: "Bypass" or "Allow"
     - **Include**: 
       - Select "IP Address"
       - Enter your ERPNext server's public IP (from step 1)
     - **Exclude**: Leave empty (or add any IPs you want to still require email auth)
   - Save the policy
   - **Important**: Make sure this policy is ordered BEFORE any policies that require email authentication

3. **Verify the Policy**:
   - The policy should allow connections from your ERPNext server IP without email prompt
   - Other IPs will still require email authentication (if you have other policies)

#### Option B: Service Token (Alternative - Requires cloudflared)

If IP-based bypass doesn't work or you need more control, you can use Cloudflare Service Tokens. **Note**: This requires `cloudflared` to be installed on the Frappe Cloud server.

1. **Create Service Token**:
   - Go to Cloudflare Dashboard > Zero Trust > Access > Service Tokens
   - Click "Create Service Token"
   - Give it a name (e.g., "ERPNext Integration")
   - Copy the **Client ID** and **Client Secret** (you'll need both)

2. **Configure Application to Accept Service Token**:
   - Go to Zero Trust > Access > Applications
   - Find or create application for `ssh.alkhora.com`
   - Add a policy that allows the service token:
     - **Policy Name**: "ERPNext Service Token" (or similar)
     - **Action**: "Allow"
     - **Include**: Select "Service Token" and choose your token
   - Save the policy

3. **Install cloudflared on Frappe Cloud** (if not already installed):
   - Contact Frappe Cloud support to install `cloudflared` on your site
   - Or check if it's already available in the system PATH using System Console:
     ```python
     import subprocess
     result = subprocess.run(['which', 'cloudflared'], capture_output=True, text=True)
     if result.returncode == 0:
         print(f"cloudflared found at: {result.stdout.strip()}")
     else:
         print("cloudflared not found. Contact Frappe Cloud support to install it.")
     ```
   - The code will automatically check for `cloudflared` and use it as a ProxyCommand
   - If `cloudflared` is not found, the code will return an error (use IP-based bypass instead)

4. **Configure in ERPNext Settings**:
   - Go to Nextcloud Settings
   - Enable "Use Cloudflare Service Token"
   - Enter the **Client ID** and **Client Secret** from step 1
   - The code will automatically use `cloudflared` as a proxy for SSH connections

**Recommendation**: 
- **Option A (IP-based bypass)** is simpler and doesn't require additional software
- **Option B (Service Token)** is more secure but requires `cloudflared` installation
- If you can't get the ERPNext server IP, use Option B

#### Test Cloudflare Access Configuration

**Note**: Since you're on Frappe Cloud, you can't test SSH directly from the ERPNext server. Instead:

1. **Test from your local machine** (if you have SSH access):
   ```bash
   # This should work WITHOUT email authentication prompt (if your IP is also allowed)
   ssh alkhora@ssh.alkhora.com "echo 'SSH works without email auth!'"
   ```

2. **Test via ERPNext** (after SSH keys are configured):
   - Configure SSH settings in ERPNext (Step 4)
   - Try creating a folder from an Opportunity
   - Check ERPNext Error Log for SSH connection errors
   - If it works, Cloudflare Access is configured correctly

3. **Verify in Cloudflare Dashboard**:
   - Go to Zero Trust > Access > Logs
   - Look for successful connections from your ERPNext server IP
   - If you see authentication failures, the policy may need adjustment

If you still get email authentication prompts, check:
- Policy order in Cloudflare Access (bypass policy must come first)
- ERPNext server IP is correct
- Policy is saved and active
- Wait 2-3 minutes for policy changes to propagate

### Step 1: Find Your Nextcloud Installation Path

SSH into your Nextcloud server via Cloudflare and find where Nextcloud is installed:

```bash
# Common locations:
/var/www/nextcloud
/var/www/html/nextcloud
/home/nextcloud/nextcloud
/opt/nextcloud
```

You can find it by running:
```bash
# Find Nextcloud installation
find / -name "occ" -type f 2>/dev/null | grep -v ".git"
```

This will show you the path. Note it down (e.g., `/var/www/nextcloud`).

### Step 2: Test OCC Command on Nextcloud Server

SSH into your Nextcloud server via Cloudflare and test the OCC command:

```bash
cd /var/www/nextcloud  # Use your actual path (you found: /var/www/nextcloud)
sudo -u www-data php occ files:create /ERPNext/ALKHORA/استيرادية\ 2026/test-folder
```

**Important**: The OCC command must run as `www-data` user (or `apache` on some systems). This is why we use `sudo -u www-data`.

Replace:
- `/var/www/nextcloud` with your actual Nextcloud path (you found: `/var/www/nextcloud`)
- `ERPNext` with your Nextcloud username
- Adjust the path as needed

If this works, you're ready to configure SSH in ERPNext!

**Note**: If you get a "sudo: no tty" error, you may need to configure passwordless sudo for the `alkhora` user. See troubleshooting section below.

### Step 3: Set Up SSH Key Authentication (Recommended)

For passwordless SSH access, set up SSH keys. **Since you're on Frappe Cloud, you need to generate the key using System Console**:

#### On ERPNext Server (Frappe Cloud):

1. **Generate SSH key using System Console**:
   
   **Option A: Use System Console** (if `subprocess` is allowed):
   - In ERPNext, go to **Setup > System Console**
   - Run this Python code to generate an SSH key:
     ```python
     import subprocess
     import os
     
     # Path for SSH key on Frappe Cloud
     key_path = "/home/frappe/frappe-bench/sites/.ssh/nextcloud_key"
     key_dir = os.path.dirname(key_path)
     
     # Create .ssh directory if it doesn't exist
     os.makedirs(key_dir, mode=0o700, exist_ok=True)
     
     # Generate SSH key (if it doesn't exist)
     if not os.path.exists(key_path):
         subprocess.run([
             'ssh-keygen', '-t', 'rsa', '-b', '4096',
             '-f', key_path, '-N', ''
         ], check=True)
         print(f"SSH key generated at: {key_path}")
     else:
         print(f"SSH key already exists at: {key_path}")
     
     # Display the public key
     pub_key_path = key_path + ".pub"
     if os.path.exists(pub_key_path):
         with open(pub_key_path, 'r') as f:
             pub_key = f.read().strip()
         print(f"\nPublic Key:\n{pub_key}\n")
         print("Copy this public key to add to Nextcloud server (Step 3.2)")
     else:
         print("Error: Public key not found")
     ```
   - Copy the public key that's displayed
   
   **Option B: Contact Frappe Cloud Support** (if System Console doesn't work):
   - Contact Frappe Cloud support and request them to:
     1. Generate an SSH key pair on your site
     2. Provide you with the public key
     3. Confirm the path to the private key (usually `/home/frappe/frappe-bench/sites/.ssh/nextcloud_key`)
   - This is the most reliable method if System Console restrictions prevent key generation

2. **Copy public key to Nextcloud server**:
   
   SSH into your Nextcloud server (`ssh.alkhora.com`) and add the public key:
   ```bash
   # On Nextcloud server:
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   echo "PASTE_PUBLIC_KEY_FROM_STEP_3.1_HERE" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
   
   **Important**: Make sure to paste the entire public key (starts with `ssh-rsa` and ends with a comment).

3. **Note the SSH key path for ERPNext settings**:
   - The key path on Frappe Cloud is: `/home/frappe/frappe-bench/sites/.ssh/nextcloud_key`
   - You'll need this path when configuring ERPNext settings (Step 4)

4. **Test SSH connection** (from your local machine or Nextcloud server):
   ```bash
   # This tests that the key works (you can't test from Frappe Cloud directly)
   # Test from your local machine if you have the private key, or skip this step
   # The real test will be when you try creating a folder from ERPNext
   ```

**Alternative**: If System Console doesn't work, you may need to:
- Contact Frappe Cloud support to generate the SSH key
- Or use a different authentication method (though SSH keys are recommended)

### Step 4: Configure in ERPNext

1. **Go to Nextcloud Integration > Nextcloud Settings** in ERPNext

2. **Fill in SSH Configuration**:
   - ✅ **Use SSH + OCC (Fastest Method)**: Check this box
   - **SSH Host**: Your Cloudflare tunnel hostname
     - Use: `ssh.alkhora.com` (your Cloudflare tunnel hostname)
     - **Important**: Make sure Cloudflare Access policy is configured (Step 0) before enabling this
   - **SSH Username**: Your SSH username
     - Use: `alkhora` (your SSH user)
   - **SSH Key Path** (Optional): Path to SSH private key on ERPNext server
     - **For Frappe Cloud**: Use `/home/frappe/frappe-bench/sites/.ssh/nextcloud_key`
     - Leave empty to use default SSH key (may not work on Frappe Cloud)
   - **Nextcloud Installation Path**: Full path to Nextcloud
     - Use: `/var/www/nextcloud` (you found this path)
   - **OCC User**: User to run OCC command as
     - Default: `www-data` (this is correct for most Nextcloud installations)
     - The SSH user (`alkhora`) must have sudo permissions to run commands as this user

3. **Configure Cloudflare Service Token** (Optional - Alternative to IP Bypass):
   - ✅ **Use Cloudflare Service Token**: Check this if you're using Service Token instead of IP bypass
   - **Cloudflare Client ID**: Enter the Client ID from your Service Token
   - **Cloudflare Client Secret**: Enter the Client Secret from your Service Token
   - **Note**: This requires `cloudflared` to be installed on Frappe Cloud server
   - If using Service Token, you don't need to configure IP bypass (Step 0, Option A)

3. **Save** the settings

### Step 5: Test the Connection

#### 5.1: Test SSH Connection (Verify Cloudflare Access Works)

**Note**: Since you're on Frappe Cloud, you can't test SSH directly from the ERPNext server. Use these methods to confirm the policy works:

**Method 1: Use "Test Connection" Button** (Easiest):
1. Go to **Nextcloud Integration > Nextcloud Settings** in ERPNext
2. Make sure SSH configuration is filled in:
   - ✅ Use SSH + OCC is enabled
   - SSH Host: `ssh.alkhora.com`
   - SSH Username: `alkhora`
   - SSH Key Path: `/home/frappe/frappe-bench/sites/.ssh/nextcloud_key` (or your key path)
   - Nextcloud Path: `/var/www/nextcloud`
3. Click the **"Test Connection"** button
4. **Expected Result**:
   - ✅ Success message: "Connection test successful" or similar
   - ❌ If you see "authentication" or "email" errors, the policy isn't working

**Method 2: Try Creating a Folder** (Real-world test):
1. Go to an Opportunity in ERPNext
2. Click **"Create Nextcloud Folder"** button
3. **Expected Result**:
   - ✅ Folder created instantly (<1 second)
   - ✅ Success notification appears
   - ✅ No errors in Error Log
   - ❌ If it fails with authentication errors, check the policy

**Method 3: Check Cloudflare Access Logs** (Most reliable):
1. Go to **Cloudflare Dashboard > Zero Trust > Access > Logs**
2. Filter for `ssh.alkhora.com` application
3. Look for connection attempts from IP `144.24.216.117` (your ERPNext server)
4. **Expected Result**:
   - ✅ Status: "Allow" or "Bypass" (green)
   - ✅ No email authentication prompts
   - ❌ If you see "Deny" or "Challenge", the policy isn't configured correctly

**Method 4: Check ERPNext Error Log**:
1. Go to **Setup > Error Log** in ERPNext
2. Look for recent errors related to SSH or Nextcloud
3. **Expected Result**:
   - ✅ No authentication errors
   - ✅ No "email" or "challenge" errors
   - ❌ If you see "Permission denied" or "authentication failed", check the policy

**Method 5: Test from Local Machine** (Optional - for verification):
```bash
# Test SSH connection (your local IP may still require email auth - that's OK)
ssh alkhora@ssh.alkhora.com "echo 'SSH connection test'"
```
- This verifies SSH works in general
- Note: Your local IP may still require email auth (that's expected)
- The important test is from ERPNext (IP: 144.24.216.117)

**Troubleshooting if policy doesn't work**:
1. ✅ Verify IP in policy: Should be `144.24.216.117` (your Frappe Cloud server IP)
2. ✅ Check policy order: Bypass policy must be BEFORE email auth policies
3. ✅ Wait 2-3 minutes: Policy changes can take time to propagate
4. ✅ Verify policy is saved and active in Cloudflare dashboard
5. ✅ Check Cloudflare Access Logs to see what's happening

#### 5.2: Test OCC Command via SSH

**Note**: Since you're on Frappe Cloud, you can't test OCC directly from the ERPNext server. Instead:

1. **Test via ERPNext Interface**:
   - Create a test Opportunity in ERPNext
   - Click "Create Nextcloud Folder" button
   - Check if folder is created instantly (<1 second)
   - If it works, OCC command is working correctly

2. **Test from your local machine** (if you have SSH access):
   ```bash
   # Test OCC command manually
   ssh alkhora@ssh.alkhora.com "cd /var/www/nextcloud && sudo -u www-data php occ files:create /ERPNext/test-folder-$(date +%s)"
   ```
   - This verifies OCC works in general
   - If this fails, check passwordless sudo configuration (see troubleshooting)

**Expected Result from ERPNext**:
- ✅ Folder created instantly (<1 second)
- ✅ No errors in Error Log
- ✅ Folder appears in Nextcloud
- ❌ If you get "sudo: no tty" error, configure passwordless sudo (see troubleshooting)

#### 5.3: Test from ERPNext Interface

1. Click the **"Test Connection"** button in Nextcloud Settings
2. Or try creating a folder manually from an Opportunity
3. Check the logs to see if it's using SSH+OCC
4. Verify folder appears in Nextcloud instantly (<1 second)

## Example Configuration

```
✅ Use SSH + OCC: Enabled
SSH Host: ssh.alkhora.com
SSH Username: alkhora
SSH Key Path: /home/frappe/.ssh/nextcloud_key (optional)
Nextcloud Path: /var/www/nextcloud
OCC User: www-data (default)
```

**Your specific configuration**:
- SSH Host: `ssh.alkhora.com` ✅ (your Cloudflare tunnel)
- SSH Username: `alkhora` ✅
- Nextcloud Path: `/var/www/nextcloud` ✅ (you found this)
- OCC User: `www-data` (default, should work)

**Before enabling SSH+OCC, ensure**:
- ✅ Cloudflare Access policy is configured (Step 0)
- ✅ SSH works without email prompt from ERPNext server
- ✅ SSH keys are set up
- ✅ Passwordless sudo is configured (if needed)

## Troubleshooting

### Cloudflare Access Email Authentication Issues

**Symptom**: SSH connection prompts for email authentication, blocking automated commands.

**Solution 1: Verify Cloudflare Access Policy**:
1. Go to Cloudflare Dashboard > Zero Trust > Access > Applications
2. Check that `ssh.alkhora.com` has a policy that allows your ERPNext server IP
3. Verify the policy action is "Bypass" or "Allow"
4. Check policy order - bypass policy must be BEFORE any email auth policies
5. Wait 2-3 minutes for policy changes to propagate

**Solution 2: Verify ERPNext Server IP** (Frappe Cloud):
- Since you can't SSH into Frappe Cloud server, use one of these methods:
  - Contact Frappe Cloud support to get your site's public IP
  - Check Cloudflare Access logs for connection attempts
  - Use System Console (see Step 0, Method 3)
- Compare the IP with what's in Cloudflare Access policy
- If different, update the policy with correct IP

**Solution 3: Test Policy** (Frappe Cloud):
- Since you can't SSH from ERPNext server directly, use these methods:
  
  **A. Test Connection Button**:
  - Go to Nextcloud Settings > Click "Test Connection"
  - If successful, policy is working
  - If authentication error, policy needs adjustment
  
  **B. Check Cloudflare Access Logs** (Most reliable):
  - Go to Cloudflare Dashboard > Zero Trust > Access > Logs
  - Filter for `ssh.alkhora.com`
  - Look for connections from IP `144.24.216.117` (your ERPNext server IP)
  - Status should be "Allow" or "Bypass" (not "Deny" or "Challenge")
  
  **C. Try Creating a Folder**:
  - Create a folder from an Opportunity
  - If it works instantly, policy is working
  - If it fails with auth errors, check the policy
  
  **D. Check ERPNext Error Log**:
  - Go to Setup > Error Log
  - Look for SSH authentication errors
  - No errors = policy is working
  
- Test from your local machine (optional):
  ```bash
  ssh alkhora@ssh.alkhora.com "echo 'test'"
  ```
  - Note: Your local IP may still require email auth (that's OK)
  - The important test is from ERPNext server (IP: 144.24.216.117)

**Solution 4: Check Cloudflare Tunnel Configuration**:
- Ensure SSH (port 22) is configured in Cloudflare tunnel
- Verify tunnel is active and running
- Check tunnel logs in Cloudflare dashboard

### SSH Connection Fails

1. **Test SSH from ERPNext** (Frappe Cloud):
   - Use the "Test Connection" button in Nextcloud Settings
   - Check ERPNext Error Log for specific error messages
   - Common errors: "Permission denied", "Host key verification failed", "Connection refused"

2. **Check SSH key path** (Frappe Cloud):
   - Ensure the path is correct: `/home/frappe/frappe-bench/sites/.ssh/nextcloud_key`
   - Verify the key exists (you can't check directly, but verify via System Console if needed)
   - If key doesn't exist, regenerate it using System Console (Step 3.1)

3. **Check SSH key permissions** (if you have access):
   - On Frappe Cloud, permissions should be set automatically
   - If you regenerate the key, ensure it's readable by the Frappe user

3. **Check Cloudflare tunnel**:
   - Ensure SSH port (22) is accessible via Cloudflare tunnel
   - Verify your Cloudflare tunnel is configured to forward SSH traffic
   - Test: `ssh alkhora@ssh.alkhora.com` should work
   - Check Cloudflare tunnel logs if connection fails
   - Verify tunnel is pointing to correct server: `<tunnel-id>.cfargotunnel.com`

### OCC Command Fails

1. **Test OCC command manually via Cloudflare**:
```bash
ssh -i ~/.ssh/nextcloud_key alkhora@ssh.alkhora.com "cd /var/www/nextcloud && sudo -u www-data php occ files:create /ERPNext/test-folder"
```

Replace:
- `ERPNext` with your Nextcloud username

2. **Check Nextcloud path**:
   - Ensure the path is correct (`/var/www/nextcloud` in your case)
   - Ensure the user has permission to run OCC

3. **Check PHP path**:
   - The code uses `php` command - ensure it's in PATH
   - Test: `ssh alkhora@ssh.alkhora.com "which php"` should show PHP path
   - Or update the code to use full path like `/usr/bin/php`

4. **Check Cloudflare Access is working**:
   - If OCC command fails with authentication error, Cloudflare Access policy may not be configured
   - Go back to Step 0 and configure the Access policy

### Permission Issues

If you get permission errors:

1. **Sudo Permission Required**:
   - The `alkhora` user must have sudo permissions to run commands as `www-data`
   - Test: `ssh alkhora@hostname "sudo -u www-data whoami"` should return `www-data`
   - If it asks for a password, configure passwordless sudo (see below)

2. **Configure Passwordless Sudo** (if needed):
   On Nextcloud server, run:
   ```bash
   sudo visudo
   ```
   Add this line (allows alkhora to run OCC as www-data without password):
   ```
   alkhora ALL=(www-data) NOPASSWD: /usr/bin/php /var/www/nextcloud/occ files:create *
   ```
   Or more broadly (less secure but simpler):
   ```
   alkhora ALL=(www-data) NOPASSWD: ALL
   ```

3. **Test Sudo Access**:
   ```bash
   ssh alkhora@<hostname> "sudo -u www-data php /var/www/nextcloud/occ --version"
   ```
   This should work without asking for a password.

4. **OCC User Configuration**:
   - The code automatically uses `sudo -u www-data` (or the user you specify in "OCC User" field)
   - If your system uses `apache` instead of `www-data`, change "OCC User" to `apache` in settings

## Performance Comparison

| Method | Speed | Setup |
|--------|-------|-------|
| **SSH + OCC** (via Cloudflare) | **<1 second** | ✅ Configured above |
| Optimized WebDAV | ~5-10 seconds | Already working |
| Standard WebDAV | ~60 seconds | Fallback |

## Security Notes

- ✅ SSH keys are more secure than passwords
- ✅ Use a dedicated SSH key for this integration
- ✅ Restrict SSH key permissions (use `command=` restriction in `authorized_keys` if possible)
- ✅ Keep SSH keys secure and don't commit them to git

## Cloudflare Tunnel Specific Notes

1. **SSH via Cloudflare Tunnel**:
   - Your SSH hostname: `ssh.alkhora.com` (CNAME to `<tunnel-id>.cfargotunnel.com`)
   - Cloudflare tunnels can forward SSH traffic (port 22)
   - Ensure your Cloudflare tunnel configuration includes SSH forwarding
   - The hostname you use to SSH is what you'll enter in "SSH Host"

2. **Cloudflare Access Email Authentication**:
   - **CRITICAL**: If Cloudflare requires email authentication, automated SSH will fail
   - You MUST configure Cloudflare Access policy (Step 0) to allow ERPNext server IP
   - Without this, folder creation will fail because it can't interact with email prompts
   - Test: SSH from ERPNext server should work WITHOUT email prompt

3. **Connection Speed**:
   - SSH via Cloudflare may add slight latency, but OCC execution is still instant
   - Total time should be <1 second (much faster than WebDAV's 60 seconds)
   - Cloudflare Access policy check adds minimal overhead

4. **Security**:
   - SSH keys are required for passwordless access
   - Cloudflare tunnel adds an extra layer of security
   - Cloudflare Access policy restricts access to specific IPs
   - Ensure SSH keys are properly secured

## Next Steps

1. **Complete the steps above**:
   - Get ERPNext server IP (contact Frappe Cloud support or use System Console)
   - Configure Cloudflare Access policy to allow ERPNext server IP
   - Generate SSH key using System Console (Step 3.1)
   - Copy key to Nextcloud server
   - Configure passwordless sudo on Nextcloud server (if needed)

2. **Push the code changes**:
   ```bash
   git add nextcloud_integration/ requirements.txt pyproject.toml
   git commit -m "Add SSH+OCC support with www-data user handling"
   git push origin main
   ```

3. **Install dependencies** (if not auto-installed):
   ```bash
   pip install paramiko
   ```

4. **Configure in ERPNext**:
   - Go to Nextcloud Settings
   - Enable SSH + OCC
   - Fill in all SSH configuration fields
   - Set OCC User to `www-data` (default)

5. **Test folder creation** - it should be instant (<1 second)!
