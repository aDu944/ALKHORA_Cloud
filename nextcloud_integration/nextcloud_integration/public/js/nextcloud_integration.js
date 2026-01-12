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
		
		// Listen for realtime notifications
		frappe.realtime.on('nextcloud_folder_created', function(data) {
			if (data.success) {
				frappe.show_alert({
					message: __('Nextcloud folder created successfully'),
					indicator: 'green'
				}, 5);
				// Reload the form to show the new comment
				frm.reload_doc();
			} else {
				frappe.show_alert({
					message: data.error || __('Failed to create folder'),
					indicator: 'red'
				}, 10);
			}
		});
	}
});

function create_nextcloud_folder(frm) {
	// Show immediate feedback - NO loading indicator
	frappe.show_alert({
		message: __('Folder creation started in background. You will be notified when complete.'),
		indicator: 'blue'
	}, 5);
	
	// Use XMLHttpRequest for TRUE fire-and-forget (no UI blocking at all)
	var xhr = new XMLHttpRequest();
	xhr.open('POST', '/api/method/nextcloud_integration.hooks.create_nextcloud_folder_manual', true);
	xhr.setRequestHeader('Content-Type', 'application/json');
	xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
	
	// Very short timeout - just to trigger the job, don't wait for response
	xhr.timeout = 3000; // 3 seconds max to start the job
	
	// Send request (fire and forget)
	xhr.send(JSON.stringify({
		args: {
			opportunity_name: frm.doc.name
		}
	}));
	
	// Optional: Handle quick response (but don't block)
	xhr.onload = function() {
		if (xhr.status === 200) {
			try {
				var response = JSON.parse(xhr.responseText);
				if (response.message && !response.message.success) {
					frappe.show_alert({
						message: response.message.error || __('Failed to start folder creation'),
						indicator: 'red'
					}, 10);
				}
			} catch(e) {
				// Ignore parse errors - job might still be queued
			}
		}
	};
	
	xhr.ontimeout = function() {
		// Timeout is OK - job is probably queued
		// User will get notification when done
	};
	
	xhr.onerror = function() {
		// Error is OK - job might still be queued
		frappe.show_alert({
			message: __('Note: Please check if folder was created. Connection may be slow.'),
			indicator: 'orange'
		}, 5);
	};
}
