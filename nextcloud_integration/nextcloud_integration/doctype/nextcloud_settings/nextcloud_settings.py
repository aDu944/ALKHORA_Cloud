import frappe
from frappe.model.document import Document
from frappe import _

class NextcloudSettings(Document):
	"""Nextcloud Integration Settings - Single DocType"""
	
	def validate(self):
		"""Validate settings before saving"""
		# Validate retry attempts range
		if self.auto_retry_failed:
			if not self.max_retry_attempts or self.max_retry_attempts < 1:
				self.max_retry_attempts = 3
			elif self.max_retry_attempts > 10:
				frappe.throw(_("Maximum retry attempts cannot exceed 10"))
		
		# Validate required fields when enabled
		if self.enabled:
			if not self.nextcloud_url:
				frappe.throw(_("Nextcloud URL is required when integration is enabled"))
			if not self.username:
				frappe.throw(_("Username is required when integration is enabled"))
			if not self.get_password("password"):
				frappe.throw(_("Password is required when integration is enabled"))
	
	def is_feature_enabled(self, feature_name):
		"""Check if a specific feature is enabled"""
		if not self.enabled:
			return False
		
		feature_map = {
			"auto_create": getattr(self, "auto_create_folders", True),
			"add_comments": getattr(self, "add_comments", True),
			"send_notifications": getattr(self, "send_notifications", True),
			"log_events": getattr(self, "log_events", True),
			"auto_retry": getattr(self, "auto_retry_failed", True),
		}
		
		return feature_map.get(feature_name, False)
	
	def get_max_retries(self):
		"""Get maximum retry attempts"""
		if not self.auto_retry_failed:
			return 0
		return min(max(getattr(self, "max_retry_attempts", 3), 1), 10)
