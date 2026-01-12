import requests
import frappe
from requests.auth import HTTPBasicAuth
from urllib.parse import quote, urljoin
import subprocess
import os

def create_nextcloud_folder(nextcloud_url, username, password, folder_path, use_rest_api=True, ssh_host=None, ssh_user=None, use_service_token=False, cf_client_id=None, cf_client_secret=None):
	"""
	Create a folder in Nextcloud using the fastest available method
	
	Priority:
	1. SSH + OCC command (fastest, if SSH access available)
	2. REST API (faster than WebDAV)
	3. WebDAV (fallback)
	
	Args:
		nextcloud_url: Base URL of Nextcloud (e.g., https://cloud.alkhora.com)
		username: Nextcloud username
		password: Nextcloud password or app password
		folder_path: Full path of the folder to create (e.g., "ALKHORA/استيرادية 2026/Opportunity-OPP-00001")
		use_rest_api: Use REST API instead of WebDAV (default: True, faster)
		ssh_host: SSH host for direct server access (optional, fastest method)
		ssh_user: SSH username (optional)
		use_service_token: Use Cloudflare Service Token for authentication (optional)
		cf_client_id: Cloudflare Service Token Client ID (optional)
		cf_client_secret: Cloudflare Service Token Client Secret (optional)
	
	Returns:
		dict: {"success": bool, "folder_path": str, "error": str}
	"""
	# Try SSH + OCC first (fastest method)
	if ssh_host:
		return _create_via_ssh_occ(ssh_host, ssh_user, username, folder_path, nextcloud_url, None, None, "www-data", use_service_token, cf_client_id, cf_client_secret)
	
	# Note: Nextcloud doesn't have a direct REST API for file operations
	# File operations are done via WebDAV, but we can optimize it
	# Try optimized WebDAV with connection pooling (faster than standard WebDAV)
	return _create_via_webdav_optimized(nextcloud_url, username, password, folder_path)


