import frappe
from frappe.model.document import Document

class NextcloudSettings(Document):
	def validate(self):
		# Ensure only one settings document exists
		if self.is_new():
			existing = frappe.db.exists("Nextcloud Settings", {"name": ["!=", self.name]})
			if existing:
				frappe.throw("Only one Nextcloud Settings document is allowed")
