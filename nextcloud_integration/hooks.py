from frappe import _
import frappe
from datetime import datetime
from nextcloud_integration.nextcloud_integration.nextcloud_api import create_nextcloud_folder, test_nextcloud_connection

app_name = "nextcloud_integration"
app_title = "Nextcloud Integration"
app_publisher = "ALKHORA"
app_description = "Automatically create Nextcloud folders for new opportunities"
app_email = "support@alkhora.com"
app_license = "MIT"

# Hooks
doc_events = {
	"Opportunity": {
		"after_insert": "nextcloud_integration.hooks.create_opportunity_folder"
	}
}

# Alternative: You can also use the API function directly
# doc_events = {
# 	"Opportunity": {
# 		"after_insert": "nextcloud_integration.api.create_nextcloud_folder_on_opportunity"
#  }
# }


def create_opportunity_folder(doc, method):
	"""
	Create a folder in Nextcloud when a new Opportunity is created
	Runs in background to avoid blocking the opportunity creation
	"""
	try:
		# Check if auto-create is enabled
		settings_name = _get_settings_name()
		if settings_name:
			nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
			if not nextcloud_config.enabled or not nextcloud_config.is_feature_enabled("auto_create"):
				frappe.logger().info(f"Auto-create folders is disabled. Skipping folder creation for Opportunity {doc.name}")
				return
		
		# Enqueue the folder creation to run in background
		frappe.enqueue(
			method=_create_nextcloud_folder_background,
			queue="default",
			timeout=None,  # No timeout
			job_name=f"create_nextcloud_folder_{doc.name}",
			opportunity_name=doc.name,
			is_async=True
		)
		frappe.logger().info(f"Enqueued Nextcloud folder creation for Opportunity {doc.name}")
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Integration Error",
			message=f"Error enqueueing Nextcloud folder creation for Opportunity {doc.name}: {str(e)}"
		)

def _get_settings_name():
	"""Helper function to get Nextcloud Settings document name"""
	settings_name = None
	# Method 1: Try known document name first (most reliable)
	if frappe.db.exists("Nextcloud Settings", "ck82qg4l2r"):
		settings_name = "ck82qg4l2r"
	# Method 2: Try Single DocType name
	elif frappe.db.exists("Nextcloud Settings", "Nextcloud Settings"):
		settings_name = "Nextcloud Settings"
	# Method 3: Try to get any existing document
	else:
		existing = frappe.get_all("Nextcloud Settings", limit=1)
		if existing:
			settings_name = existing[0].name
	return settings_name