def _create_via_ssh_occ(ssh_host, ssh_user, nextcloud_user, folder_path, nextcloud_url, nextcloud_path=None, ssh_key_path=None, occ_user="www-data", use_service_token=False, cf_client_id=None, cf_client_secret=None):
	"""
	Create folder using SSH + Nextcloud OCC command (FASTEST method)
	Executes OCC command remotely via SSH
	
	Args:
		occ_user: User to run OCC command as (usually www-data or apache)
	"""
	try:
		import time
		start_time = time.time()
		
		# Build the OCC command
		# Format: occ files:create /username/path/to/folder
		full_path = f"/{nextcloud_user}/{folder_path}"
		
		# Escape the path for shell (handle special characters and spaces)
		escaped_path = full_path.replace("'", "'\\''")
		
		# Build the full command to run on remote server
		# Use sudo -u to run as the specified user (usually www-data)
		if nextcloud_path:
			occ_cmd = f"cd {nextcloud_path} && sudo -u {occ_user} php occ files:create '{escaped_path}'"
		else:
			occ_cmd = f"sudo -u {occ_user} php occ files:create '{escaped_path}'"
		
		frappe.logger().info(f"Creating folder via SSH+OCC: {full_path} on {ssh_host}")
		
		# Build SSH command
		ssh_options = []
		
		# Add SSH key if provided
		if ssh_key_path and os.path.exists(ssh_key_path):
			ssh_options.extend(['-i', ssh_key_path])
		
		# Add Cloudflare Service Token ProxyCommand if enabled
		if use_service_token and cf_client_id and cf_client_secret:
			# Check if cloudflared is available
			try:
				cloudflared_check = subprocess.run(
					['which', 'cloudflared'],
					capture_output=True,
					text=True,
					timeout=2
				)
				if cloudflared_check.returncode != 0:
					frappe.logger().error("cloudflared not found in PATH. Service Token authentication requires cloudflared to be installed.")
					return {
						"success": False,
						"error": "cloudflared is not installed. Please install cloudflared or use IP-based bypass instead."
					}
			except Exception as e:
				frappe.logger().warning(f"Could not check for cloudflared: {str(e)}. Proceeding anyway...")
			
			# Use cloudflared as ProxyCommand for Service Token authentication
			proxy_cmd = (
				f"cloudflared access ssh "
				f"--hostname {ssh_host} "
				f"--id {cf_client_id} "
				f"--secret {cf_client_secret}"
			)
			ssh_options.extend(['-o', f'ProxyCommand={proxy_cmd}'])
			frappe.logger().info(f"Using Cloudflare Service Token for SSH connection via cloudflared")
		else:
			# Standard SSH options (for IP-based bypass or direct connection)
			ssh_options.extend([
				'-o', 'StrictHostKeyChecking=no',  # Accept new host keys
				'-o', 'UserKnownHostsFile=/dev/null',  # Don't save host keys
				'-o', 'ConnectTimeout=10',  # 10 second connection timeout
				'-o', 'BatchMode=yes'  # Don't prompt for password
			])
		
		# Build full SSH command
		ssh_target = f"{ssh_user}@{ssh_host}" if ssh_user else f"{nextcloud_user}@{ssh_host}"
		ssh_cmd = ['ssh'] + ssh_options + [ssh_target, occ_cmd]
		
		# Execute SSH command
		try:
			result = subprocess.run(
				ssh_cmd,
				capture_output=True,
				text=True,
				timeout=10,  # 10 second timeout for the whole operation
				check=False  # Don't raise exception on non-zero exit
			)
			
			elapsed = time.time() - start_time
			
			if result.returncode == 0:
				frappe.logger().info(f"Folder created via SSH+OCC in {elapsed:.2f}s")
				
				path_parts = [p for p in folder_path.split('/') if p]
				display_path = "/" + "/".join(path_parts)
				encoded_display_path = quote(display_path, safe='')
				
				return {
					"success": True,
					"folder_path": f"{nextcloud_url}/apps/files/?dir={encoded_display_path}",
					"webdav_path": display_path,
					"message": f"Folder created successfully via SSH+OCC in {elapsed:.2f}s"
				}
			else:
				error_output = result.stderr or result.stdout
				frappe.logger().error(f"SSH+OCC failed: {error_output}")
				return {
					"success": False,
					"error": f"SSH+OCC command failed: {error_output}"
				}
				
		except subprocess.TimeoutExpired:
			frappe.logger().error("SSH+OCC command timed out")
			return {
				"success": False,
				"error": "SSH+OCC command timed out after 10 seconds"
			}
		except Exception as e:
			frappe.logger().error(f"SSH execution error: {str(e)}")
			return {
				"success": False,
				"error": f"SSH execution error: {str(e)}"
			}
		
	except Exception as e:
		frappe.logger().error(f"SSH+OCC error: {str(e)}")
		return {
			"success": False,
			"error": f"SSH+OCC error: {str(e)}"
		}


