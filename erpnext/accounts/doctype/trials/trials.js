cur_frm.cscript.work_order_changes = function(doc, cdt, cdn){

	var d =locals[cdt][cdn]
	if(d.work_order && parseInt(d.amend)==1){
		frappe.route_options = { work_order: d.work_order, args: d};
		frappe.set_route("work-order");		
	}else{
		alert("Not allowed to amend")
	}
	
}


cur_frm.fields_dict['trial_serial_no'].get_query = function(doc, cdt, cdn) {
      	return {
      		query : "tools.tools_management.custom_methods.get_serial_no",
      		filters : {
      			'serial_no':doc.serial_no_data
      		}
      	}
}

cur_frm.cscript.trial_serial_no = function(doc, cdt, cdn) {
    get_server_fields('update_status', '','',doc, cdt, cdn, 1, function(){
		// hide_field('trial_serial_no');
		refresh_field('trials_serial_no_status')
	})  	
}

cur_frm.cscript.validate= function(doc){
	if(doc.trials_serial_no_status){
		hide_field('trial_serial_no');
	}
	setTimeout(function(){refresh_field(['trial_dates', 'completed_process_log'])}, 1000)
}

cur_frm.cscript.refresh= function(doc, cdt, cdn){
	if(frappe.route_options){
		cur_frm.cscript.set_value(doc, cdt, cdn,frappe.route_options)
	}
	refresh_field('trial_dates')
	if(doc.trials_serial_no_status){
		hide_field('trial_serial_no');
	}
}

cur_frm.cscript.set_value= function(doc, cdt, cdn, prev_args){
	window.location.reload();
}

cur_frm.cscript.finished_all_trials = function(doc,dt,dn){
	var cl = doc.trial_dates || [ ]
	var flag = 0
	$.each(cl, function(i){
		if(cl[i].production_status!='Closed' && cl[i].work_status == 'Open'){
                  flag = 1
                   msgprint("Trial is Open for Process {0} in Row {1} So,can not cancel all remaining trials. Please Complete that trial For Cancellation of Remaining Trials".replace('{0}',cl[i].process).replace('{1}',cl[i].idx))
                   return false
		}
	})



   if (flag == 0){

	$.each(cl, function(i){
		if(cl[i].production_status!='Closed' && cl[i].work_status == 'Pending' && cl[i].skip_trial != 1){
			cl[i].skip_trial = parseInt(doc.finished_all_trials)
		get_server_fields('update_process_allotment',cl[i].process, '', doc, dt, dn,1, function(){
			refresh_field('trial_dates')
		})	


		}
	})


  }

	refresh_field('trial_dates')
}

// cur_frm.cscript.work_status = function(doc, cdt, cdn){
// 	var d = locals[cdt][cdn]
// 	var cl = doc.trial_dates || [ ]
// 	d.trial_no = d.idx
// 	if(d.work_status == 'Open'){

// 		$.each(cl, function(i){
// 			if(cl[i].production_status!='Closed' && parseInt(cl[i].idx) < parseInt(d.idx)){
// 				cl[i].next_trial_no = d.trial_no
// 			}
// 		})
// 	}
// 	refresh_field('trial_dates')
// }

cur_frm.fields_dict['finish_trial_for_process'].get_query = function(doc, cdt, cdn) {
		get_finished_list = cur_frm.cscript.get_finished_list(doc)
      	return {
      		query : "tools.tools_management.custom_methods.get_unfinished_process",
      		filters : {
      			'item_code':doc.item_code,
      			'get_finished_list' : get_finished_list
      		}
      	}
}

cur_frm.cscript.process = function(doc, cdt, cdn){
	var d =locals[cdt][cdn]
	if(d.production_status != 'Closed'){
		get_server_fields('get_trial_no', d, '', doc, cdt, cdn,1, function(r, rt){
			refresh_field('trial_no', d.name, 'trial_dates')	
		})	
	}else{
		cur_frm.cscript.PermissionException(doc, cdt, cdn)
	}
			
		// d.trial_no = d.idx
}

cur_frm.cscript.PermissionException = function(doc, cdt, cdn){
	get_server_fields('PermissionException','','', doc, cdt, cdn, 1, function(r){
		refresh_field('trial_dates')
	})
}

cur_frm.cscript.get_finished_list= function(doc){
	var cl = doc.completed_process_log || [ ]
	var process_list = ""
	if (parseInt(cl.length) > 1){
		$.each(cl, function(i){
			if(cl[i].completed_process && process_list){
				process_list = process_list + ",'" + cl[i].completed_process + "'"
			}else{
				process_list = "'" + cl[i].completed_process + "'"
			}
		})
		process_list = "(" + process_list + ")"
	}
	return process_list
}

cur_frm.cscript.work_status = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]

	if(d.production_status != 'Closed'){
		if(d.work_status == 'Open' && doc.trials_serial_no_status){
			d.subject = doc.trials_serial_no_status
			if(d.work_status == 'Open' && parseInt(d.trial_no) > 1 && d.work_status != 'Closed'){
				get_server_fields('check_serial_no', '', '', doc, cdt, cdn,1, function(r, rt){
					var a;
				})
			}
		}else if(!doc.trials_serial_no_status){
			d.work_status = 'Pending'
			refresh_field('work_status', d.name, 'trial_dates')
			alert("Select trial serial no")
		}	
	}else{
		cur_frm.cscript.PermissionException(doc, cdt, cdn)
	}
	
	refresh_field('subject', d.name, 'trial_dates')
}

cur_frm.cscript.trial_dates_add = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]
	var cl = doc.trial_dates || [ ]
	var work_order;
	if(d.production_status == 'Closed'){
		return false
	}else{
		if(!d.work_order){
			$.each(cl, function(i){
				if(parseInt(cl[i].idx) < parseInt(d.idx)){
					work_order = cl[i].work_order
				}
			})
			d.work_order = work_order
			refresh_field('trial_dates')
		}	
	}
	
}


cur_frm.cscript.trial_date = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]
	if(d.production_status != 'Closed'){
		if(doc.trials_serial_no_status){
			d.subject = doc.trials_serial_no_status
		}
		refresh_field('trial_dates')
	}else{
		cur_frm.cscript.PermissionException(doc, cdt, cdn)
	}
}


cur_frm.cscript.trial_branch = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]
	if (d.production_status =='Closed'){
		cur_frm.cscript.PermissionException(doc, cdt, cdn)
	}
}

cur_frm.cscript.finish_trial_for_process = function(doc, cdt, cdn){
	if(doc.trials_serial_no_status){
		get_server_fields('check_serial_no', '', '', doc, cdt, cdn,1, function(r, rt){
			var a;
		})
	}else{
		alert("Select serial no")
	}
	
}