def _create_nextcloud_folder_background(opportunity_name, retry_count=0):
	"""
	Background job function to create Nextcloud folder
	This runs in the background without blocking the user
	"""
	try:
		# Validate that the opportunity exists
		if not frappe.db.exists("Opportunity", opportunity_name):
			if getattr(frappe.local, "nextcloud_config", None):
				if frappe.local.nextcloud_config.is_feature_enabled("log_events"):
					frappe.log_error(
						title="Nextcloud Folder Creation Error",
						message=f"Opportunity {opportunity_name} not found"
					)
			return
		
		# Get Nextcloud configuration
		settings_name = _get_settings_name()
		
		if not settings_name:
			frappe.log_error(
				title="Nextcloud Folder Creation Error",
				message="Nextcloud Settings not configured"
			)
			return
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		frappe.local.nextcloud_config = nextcloud_config  # Store for helper functions
		
		if not nextcloud_config.enabled:
			if nextcloud_config.is_feature_enabled("log_events"):
				frappe.logger().info("Nextcloud integration is disabled")
			return
		
		# Generate folder path: /ALKHORA/استيرادية {YEAR}/Opportunity-{name}
		current_year = datetime.now().year
		folder_prefix = nextcloud_config.folder_prefix or "Opportunity-"
		
		# Build the full path
		base_path = f"ALKHORA/استيرادية {current_year}"
		folder_name = f"{folder_prefix}{opportunity_name}"
		full_path = f"{base_path}/{folder_name}"
		
		# Create folder in Nextcloud using fastest available method
		frappe.logger().info(f"Creating Nextcloud folder for opportunity {opportunity_name}: {full_path}")
		
		# Check if SSH is enabled and configured
		use_ssh = getattr(nextcloud_config, 'use_ssh', False) and \
		          getattr(nextcloud_config, 'ssh_host', None) and \
		          getattr(nextcloud_config, 'ssh_user', None)
		
		if use_ssh:
			# Use SSH + OCC (fastest method)
			ssh_host = nextcloud_config.ssh_host
			ssh_user = nextcloud_config.ssh_user
			ssh_key_path = getattr(nextcloud_config, 'ssh_key_path', None) or None
			nextcloud_path = getattr(nextcloud_config, 'nextcloud_path', None) or None
			occ_user = getattr(nextcloud_config, 'occ_user', None) or "www-data"  # Default to www-data
			
			# Check if Service Token is enabled
			use_service_token = getattr(nextcloud_config, 'use_service_token', False)
			cf_client_id = getattr(nextcloud_config, 'cf_client_id', None) or None
			cf_client_secret = None
			if use_service_token and cf_client_id:
				cf_client_secret = nextcloud_config.get_password("cf_client_secret") if hasattr(nextcloud_config, 'cf_client_secret') else None
			
			from nextcloud_integration.nextcloud_integration.nextcloud_api import _create_via_ssh_occ
			result = _create_via_ssh_occ(
				ssh_host=ssh_host,
				ssh_user=ssh_user,
				nextcloud_user=nextcloud_config.username,
				folder_path=full_path,
				nextcloud_url=nextcloud_config.nextcloud_url,
				nextcloud_path=nextcloud_path,
				ssh_key_path=ssh_key_path,
				occ_user=occ_user,
				use_service_token=use_service_token,
				cf_client_id=cf_client_id,
				cf_client_secret=cf_client_secret
			)
		else:
			# Use optimized WebDAV
			result = create_nextcloud_folder(
				nextcloud_url=nextcloud_config.nextcloud_url,
				username=nextcloud_config.username,
				password=nextcloud_config.get_password("password"),
				folder_path=full_path,
				use_rest_api=False  # Use optimized WebDAV
			)
		
		if result.get("success"):
			# Add comment if feature is enabled
			if nextcloud_config.is_feature_enabled("add_comments"):
				try:
					opportunity_doc = frappe.get_doc("Opportunity", opportunity_name)
					opportunity_doc.add_comment(
						comment_type="Info",
						text=f"Nextcloud folder created: {result.get('folder_path')}"
					)
				except Exception as e:
					if nextcloud_config.is_feature_enabled("log_events"):
						frappe.logger().error(f"Failed to add comment to opportunity: {str(e)}")
			
			# Send notification if feature is enabled
			if nextcloud_config.is_feature_enabled("send_notifications"):
				frappe.publish_realtime(
					event="nextcloud_folder_created",
					message={
						"success": True,
						"message": f"Nextcloud folder created successfully for {opportunity_name}",
						"folder_path": result.get("folder_path")
					},
					user=frappe.session.user
				)
			
			# Log event if feature is enabled
			if nextcloud_config.is_feature_enabled("log_events"):
				frappe.logger().info(f"Successfully created Nextcloud folder: {result.get('folder_path')} for Opportunity: {opportunity_name}")
		else:
			error_msg = result.get("error", "Failed to create folder")
			
			# Log error if feature is enabled
			if nextcloud_config.is_feature_enabled("log_events"):
				frappe.log_error(
					title="Nextcloud Folder Creation Error",
					message=f"Failed to create folder for {opportunity_name}: {error_msg}"
				)
			
			# Try auto-retry if enabled
			max_retries = nextcloud_config.get_max_retries()
			if nextcloud_config.is_feature_enabled("auto_retry") and retry_count < max_retries:
				frappe.logger().info(f"Retrying folder creation for {opportunity_name} (attempt {retry_count + 1}/{max_retries})")
				frappe.enqueue(
					method=_create_nextcloud_folder_background,
					queue="default",
					timeout=None,
					job_name=f"create_nextcloud_folder_{opportunity_name}_retry_{retry_count + 1}",
					opportunity_name=opportunity_name,
					retry_count=retry_count + 1,
					is_async=True,
					at_front=True
				)
				return  # Don't send error notification yet, wait for retry
			
			# Send error notification if feature is enabled
			if nextcloud_config.is_feature_enabled("send_notifications"):
				frappe.publish_realtime(
					event="nextcloud_folder_created",
					message={
						"success": False,
						"error": f"Failed to create Nextcloud folder: {error_msg}"
					},
					user=frappe.session.user
				)
			
	except Exception as e:
		# Get config for feature checks
		nextcloud_config = getattr(frappe.local, "nextcloud_config", None)
		if not nextcloud_config:
			settings_name = _get_settings_name()
			if settings_name:
				nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		# Log error if feature is enabled
		if not nextcloud_config or nextcloud_config.is_feature_enabled("log_events"):
			frappe.log_error(
				title="Nextcloud Folder Creation Error",
				message=f"Error creating Nextcloud folder for Opportunity {opportunity_name}: {str(e)}"
			)
		
		# Try auto-retry if enabled
		if nextcloud_config and nextcloud_config.is_feature_enabled("auto_retry"):
			max_retries = nextcloud_config.get_max_retries()
			if retry_count < max_retries:
				frappe.logger().info(f"Retrying folder creation for {opportunity_name} after exception (attempt {retry_count + 1}/{max_retries})")
				frappe.enqueue(
					method=_create_nextcloud_folder_background,
					queue="default",
					timeout=None,
					job_name=f"create_nextcloud_folder_{opportunity_name}_retry_{retry_count + 1}",
					opportunity_name=opportunity_name,
					retry_count=retry_count + 1,
					is_async=True,
					at_front=True
				)
				return  # Don't send error notification yet, wait for retry
		
		# Send error notification if feature is enabled
		if not nextcloud_config or nextcloud_config.is_feature_enabled("send_notifications"):
			frappe.publish_realtime(
				event="nextcloud_folder_created",
				message={
					"success": False,
					"error": f"An error occurred: {str(e)}"
				},
				user=frappe.session.user
			)


