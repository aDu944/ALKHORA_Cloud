# Nextcloud Integration for ERPNext

This ERPNext app automatically creates a folder in your Nextcloud server whenever a new Opportunity is created in ERPNext.

## Features

- Automatically creates folders in Nextcloud when opportunities are created
- Manual folder creation button on Opportunity form
- Configurable folder naming with prefix support
- Secure credential management
- Error logging and notifications
- Easy enable/disable toggle

## Installation

1. **Install the app in your ERPNext bench:**

```bash
cd /path/to/your/bench
bench get-app https://github.com/aDu944/ALKHORA_Cloud.git
bench --site bms.alkhora.com install-app nextcloud_integration
```

2. **Migrate the site:**

```bash
bench --site bms.alkhora.com migrate
```

3. **Restart your bench:**

```bash
bench restart
```

## Configuration

1. After installation, go to **Nextcloud Integration > Nextcloud Settings** in ERPNext
2. Fill in the following details:
   - **Enable Nextcloud Integration**: Check this box to enable the integration
   - **Nextcloud URL**: `https://cloud.alkhora.com`
   - **Username**: Your Nextcloud username
   - **Password / App Password**: Your Nextcloud password or app-specific password (recommended)
   - **Folder Prefix**: Prefix for folder names (default: "Opportunity-")

### Creating an App Password in Nextcloud

For security, it's recommended to use an App Password instead of your main password:

1. Log in to Nextcloud (cloud.alkhora.com)
2. Go to **Settings > Security**
3. Scroll down to **Devices & sessions**
4. Click **Create new app password**
5. Give it a name (e.g., "ERPNext Integration")
6. Copy the generated password and use it in the ERPNext settings

## How It Works

### Automatic Folder Creation

When a new Opportunity is created in ERPNext:
1. The app detects the creation event
2. It generates a folder path using the format: `/ALKHORA/استيرادية {YEAR}/{Folder Prefix}{Opportunity Name}`
   - Example: `/ALKHORA/استيرادية 2026/Opportunity-OPP-00001`
   - The year is automatically set to the current year
3. It creates the folder (and parent directories if needed) in Nextcloud using the WebDAV API
4. A comment is added to the Opportunity with the folder link
5. Any errors are logged in ERPNext's error log

### Manual Folder Creation

You can also manually create a Nextcloud folder for any existing Opportunity:
1. Open the Opportunity document in ERPNext
2. Click the **"Create Nextcloud Folder"** button in the Actions menu
3. The app will create the folder and show a success message with a link to open it
4. A comment will be added to the Opportunity documenting the manual creation

This is useful if:
- The automatic creation failed
- The opportunity was created before the app was installed
- You need to recreate the folder

## Folder Structure

Folders are created in a specific path structure in your Nextcloud:
- Base Path: `/ALKHORA/استيرادية {YEAR}/`
- Full Format: `/ALKHORA/استيرادية {YEAR}/{Folder Prefix}{Opportunity Name}`
- Example: `/ALKHORA/استيرادية 2026/Opportunity-OPP-00001`

The year is automatically updated each year, so opportunities created in 2026 will be in `/ALKHORA/استيرادية 2026/`, and opportunities created in 2027 will be in `/ALKHORA/استيرادية 2027/`, etc.

## Troubleshooting

### Folder Not Created

1. Check **Nextcloud Integration > Nextcloud Settings** is enabled
2. Verify your Nextcloud URL, username, and password are correct
3. Check ERPNext error log: **Setup > Error Log**
4. Ensure your Nextcloud user has permission to create folders

### Authentication Errors

- Make sure you're using the correct username (not email if different)
- If using app password, ensure it was copied correctly
- Verify the Nextcloud URL is accessible from your ERPNext server

### Network Errors

- Ensure your ERPNext server can reach `https://cloud.alkhora.com`
- Check firewall rules allow outbound HTTPS connections
- Verify SSL certificate is valid

## Development

### Project Structure

```
nextcloud_integration/
├── nextcloud_integration/
│   ├── __init__.py
│   ├── hooks.py              # ERPNext hooks for Opportunity events + manual API
│   ├── nextcloud_api.py      # Nextcloud WebDAV API integration
│   ├── modules.txt
│   ├── public/
│   │   └── js/
│   │       └── nextcloud_integration.js  # Client-side JavaScript (backup)
│   └── doctype/
│       ├── nextcloud_settings/
│       │   ├── __init__.py
│       │   ├── nextcloud_settings.json
│       │   └── nextcloud_settings.py
│       └── opportunity_nextcloud_button/
│           ├── __init__.py
│           └── opportunity_nextcloud_button.json  # Client Script for button
├── setup.py
└── README.md
```

## License

MIT License

## Support

For issues or questions, please contact support@alkhora.com
