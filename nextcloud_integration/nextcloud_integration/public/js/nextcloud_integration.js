// Add button to Opportunity form for manual Nextcloud folder creation
frappe.ui.form.on('Opportunity', {
	refresh: function(frm) {
		// Only show button if opportunity is saved (has a name)
		if (frm.doc.name && !frm.doc.__islocal) {
			// Add custom button
			frm.add_custom_button(__('Create Nextcloud Folder'), function() {
				create_nextcloud_folder(frm);
			}, __('Actions'));
		}
	}
});

function create_nextcloud_folder(frm) {
	// Show loading indicator
	frappe.show_progress(__('Creating Folder'), 50, __('Creating Nextcloud folder...'));
	
	// Call server method
	frappe.call({
		method: 'nextcloud_integration.hooks.create_nextcloud_folder_manual',
		args: {
			opportunity_name: frm.doc.name
		},
		callback: function(r) {
			frappe.hide_progress();
			
			if (r.message && r.message.success) {
				// Show success message
				frappe.show_alert({
					message: __('Nextcloud folder created successfully'),
					indicator: 'green'
				}, 5);
				
				// Reload the form to show the new comment
				frm.reload_doc();
				
				// Optionally open the folder in a new tab
				if (r.message.folder_path) {
					frappe.msgprint({
						title: __('Success'),
						message: __('Folder created successfully!<br><br><a href="{0}" target="_blank">Open Folder in Nextcloud</a>', [r.message.folder_path]),
						indicator: 'green'
					});
				}
			} else {
				// Show error message
				const error_msg = r.message && r.message.error ? r.message.error : __('Failed to create folder');
				frappe.show_alert({
					message: error_msg,
					indicator: 'red'
				}, 10);
				
				frappe.msgprint({
					title: __('Error'),
					message: error_msg,
					indicator: 'red'
				});
			}
		},
		error: function(r) {
			frappe.hide_progress();
			frappe.show_alert({
				message: __('An error occurred while creating the folder'),
				indicator: 'red'
			}, 10);
		}
	});
}
