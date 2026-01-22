import frappe
from frappe import _
from datetime import datetime
from nextcloud_integration.nextcloud_integration.nextcloud_api import create_nextcloud_folder

@frappe.whitelist()
def create_nextcloud_folder_for_document(doc_name, doctype="Opportunity"):
	"""
	Create Nextcloud folder for a document
	Can be called from client-side or server-side
	
	Args:
		doc_name: Name of the document (e.g., "OPP-00001")
		doctype: Type of document (default: "Opportunity")
	
	Returns:
		dict: {"success": bool, "message": str, "folder_path": str}
	"""
	try:
		# Get the document
		if not frappe.db.exists(doctype, doc_name):
			return {
				"success": False,
				"message": _(f"{doctype} {doc_name} not found")
			}
		
		doc = frappe.get_doc(doctype, doc_name)
		
		# Get Nextcloud settings
		settings_name = _get_settings_name()
		if not settings_name:
			return {
				"success": False,
				"message": _("Nextcloud Settings not configured. Please configure Nextcloud Settings first.")
			}
		
		settings = frappe.get_doc("Nextcloud Settings", settings_name)
		
		# Check if integration is enabled
		if not settings.enabled:
			return {
				"success": False,
				"message": _("Nextcloud integration is not enabled. Please enable it in Nextcloud Settings.")
			}
		
		# Check if auto-create is enabled (for manual calls, we still allow it)
		# But respect the feature flag for logging/notifications
		
		# Build folder path based on document type
		current_year = datetime.now().year
		folder_prefix = settings.folder_prefix or "Opportunity-"
		
		if doctype == "Opportunity":
			# Use the existing folder structure
			base_path = f"ALKHORA/استيرادية {current_year}"
			folder_name = f"{folder_prefix}{doc_name}"
			folder_path = f"{base_path}/{folder_name}"
		else:
			# Generic folder structure for other doctypes
			folder_name = doc_name.replace("/", "-")
			folder_path = f"{doctype}/{folder_name}"
		
		# Get Nextcloud credentials
		nextcloud_url = settings.nextcloud_url
		nextcloud_username = settings.username
		nextcloud_password = settings.get_password("password")
		
		if not nextcloud_url or not nextcloud_username or not nextcloud_password:
			return {
				"success": False,
				"message": _("Nextcloud credentials are incomplete. Please check Nextcloud Settings.")
			}
		
		# Check if SSH is enabled and configured
		use_ssh = getattr(settings, 'use_ssh', False) and \
		          getattr(settings, 'ssh_host', None) and \
		          getattr(settings, 'ssh_user', None)
		
		# Prepare SSH parameters if available
		ssh_host = None
		ssh_user = None
		ssh_key_path = None
		nextcloud_path = None
		occ_user = "www-data"
		use_service_token = False
		cf_client_id = None
		cf_client_secret = None
		
		if use_ssh:
			ssh_host = settings.ssh_host
			ssh_user = settings.ssh_user
			ssh_key_path = getattr(settings, 'ssh_key_path', None) or None
			nextcloud_path = getattr(settings, 'nextcloud_path', None) or None
			occ_user = getattr(settings, 'occ_user', None) or "www-data"
			
			# Check if Service Token is enabled
			use_service_token = getattr(settings, 'use_service_token', False)
			cf_client_id = getattr(settings, 'cf_client_id', None) or None
			if use_service_token and cf_client_id:
				cf_client_secret = settings.get_password("cf_client_secret") if hasattr(settings, 'cf_client_secret') else None
		
		# Create folder using the existing function
		result = create_nextcloud_folder(
			nextcloud_url=nextcloud_url,
			username=nextcloud_username,
			password=nextcloud_password,
			folder_path=folder_path,
			use_rest_api=False,  # Use optimized WebDAV
			ssh_host=ssh_host if use_ssh else None,
			ssh_user=ssh_user if use_ssh else None,
			nextcloud_path=nextcloud_path if use_ssh else None,
			ssh_key_path=ssh_key_path if use_ssh else None,
			occ_user=occ_user if use_ssh else None,
			use_service_token=use_service_token if use_ssh else False,
			cf_client_id=cf_client_id if use_ssh else None,
			cf_client_secret=cf_client_secret if use_ssh else None
		)
		
		if result.get("success"):
			# Add comment if feature is enabled
			if settings.is_feature_enabled("add_comments"):
				try:
					doc.add_comment(
						comment_type="Info",
						text=f"Nextcloud folder created: {result.get('folder_path')}"
					)
				except Exception as e:
					if settings.is_feature_enabled("log_events"):
						frappe.logger().error(f"Failed to add comment to {doctype} {doc_name}: {str(e)}")
			
			# Send notification if feature is enabled
			if settings.is_feature_enabled("send_notifications"):
				frappe.publish_realtime(
					event="nextcloud_folder_created",
					message={
						"success": True,
						"message": f"Nextcloud folder created successfully for {doctype} {doc_name}",
						"folder_path": result.get("folder_path")
					},
					user=frappe.session.user
				)
			
			# Log event if feature is enabled
			if settings.is_feature_enabled("log_events"):
				frappe.logger().info(f"Successfully created Nextcloud folder: {result.get('folder_path')} for {doctype}: {doc_name}")
			
			# Return success message
			return {
				"success": True,
				"message": _(f"✅ Nextcloud folder created: {result.get('folder_path')}"),
				"folder_path": result.get("folder_path")
			}
		else:
			error_msg = result.get("error", "Failed to create folder")
			
			# Log error if feature is enabled
			if settings.is_feature_enabled("log_events"):
				frappe.log_error(
					title="Nextcloud Folder Creation Error",
					message=f"Failed to create folder for {doctype} {doc_name}: {error_msg}"
				)
			
			# Send error notification if feature is enabled
			if settings.is_feature_enabled("send_notifications"):
				frappe.publish_realtime(
					event="nextcloud_folder_created",
					message={
						"success": False,
						"error": f"Failed to create Nextcloud folder: {error_msg}"
					},
					user=frappe.session.user
				)
			
			return {
				"success": False,
				"message": _(f"Failed to create folder: {error_msg}"),
				"error": error_msg
			}
	
	except Exception as e:
		error_msg = str(e)
		frappe.log_error(
			title="Nextcloud API Error",
			message=f"Error creating Nextcloud folder for {doctype} {doc_name}: {error_msg}"
		)
		return {
			"success": False,
			"message": _(f"An error occurred: {error_msg}")
		}


def create_nextcloud_folder_on_opportunity(doc, method):
	"""
	Event handler for Opportunity after_insert
	This is called automatically by hooks.py when a new Opportunity is created
	
	Args:
		doc: The Opportunity document
		method: The method name (e.g., "after_insert")
	"""
	# Check if auto-create is enabled
	settings_name = _get_settings_name()
	if settings_name:
		settings = frappe.get_doc("Nextcloud Settings", settings_name)
		if not settings.enabled or not settings.is_feature_enabled("auto_create"):
			frappe.logger().info(f"Auto-create folders is disabled. Skipping folder creation for Opportunity {doc.name}")
			return
	
	# Use the existing robust implementation from hooks.py
	# This includes retry logic and all feature flags
	from nextcloud_integration.hooks import _create_nextcloud_folder_background
	
	# Enqueue the folder creation to run in background
	frappe.enqueue(
		method=_create_nextcloud_folder_background,
		queue="default",
		timeout=None,
		job_name=f"create_nextcloud_folder_{doc.name}",
		opportunity_name=doc.name,
		is_async=True,
		at_front=True
	)
	frappe.logger().info(f"Enqueued Nextcloud folder creation for Opportunity {doc.name}")


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
