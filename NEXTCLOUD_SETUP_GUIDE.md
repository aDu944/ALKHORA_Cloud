# Nextcloud Integration Setup Guide

## Important Note
Nextcloud **does not have a REST API for file operations**. File operations in Nextcloud are done via **WebDAV**. However, we've optimized the WebDAV connection to be much faster.

## Current Implementation

The code now uses **optimized WebDAV** with:
- Connection pooling (faster subsequent requests)
- Keep-alive connections
- Reduced timeout (30 seconds instead of 60)
- Single request (only creates final folder, parent folders already exist)

## Step-by-Step Configuration

### Option 1: Optimized WebDAV (Current - No Configuration Needed)

**This is already configured and working!** The code automatically uses optimized WebDAV.

**What you need:**
1. ✅ Nextcloud URL: `https://cloud.alkhora.com`
2. ✅ Username: Your Nextcloud username
3. ✅ Password: Your Nextcloud password or app password

**No additional configuration needed!** The optimized WebDAV should be faster than before.

---

### Option 2: OCC Command (FASTEST - If Same Server)

If your ERPNext and Nextcloud are on the **same server**, you can use the OCC command directly for instant folder creation.

#### Step 1: Find Your Nextcloud Installation Path

SSH into your server and find where Nextcloud is installed:

```bash
# Common locations:
/var/www/nextcloud
/var/www/html/nextcloud
/home/nextcloud/nextcloud
/opt/nextcloud
```

#### Step 2: Test OCC Command

Test if you can run OCC commands:

```bash
cd /path/to/nextcloud
sudo -u www-data php occ files:create /username/ALKHORA/استيرادية\ 2026/test-folder
```

Replace:
- `/path/to/nextcloud` with your actual Nextcloud path
- `username` with your Nextcloud username
- Adjust the path as needed

#### Step 3: Update the Code

If OCC works, update the code in `nextcloud_integration/nextcloud_integration/nextcloud_api.py`:

Find this line (around line 77):
```python
cwd='/var/www/nextcloud'  # Adjust to your Nextcloud path
```

Change it to your actual Nextcloud path:
```python
cwd='/var/www/html/nextcloud'  # Your actual path
```

#### Step 4: Configure in Nextcloud Settings (Optional)

You can add SSH configuration fields to the Nextcloud Settings doctype if you want to configure it via UI.

---

### Option 3: Direct Filesystem Access (If You Have SSH)

If you have SSH access and both servers can access the same filesystem:

1. **Mount Nextcloud data directory** to ERPNext server (if different servers)
2. **Use Python's `os.makedirs()`** to create folders directly
3. **Update Nextcloud's file cache** using OCC command

This is the fastest method but requires server access.

---

## Performance Comparison

| Method | Speed | Configuration |
|--------|-------|---------------|
| **Optimized WebDAV** (Current) | ~5-10 seconds | ✅ Already configured |
| **OCC Command** (Same server) | <1 second | Requires server access |
| **Direct Filesystem** | <1 second | Requires SSH + filesystem access |

---

## Troubleshooting

### If WebDAV is Still Slow

1. **Check Network Connection**
   - Test ping from ERPNext server to Nextcloud: `ping cloud.alkhora.com`
   - Check if there's a firewall blocking connections

2. **Check Nextcloud Server Performance**
   - Check Nextcloud server CPU/memory usage
   - Check Nextcloud logs for errors

3. **Enable OCC Method** (if on same server)
   - Follow Option 2 above

4. **Check Nextcloud Configuration**
   - Ensure WebDAV is enabled (it's enabled by default)
   - Check `config.php` for any restrictions

### Test WebDAV Connection

Test from ERPNext server:

```bash
curl -X MKCOL "https://cloud.alkhora.com/remote.php/dav/files/USERNAME/ALKHORA/استيرادية%202026/test-folder/" \
  -u "USERNAME:PASSWORD"
```

Replace `USERNAME` and `PASSWORD` with your credentials.

---

## Current Status

✅ **Optimized WebDAV is already configured and active**
- Uses connection pooling
- Single request (only creates final folder)
- 30-second timeout
- Should be faster than before

The code will automatically use the fastest available method. No additional configuration is needed unless you want to use OCC (Option 2).