@frappe.whitelist()
def create_nextcloud_folder_manual(opportunity_name):
	"""
	Manually create a Nextcloud folder for an Opportunity
	This enqueues the job in the background and returns immediately
	"""
	try:
		# Quick validation
		if not frappe.db.exists("Opportunity", opportunity_name):
			return {
				"success": False,
				"error": f"Opportunity {opportunity_name} not found"
			}
		
		# Get Nextcloud configuration (quick lookup)
		settings_name = _get_settings_name()
		
		if not settings_name:
			return {
				"success": False,
				"error": "Nextcloud Settings not configured."
			}
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		if not nextcloud_config.enabled:
			return {
				"success": False,
				"error": "Nextcloud integration is disabled."
			}
		
		# Enqueue immediately and return - don't wait
		# Use at_front=True to prioritize this job
		frappe.enqueue(
			method=_create_nextcloud_folder_background,
			queue="default",
			timeout=None,
			job_name=f"create_nextcloud_folder_{opportunity_name}",
			opportunity_name=opportunity_name,
			is_async=True,
			now=False,  # Don't wait, just enqueue
			at_front=True  # Process this job first
		)
		
		# Return immediately - don't wait for job
		# This should return in < 1 second
		return {
			"success": True,
			"message": "Folder creation started in background."
		}
		
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Manual Folder Creation Error",
			message=f"Error enqueueing Nextcloud folder creation: {str(e)}"
		)
		return {
			"success": False,
			"error": f"Error: {str(e)}"
		}


@frappe.whitelist()
def test_nextcloud_connection_manual():
	"""
	Test the connection to Nextcloud using the current settings
	"""
	try:
		# Get Nextcloud configuration
		settings_name = _get_settings_name()
		
		if not settings_name:
			return {
				"success": False,
				"error": "Nextcloud Settings not configured. Please configure it first."
			}
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		# Validate required fields
		if not nextcloud_config.nextcloud_url:
			return {
				"success": False,
				"error": "Nextcloud URL is required. Please enter a Nextcloud URL."
			}
		
		if not nextcloud_config.username:
			return {
				"success": False,
				"error": "Username is required. Please enter a Nextcloud username."
			}
		
		if not nextcloud_config.get_password("password"):
			return {
				"success": False,
				"error": "Password is required. Please enter a Nextcloud password or app password."
			}
		
		# Test the connection
		frappe.logger().info(f"Testing Nextcloud connection for {nextcloud_config.nextcloud_url}")
		result = test_nextcloud_connection(
			nextcloud_url=nextcloud_config.nextcloud_url,
			username=nextcloud_config.username,
			password=nextcloud_config.get_password("password")
		)
		
		frappe.logger().info(f"Nextcloud connection test result: {result}")
		
		return result
		
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Connection Test Error",
			message=f"Error testing Nextcloud connection: {str(e)}"
		)
		return {
			"success": False,
			"error": f"An error occurred while testing connection: {str(e)}"
		}


@frappe.whitelist()
def ensure_parent_folders_exist():
	"""
	Pre-create parent folders (ALKHORA/استيرادية {YEAR}) to make folder creation instant
	This should be run once per year or when setting up
	"""
	try:
		# Get Nextcloud configuration
		settings_name = _get_settings_name()
		
		if not settings_name:
			return {
				"success": False,
				"error": "Nextcloud Settings not configured."
			}
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		if not nextcloud_config.enabled:
			return {
				"success": False,
				"error": "Nextcloud integration is disabled."
			}
		
		# Create parent folders
		current_year = datetime.now().year
		base_path = f"ALKHORA/استيرادية {current_year}"
		
		frappe.logger().info(f"Pre-creating parent folders: {base_path}")
		result = create_nextcloud_folder(
			nextcloud_url=nextcloud_config.nextcloud_url,
			username=nextcloud_config.username,
			password=nextcloud_config.get_password("password"),
			folder_path=base_path
		)
		
		if result.get("success"):
			return {
				"success": True,
				"message": f"Parent folders created/verified: {base_path}"
			}
		else:
			return {
				"success": False,
				"error": result.get("error", "Failed to create parent folders")
			}
		
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Parent Folders Error",
			message=f"Error creating parent folders: {str(e)}"
		)
		return {
			"success": False,
			"error": f"Error: {str(e)}"
		}
