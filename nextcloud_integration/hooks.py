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


def create_opportunity_folder(doc, method):
	"""
	Create a folder in Nextcloud when a new Opportunity is created
	Runs in background to avoid blocking the opportunity creation
	"""
	try:
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

def _create_nextcloud_folder_background(opportunity_name):
	"""
	Background job function to create Nextcloud folder
	This runs in the background without blocking the user
	"""
	try:
		# Validate that the opportunity exists
		if not frappe.db.exists("Opportunity", opportunity_name):
			frappe.log_error(
				title="Nextcloud Folder Creation Error",
				message=f"Opportunity {opportunity_name} not found"
			)
			return
		
		# Get Nextcloud configuration
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
		
		if not settings_name:
			frappe.log_error(
				title="Nextcloud Folder Creation Error",
				message="Nextcloud Settings not configured"
			)
			return
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		if not nextcloud_config.enabled:
			frappe.logger().info("Nextcloud integration is disabled")
			return
		
		# Generate folder path: /ALKHORA/استيرادية {YEAR}/Opportunity-{name}
		current_year = datetime.now().year
		folder_prefix = nextcloud_config.folder_prefix or "Opportunity-"
		
		# Build the full path
		base_path = f"ALKHORA/استيرادية {current_year}"
		folder_name = f"{folder_prefix}{opportunity_name}"
		full_path = f"{base_path}/{folder_name}"
		
		# Create folder in Nextcloud
		frappe.logger().info(f"Creating Nextcloud folder for opportunity {opportunity_name}: {full_path}")
		result = create_nextcloud_folder(
			nextcloud_url=nextcloud_config.nextcloud_url,
			username=nextcloud_config.username,
			password=nextcloud_config.get_password("password"),
			folder_path=full_path
		)
		
		if result.get("success"):
			# Get the opportunity document to add a comment
			opportunity_doc = frappe.get_doc("Opportunity", opportunity_name)
			opportunity_doc.add_comment(
				comment_type="Info",
				text=f"Nextcloud folder created: {result.get('folder_path')}"
			)
			
			# Send notification to user
			frappe.publish_realtime(
				event="nextcloud_folder_created",
				message={
					"success": True,
					"message": f"Nextcloud folder created successfully for {opportunity_name}",
					"folder_path": result.get("folder_path")
				},
				user=frappe.session.user
			)
			
			frappe.logger().info(f"Successfully created Nextcloud folder: {result.get('folder_path')} for Opportunity: {opportunity_name}")
		else:
			error_msg = result.get("error", "Failed to create folder")
			frappe.log_error(
				title="Nextcloud Folder Creation Error",
				message=f"Failed to create folder for {opportunity_name}: {error_msg}"
			)
			
			# Send error notification to user
			frappe.publish_realtime(
				event="nextcloud_folder_created",
				message={
					"success": False,
					"error": f"Failed to create Nextcloud folder: {error_msg}"
				},
				user=frappe.session.user
			)
			
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Folder Creation Error",
			message=f"Error creating Nextcloud folder for Opportunity {opportunity_name}: {str(e)}"
		)
		
		# Send error notification to user
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
	This enqueues the job in the background
	"""
	try:
		# Validate that the opportunity exists
		if not frappe.db.exists("Opportunity", opportunity_name):
			return {
				"success": False,
				"error": f"Opportunity {opportunity_name} not found"
			}
		
		# Get Nextcloud configuration
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
		
		if not settings_name:
			return {
				"success": False,
				"error": "Nextcloud Settings not configured. Please configure it first."
			}
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		if not nextcloud_config.enabled:
			return {
				"success": False,
				"error": "Nextcloud integration is disabled. Please enable it in Nextcloud Settings."
			}
		
		# Enqueue the job to run in background
		frappe.enqueue(
			method=_create_nextcloud_folder_background,
			queue="default",
			timeout=None,  # No timeout
			job_name=f"create_nextcloud_folder_{opportunity_name}",
			opportunity_name=opportunity_name,
			is_async=True
		)
		
		return {
			"success": True,
			"message": "Folder creation started in background. You will be notified when it's complete."
		}
		
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Manual Folder Creation Error",
			message=f"Error enqueueing Nextcloud folder creation for Opportunity {opportunity_name}: {str(e)}"
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