def _create_via_rest_api(nextcloud_url, username, password, folder_path):
	"""
	Create folder using Nextcloud REST API (FASTER than WebDAV)
	Uses the Files API endpoint
	"""
	try:
		import time
		start_time = time.time()
		
		# Nextcloud REST API endpoint for creating files/folders
		# Format: POST /ocs/v2.php/apps/files/api/v1/files/{path}
		nextcloud_url = nextcloud_url.rstrip('/')
		
		# Encode the path
		path_parts = [p for p in folder_path.split('/') if p]
		encoded_parts = [quote(part, safe='') for part in path_parts]
		encoded_path = "/".join(encoded_parts)
		
		# REST API endpoint (faster than WebDAV)
		api_url = f"{nextcloud_url}/ocs/v2.php/apps/files/api/v1/files/{username}/{encoded_path}"
		
		frappe.logger().info(f"Creating folder via REST API: {api_url}")
		
		# Make POST request to create folder
		response = requests.post(
			api_url,
			auth=HTTPBasicAuth(username, password),
			headers={
				"OCS-APIRequest": "true",
				"Content-Type": "application/json"
			},
			json={},  # Empty body for folder creation
			timeout=10  # Much shorter timeout - REST API is faster
		)
		
		elapsed = time.time() - start_time
		frappe.logger().info(f"REST API response: {response.status_code} ({elapsed:.2f}s)")
		
		# REST API returns 201 for created, 200 for success
		if response.status_code in [200, 201]:
			display_path = "/" + "/".join(path_parts)
			encoded_display_path = quote(display_path, safe='')
			
			return {
				"success": True,
				"folder_path": f"{nextcloud_url}/apps/files/?dir={encoded_display_path}",
				"webdav_path": display_path,
				"message": "Folder created successfully via REST API"
			}
		else:
			# If REST API doesn't work, return error to try WebDAV
			error_msg = response.text
			if response.status_code == 404:
				error_msg = "Parent folder not found in REST API"
			elif response.status_code == 403:
				error_msg = "Permission denied in REST API"
			
			return {
				"success": False,
				"error": f"REST API HTTP {response.status_code}: {error_msg}"
			}
			
	except requests.exceptions.Timeout:
		return {
			"success": False,
			"error": "REST API timeout"
		}
	except Exception as e:
		frappe.logger().error(f"REST API error: {str(e)}")
		return {
			"success": False,
			"error": f"REST API error: {str(e)}"
		}


def _create_via_webdav_optimized(nextcloud_url, username, password, folder_path):
	"""
	Create folder using optimized WebDAV with connection pooling (FASTER)
	Uses requests.Session for connection reuse and better performance
	"""
	try:
		import time
		start_time = time.time()
		
		# Ensure URL doesn't end with slash
		nextcloud_url = nextcloud_url.rstrip('/')
		
		# Split path into components
		path_parts = [p for p in folder_path.split('/') if p]
		
		# OPTIMIZED: Parent folders already exist, so only create the final folder
		encoded_parts = [quote(part, safe='') for part in path_parts]
		encoded_path = "/".join(encoded_parts)
		webdav_url = f"{nextcloud_url}/remote.php/dav/files/{username}/{encoded_path}/"
		
		frappe.logger().info(f"Creating Nextcloud folder via optimized WebDAV: {webdav_url}")
		
		# Use Session for connection pooling (faster)
		session = requests.Session()
		session.auth = HTTPBasicAuth(username, password)
		
		try:
			# Single request to create the final folder
			response = session.request(
				"MKCOL",
				webdav_url,
				headers={
					"Content-Type": "application/xml",
					"Connection": "keep-alive"  # Keep connection alive for faster subsequent requests
				},
				timeout=30,  # Reduced timeout - should be faster
				stream=False,
				verify=True
			)
			
			create_time = time.time() - start_time
			frappe.logger().info(f"MKCOL response: {response.status_code} ({create_time:.2f}s)")
			
			# Check if folder was created successfully or already exists
			if response.status_code not in [201, 405, 207]:
				error_msg = response.text
				if response.status_code == 401:
					error_msg = "Authentication failed. Please check username and password."
				elif response.status_code == 403:
					error_msg = "Permission denied. User doesn't have permission to create folders."
				elif response.status_code == 404:
					error_msg = "Parent folder not found. Please ensure parent folders exist."
				elif response.status_code == 409:
					error_msg = "Conflict: Parent folder may not exist."
				
				return {
					"success": False,
					"error": f"HTTP {response.status_code}: {error_msg}",
					"status_code": response.status_code
				}
			
			total_time = time.time() - start_time
			frappe.logger().info(f"Folder created via optimized WebDAV in {total_time:.2f}s")
			
			# Build the display URL
			display_path = "/" + "/".join(path_parts)
			encoded_display_path = quote(display_path, safe='')
			
			return {
				"success": True,
				"folder_path": f"{nextcloud_url}/apps/files/?dir={encoded_display_path}",
				"webdav_path": display_path,
				"message": "Folder created successfully via optimized WebDAV"
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
		finally:
			session.close()
			
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
