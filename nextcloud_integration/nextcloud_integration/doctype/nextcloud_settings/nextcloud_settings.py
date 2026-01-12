import frappe
from frappe.model.document import Document

class NextcloudSettings(Document):
	# This is a Single DocType, so there's only one document
	# No need for validation since Single DocTypes enforce uniqueness automatically
	pass
