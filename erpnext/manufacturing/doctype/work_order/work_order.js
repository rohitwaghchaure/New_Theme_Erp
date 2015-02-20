
cur_frm.cscript.image = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	d.image_view = '<table style="width: 100%; table-layout: fixed;"><tr><td style="width:110px"><img src="'+d.image+'" width="100px"></td></tr></table>'
	refresh_field("measurement_item");
}

cur_frm.cscript.add_image = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	d.image_viewer = '<table style="width: 100%; table-layout: fixed;"><tr><td style="width:110px"><img src="'+d.add_image+'" width="100px"></td></tr></table>'
	refresh_field("wo_style");
}

cur_frm.cscript.item_code = function(doc, cdt, cdn){
	get_server_fields('get_details',doc.item_code,'',doc ,cdt, cdn,1, function(){
		refresh_field(['measurement_item','wo_process','raw_material'])
	})
}

cur_frm.cscript.validate = function(doc, cdt, cdn){
	refresh_field('work_order_name')
}

cur_frm.cscript.field_name=function(doc,cdt,cdn){
	var d=locals[cdt][cdn]
	frappe.call({
		method:"erpnext.accounts.accounts_custom_methods.get_styles_DefaultValues",
		args:{style:d.field_name,item_code:doc.item_code},
		callback:function(r){
			d.default_value=r.message[1]
			d.image_viewer=r.message[0]
			refresh_field('image_viewer',d.name,'wo_style');
			refresh_field('default_value',d.name,'wo_style');

		}

	})
}


cur_frm.cscript.value = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]
	args = {'parameter':d.parameter, 'value':d.value, 'item':doc.item_code}
	get_server_fields('apply_rules',args,'',doc ,cdt, cdn,1, function(){
		refresh_field('measurement_item')
	})	
}

cur_frm.fields_dict.wo_style.grid.get_field("field_name").get_query = function(doc) {
      	return {
      		query : "tools.tools_management.custom_methods.get_style",
      		filters : {
      			'item_code':doc.item_code
      		}
      	}
}

cur_frm.fields_dict.process_wise_warehouse_detail.grid.get_field("warehouse").get_query = function(doc, cdt, cdn) {
		var d = locals[cdt][cdn]
      	return {
      		query : "tools.tools_management.custom_methods.get_branch_of_process",
      		filters : {
      			'item_code':doc.item_code,
      			'process' : d.process
      		}
      	}
}

cur_frm.cscript.view = function(doc, cdt, cdn){
	var e =locals[cdt][cdn]
	var image_data;
	var dialog = new frappe.ui.Dialog({
			title:__(e.field_name+' Styles'),
			fields: [
				{fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
					description: __("")},
					{fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
			]
		})
	var fd = dialog.fields_dict;

        // $(fd.styles_name.wrapper).append('<div id="style">Welcome</div>')
        return frappe.call({
			type: "GET",
			method: "tools.tools_management.custom_methods.get_styles_details",
			args: {
				"item": doc.item_code,
				"style": e.field_name
			},
			callback: function(r) {
				if(r.message) {
					
					var result_set = r.message;
					this.table = $("<table class='table table-bordered'>\
                       <thead><tr></tr></thead>\
                       <tbody></tbody>\
                       </table>").appendTo($(fd.styles_name.wrapper))

					columns =[['Style','10'],['Image','40'],['Value','40']]
					var me = this;
					$.each(columns, 
                       function(i, col) {                  
                       $("<th>").html(col[0]).css("width", col[1]+"%")
                               .appendTo(me.table.find("thead tr"));
                  }	);
					
					$.each(result_set, function(i, d) {
						var row = $("<tr>").appendTo(me.table.find("tbody"));
                       $("<td>").html('<input type="radio" name="sp" value="'+d[0]+'">')
                       		   .attr("style", d[0])
                               .attr("image", d[1])
                               .attr("value", d[2])
                               .attr("abbr", d[3])
                               .attr("customer_cost", d[4])
                               .attr("tailor_cost", d[5])
                               .attr("extra_cost", d[6])
                               .appendTo(row)
                               .click(function() {
                                      e.image_viewer = $(this).attr('image')
                                      e.default_value = $(this).attr('value')
                                      e.abbreviation = $(this).attr('abbr')
                                      e.cost_to_customer = $(this).attr('customer_cost')
                                      e.cost_to_tailor = $(this).attr('tailor_cost')                           
                               });
                     
                       $("<td>").html($(d[1]).find('img')).appendTo(row);
                       $("<td>").html(d[2]).appendTo(row);                    
               });
					
					dialog.show();
					$(fd.create_new.input).click(function() {						
						refresh_field('wo_style')	
						dialog.hide()
					})
				}
			}
		})		
}

cur_frm.fields_dict['trial_serial_no'].get_query = function(doc, cdt, cdn) {
		
      	return {
      		query : "tools.tools_management.custom_methods.get_serial_no",
      		filters : {
      			'serial_no':doc.serial_no_data
      		}
      	}
}

cur_frm.cscript.refresh = function(doc){
	if(doc.docstatus==1){
		cur_frm.appframe.add_primary_action(__('Draw Canvas'), cur_frm.cscript['Draw Canvas'], "icon-truck")
	}
	 if(frappe.route_options) {
	 	  if (frappe.route_options.number == 1){
	 	  	window.location.reload();
	 	  }
            
          }
}

cur_frm.cscript['Draw Canvas'] = function(){
	
	frappe.call({
          "method": "frappe.core.page.imgcanvas.imgcanvas.get_img",
          args: {
            work_order: cur_frm.docname
          },
          callback:function(r){
          	if(r.message){
          		frappe.route_options = { work_order: cur_frm.docname};
				frappe.set_route("imgcanvas");

          	}
          	else if(!r.message){

             alert("No Attached file found for Item")

          	}
          }


      });
	
}

cur_frm.fields_dict['work_orders'].get_query = function(doc) {
	return {
		query: "erpnext.manufacturing.doctype.work_order.work_order.get_prev_wo",
    	filters: {
			"customer": doc.customer,
			"item_code": doc.item_code
		}
	}
}

cur_frm.cscript.work_orders = function(doc, cdt, cdn){
	if(doc.work_orders){
		return get_server_fields('fill_measurement_details', '', '', doc, cdt, cdn, 1, function(){
			refresh_field('measurement_item')
		});	
	}
}

cur_frm.cscript.fetch_measurement_details = function(doc, cdt, cdn){
	return get_server_fields('fill_cust_measurement_details', '', '', doc, cdt, cdn, 1, function(){
		refresh_field('measurement_item')
	});
}

cur_frm.cscript.style_work_order = function(doc, cdt, cdn){
	if(doc.style_work_order){
		return get_server_fields('fetch_previuos_Wo_Style', '', '', doc, cdt, cdn, 1, function(){
			refresh_field('wo_style')
		});	
	}
}

cur_frm.fields_dict['style_work_order'].get_query = function(doc) {
	return {
		query: "erpnext.manufacturing.doctype.work_order.work_order.get_prev_wo",
    	filters: {
			"customer": doc.customer,
			"item_code": doc.item_code
		}
	}
}