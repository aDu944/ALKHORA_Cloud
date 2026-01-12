import requests
import frappe
from requests.auth import HTTPBasicAuth
from urllib.parse import quote, urljoin

def create_nextcloud_folder(nextcloud_url, username, password, folder_path):
	"""
	Create a folder in Nextcloud using WebDAV API
	Creates parent directories if they don't exist
	
	Args:
		nextcloud_url: Base URL of Nextcloud (e.g., https://cloud.alkhora.com)
		username: Nextcloud username
		password: Nextcloud password or app password
		folder_path: Full path of the folder to create (e.g., "ALKHORA/استيرادية 2026/Opportunity-OPP-00001")
	
	Returns:
		dict: {"success": bool, "folder_path": str, "error": str}
	"""
	try:
		# Ensure URL doesn't end with slash
		nextcloud_url = nextcloud_url.rstrip('/')
		
		# Split path into components and create parent directories first
		path_parts = [p for p in folder_path.split('/') if p]
		encoded_parts = []
		
		# Create each parent directory if it doesn't exist
		for i, part in enumerate(path_parts):
			# URL encode each segment separately
			encoded_part = quote(part, safe='')
			encoded_parts.append(encoded_part)
			
			# Build the encoded path up to this point
			encoded_path = "/".join(encoded_parts)
			webdav_url = f"{nextcloud_url}/remote.php/dav/files/{username}/{encoded_path}/"
			
			# Make MKCOL request (WebDAV method to create a collection/folder)
			response = requests.request(
				"MKCOL",
				webdav_url,
				auth=HTTPBasicAuth(username, password),
				headers={
					"Content-Type": "application/xml"
				},
				timeout=30
			)
			
			# Check if folder was created successfully or already exists
			if response.status_code not in [201, 405, 207]:
				# 201 = created, 405 = already exists, 207 = multi-status (some created)
				# If it's the final folder and it's not 201/405, it's an error
				if i == len(path_parts) - 1:
					error_msg = response.text
					if response.status_code == 401:
						error_msg = "Authentication failed. Please check username and password."
					elif response.status_code == 403:
						error_msg = "Permission denied. User doesn't have permission to create folders."
					elif response.status_code == 404:
						error_msg = "User not found or path invalid."
					
					return {
						"success": False,
						"error": f"HTTP {response.status_code}: {error_msg}",
						"status_code": response.status_code
					}
		
		# All folders created successfully
		# Build the display URL (for the files app)
		display_path = "/" + "/".join(path_parts)
		encoded_display_path = quote(display_path, safe='')
		
		return {
			"success": True,
			"folder_path": f"{nextcloud_url}/apps/files/?dir={encoded_display_path}",
			"webdav_path": display_path,
			"message": "Folder created successfully"
		}
			
	except requests.exceptions.RequestException as e:
		return {
			"success": False,
			"error": f"Network error: {str(e)}"
		}
	except Exception as e:
		return {
			"success": False,
			"error": f"Unexpected error: {str(e)}"
		}
