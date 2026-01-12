from frappe import _
import frappe
from datetime import datetime
from nextcloud_integration.nextcloud_integration.nextcloud_api import create_nextcloud_folder

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
	"""
	try:
		# Get Nextcloud configuration
		# Try to get the settings document (works for both Single DocType and regular)
		settings_name = "Nextcloud Settings"  # For Single DocType
		
		# If not found, try to get any existing document
		if not frappe.db.exists("Nextcloud Settings", settings_name):
			# Try to find any Nextcloud Settings document
			existing = frappe.get_all("Nextcloud Settings", limit=1)
			if existing:
				settings_name = existing[0].name
			else:
				frappe.logger().info("Nextcloud Settings not configured")
				return
		
		nextcloud_config = frappe.get_doc("Nextcloud Settings", settings_name)
		
		if not nextcloud_config.enabled:
			frappe.logger().info("Nextcloud integration is disabled")
			return
		
		# Generate folder path: /ALKHORA/استيرادية {YEAR}/Opportunity-{name}
		current_year = datetime.now().year
		opportunity_name = doc.name
		folder_prefix = nextcloud_config.folder_prefix or "Opportunity-"
		
		# Build the full path
		base_path = f"ALKHORA/استيرادية {current_year}"
		folder_name = f"{folder_prefix}{opportunity_name}"
		full_path = f"{base_path}/{folder_name}"
		
		# Create folder in Nextcloud
		result = create_nextcloud_folder(
			nextcloud_url=nextcloud_config.nextcloud_url,
			username=nextcloud_config.username,
			password=nextcloud_config.get_password("password"),
			folder_path=full_path
		)
		
		if result.get("success"):
			# Store the Nextcloud folder path in a custom field (if exists)
			# or log it for reference
			frappe.logger().info(f"Created Nextcloud folder: {result.get('folder_path')} for Opportunity: {opportunity_name}")
			
			# Add a comment to the opportunity
			doc.add_comment(
				comment_type="Info",
				text=f"Nextcloud folder created: {result.get('folder_path')}"
			)
		else:
			frappe.log_error(
				title="Nextcloud Folder Creation Failed",
				message=f"Failed to create folder for Opportunity {opportunity_name}: {result.get('error')}"
			)
			
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Integration Error",
			message=f"Error creating Nextcloud folder for Opportunity {doc.name}: {str(e)}"
		)

@frappe.whitelist()
def create_nextcloud_folder_manual(opportunity_name):
	"""
	Manually create a Nextcloud folder for an Opportunity
	This can be called from the client-side button
	"""
	try:
		# Validate that the opportunity exists
		if not frappe.db.exists("Opportunity", opportunity_name):
			return {
				"success": False,
				"error": f"Opportunity {opportunity_name} not found"
			}
		
		# Get Nextcloud configuration
		# Try to get the settings document (works for both Single DocType and regular)
		settings_name = "Nextcloud Settings"  # For Single DocType
		
		# If not found, try to get any existing document
		if not frappe.db.exists("Nextcloud Settings", settings_name):
			# Try to find any Nextcloud Settings document
			existing = frappe.get_all("Nextcloud Settings", limit=1)
			if existing:
				settings_name = existing[0].name
			else:
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
		
		# Generate folder path: /ALKHORA/استيرادية {YEAR}/Opportunity-{name}
		current_year = datetime.now().year
		folder_prefix = nextcloud_config.folder_prefix or "Opportunity-"
		
		# Build the full path
		base_path = f"ALKHORA/استيرادية {current_year}"
		folder_name = f"{folder_prefix}{opportunity_name}"
		full_path = f"{base_path}/{folder_name}"
		
		# Create folder in Nextcloud
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
				text=f"Nextcloud folder created manually: {result.get('folder_path')}"
			)
			
			frappe.logger().info(f"Manually created Nextcloud folder: {result.get('folder_path')} for Opportunity: {opportunity_name}")
			
			return {
				"success": True,
				"message": "Folder created successfully",
				"folder_path": result.get("folder_path")
			}
		else:
			return {
				"success": False,
				"error": result.get("error", "Unknown error occurred")
			}
			
	except Exception as e:
		frappe.log_error(
			title="Nextcloud Manual Folder Creation Error",
			message=f"Error manually creating Nextcloud folder for Opportunity {opportunity_name}: {str(e)}"
		)
		return {
			"success": False,
			"error": f"Error: {str(e)}"
		}
