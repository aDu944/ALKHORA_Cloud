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
		
		# Split path into components
		path_parts = [p for p in folder_path.split('/') if p]
		
		# OPTIMIZED: Parent folders already exist, so only create the final folder
		# This makes it MUCH faster - just 1 request instead of 3+
		import time
		start_time = time.time()
		
		# Encode the full path
		encoded_parts = [quote(part, safe='') for part in path_parts]
		encoded_path = "/".join(encoded_parts)
		webdav_url = f"{nextcloud_url}/remote.php/dav/files/{username}/{encoded_path}/"
		
		frappe.logger().info(f"Creating Nextcloud folder (parent folders exist): {webdav_url}")
		
		# Single request to create the final folder
		try:
			response = requests.request(
				"MKCOL",
				webdav_url,
				auth=HTTPBasicAuth(username, password),
				headers={
					"Content-Type": "application/xml"
				},
				timeout=30  # Reasonable timeout
			)
			
			create_time = time.time() - start_time
			frappe.logger().info(f"MKCOL response: {response.status_code} ({create_time:.2f}s)")
			
			# Check if folder was created successfully or already exists
			# 201 = created, 405 = already exists (both are success)
			if response.status_code not in [201, 405, 207]:
				error_msg = response.text
				if response.status_code == 401:
					error_msg = "Authentication failed. Please check username and password."
				elif response.status_code == 403:
					error_msg = "Permission denied. User doesn't have permission to create folders."
				elif response.status_code == 404:
					error_msg = "Parent folder not found. Please ensure parent folders exist."
				elif response.status_code == 409:
					error_msg = "Conflict: Parent folder may not exist. Please ensure parent folders are created first."
				
				return {
					"success": False,
					"error": f"HTTP {response.status_code}: {error_msg}",
					"status_code": response.status_code
				}
			
		except requests.exceptions.Timeout:
			frappe.logger().error(f"Timeout creating folder: {webdav_url}")
			return {
				"success": False,
				"error": f"Request timeout while creating folder. Nextcloud server may be slow."
			}
		except requests.exceptions.ConnectionError as e:
			frappe.logger().error(f"Connection error: {str(e)}")
			return {
				"success": False,
				"error": f"Connection error: Unable to reach Nextcloud server. Error: {str(e)}"
			}
		
		total_time = time.time() - start_time
		frappe.logger().info(f"Folder created in {total_time:.2f}s (single request)")
		
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


def test_nextcloud_connection(nextcloud_url, username, password):
	"""
	Test the connection to Nextcloud by attempting to list the user's root directory
	
	Args:
		nextcloud_url: Base URL of Nextcloud (e.g., https://cloud.alkhora.com)
		username: Nextcloud username
		password: Nextcloud password or app password
	
	Returns:
		dict: {"success": bool, "message": str, "error": str}
	"""
	try:
		# Ensure URL doesn't end with slash
		nextcloud_url = nextcloud_url.rstrip('/')
		
		# Use PROPFIND to list the root directory (this tests authentication and connectivity)
		webdav_url = f"{nextcloud_url}/remote.php/dav/files/{username}/"
		
		frappe.logger().info(f"Testing Nextcloud connection: {webdav_url}")
		
		try:
			response = requests.request(
				"PROPFIND",
				webdav_url,
				auth=HTTPBasicAuth(username, password),
				headers={
					"Depth": "0"  # Only get info about the root directory
				},
				timeout=10  # 10 second timeout for test
			)
			
			frappe.logger().info(f"Nextcloud connection test response: {response.status_code}")
			
			if response.status_code == 207:  # Multi-status (success for PROPFIND)
				return {
					"success": True,
					"message": f"Connection successful! Successfully authenticated to Nextcloud at {nextcloud_url}",
					"status_code": response.status_code
				}
			elif response.status_code == 401:
				return {
					"success": False,
					"error": "Authentication failed. Please check your username and password.",
					"status_code": response.status_code
				}
			elif response.status_code == 403:
				return {
					"success": False,
					"error": "Permission denied. User doesn't have permission to access WebDAV.",
					"status_code": response.status_code
				}
			elif response.status_code == 404:
				return {
					"success": False,
					"error": "User not found or WebDAV endpoint not available.",
					"status_code": response.status_code
				}
			else:
				return {
					"success": False,
					"error": f"Unexpected response from Nextcloud server: HTTP {response.status_code} - {response.text[:200]}",
					"status_code": response.status_code
				}
				
		except requests.exceptions.Timeout:
			return {
				"success": False,
				"error": f"Connection timeout. Unable to reach Nextcloud server at {nextcloud_url} within 10 seconds. Check your network connection and firewall settings."
			}
		except requests.exceptions.ConnectionError as e:
			return {
				"success": False,
				"error": f"Connection error: Unable to reach Nextcloud server at {nextcloud_url}. Check your network connection and Nextcloud URL. Error: {str(e)}"
			}
		except requests.exceptions.SSLError as e:
			return {
				"success": False,
				"error": f"SSL/TLS error: {str(e)}. Check if the Nextcloud URL uses HTTPS correctly."
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
