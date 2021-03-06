
frappe.provide("erpnext.stock");
// frappe.require("assets/erpnext/js/controllers/stock_controller.js");

erpnext.stock.CustomItem = frappe.ui.form.Controller.extend({
    items_image: function(doc) {
        var image_data;
        var dialog = new frappe.ui.Dialog({
        title:__('Images'),
        fields: [{fieldtype:'HTML', fieldname:'image_name', label:__('Images'), reqd:false,
                  description: __("")}
                ]})

        var fd = dialog.fields_dict;
        return frappe.call({
            type: "GET",
            method: "erpnext.stock.stock_custom_methods.get_details",
            args: {
              "item_name": doc.name
            },
            callback: function(r) {
              var me = this;
              if(r.message)
              {
              result_set=r.message
              this.table = $('<div id="banner-slide" style="height:200px; width:300px;  textAlign:center">\
              <ul class="bjqs">\
              </ul></div>').appendTo($(fd.image_name.wrapper));
              $.each(result_set,function(i,d) {  
              var row = $("<li>").appendTo(me.table.find("ul"));
                        $("<li>").html('<li><img src="'+d[0]+'" width="500px" text-align="center" title="secound caption"></li>')
                               .appendTo(me.table.find(row));
                  });
                  this.table.bjqs({
                  height      : 500,
                  width       : 500,
                  responsive  : true,
                  randomstart   : true
                  });
                  dialog.show();
                }
                else
                {
                  msgprint("No Images Found");
                }
              }
          });
    },
    assign_trials : function(doc, cdt, cdn){
        var d = locals[cdt][cdn]
        if (parseInt(d.trials)==1){
            this.init_trials(d) // create dialog
            this.render_data(d) // to show data in the dialog
            this.add_trial(d) // add new rows
            this.save_data(d) // save data
            this.remove_row() // remove row
            this.auto_checked_actual_fabric()
            refresh_field('branch_dict')
        }
        else{
              alert("Click on Check box Trials")
        }
    },
    init_trials : function(data){
        this.dialog = new frappe.ui.Dialog({
            title:__('Trial'),
            fields: [
                {fieldtype:'Int', fieldname:'trial', label:__('Trial No'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'add_warehouse', label:__('Add'), reqd:false,
                    description: __("")},
                {fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
            ]
        })
        $('.modal-content').css('width', '800px')
        $('[data-fieldname = "create_new"]').css('margin-left','100px')
        this.control_trials = this.dialog.fields_dict;
        this.div = $('<div id="myGrid" style="width:100%;height:200px;margin:10px;overflow-y:scroll;"><table class="table table-bordered" style="background-color: #f9f9f9;height:10px" id="mytable">\
                    <thead><tr ><td>Process</td><td>Trial No</td><td>Quality Check</td><td>Actual Fabric</td>\
                    <td>Amendment</td><td>Trial Cost</td><td>Remove</td></tr></thead><tbody></tbody></table></div>').appendTo($(this.control_trials.styles_name.wrapper))

        this.dialog.show();
    },
    render_data: function(data){
        var me =this;
        var $trial_data;
        if (data.branch_dict){
            $trial_data = JSON.parse(data.branch_dict)
            for(j in $trial_data)
            {
                if($trial_data[j]['trial']){
                    me.table = $(me.div).find('#mytable tbody').append('<tr><td>'+$trial_data[j]['process']+'</td>\
                        <td>'+$trial_data[j]['trial']+'</td>\
                        <td><input id="quality_check" class="quality_check" type="checkbox" name="quality_check" '+$trial_data[j]['quality_check']+'></td>\
                        <td><input id="actual_fabric" class="quality_check" type="checkbox" name="actual_fabric" '+$trial_data[j]['actual_fabric']+'></td>\
                        <td><input id="amended" class="quality_check" type="checkbox"  name="amended" '+$trial_data[j]['amended']+'></td>\
                        <td><input type="Textbox" class="text_box" value="'+$trial_data[j]['cost']+'"></td>\
                        <td>&nbsp;<button  class="remove">X</button></td></tr>') 
                }
            }
        }
    },
    add_trial: function(data){
        var me = this;
        this.table;
        $(this.control_trials.add_warehouse.input).click(function(){
            var ch = ''
            if($(me.div).find('#mytable tbody tr:last td:eq(3) .quality_check').is(':checked') ==true){
                ch = 'checked'
            }
            this.table = $(me.div).find('#mytable tbody').append('<tr><td>'+data.process_name+'</td><td>'+me.control_trials.trial.last_value+'</td>\
                <td><input class="quality_check" type="checkbox" name="quality_check"></td>\
                <td><input id="actual_fabric" class="quality_check" type="checkbox" name="actual_fabric" '+ch+'></td>\
                <td><input class="quality_check" type="checkbox" name="amended" ></td><td><input class="text_box" data-fieldtype="Int" type="Textbox">\
                </td><td>&nbsp;<button  class="remove">X</button></td></tr>')
            $('[data-fieldname="trial"]').val('')
            me.auto_checked_actual_fabric()
            me.remove_row()
        })
    },
    save_data : function(data){
        var me = this;
        
        $(this.control_trials.create_new.input).click(function(){
            var status='true';
            var trials_dict={};
            $(me.div).find("#mytable tbody tr").each(function(i) {
                var key =['process','trial', 'quality_check','actual_fabric','amended','cost','cancel']
                var $data= {};
                trial_no = i;
                cells = $(this).find('td')
                $(cells).each(function(i) {
                    if(i==1 && parseInt($(this).text())!=(trial_no + 1)){
                        data.branch_dict ="";
                        status ='false';
                        return status
                    }
                    var d1 = $(this).find('.quality_check').is(':checked') ? 'checked' : $(this).find('.text_box').val() || $(this).text();
                    $data[key[i]]=d1
                })
                trials_dict[i]=($data)
            })

            if(status=='true' && trials_dict){
                data.trials_qc = me.find_trials_hasQC(trials_dict, 'quality_check')
                data.actual_fabric = me.find_trials_hasQC(trials_dict, 'actual_fabric')
                data.branch_dict = JSON.stringify(trials_dict)
                refresh_field('process_item')
                me.dialog.hide()
            }else{
                alert("Trials must be in sequence")
            }
        
        })
    },
    find_trials_hasQC: function(trials_dict, type){
        msg = 0
        $.each(trials_dict, function(i){
            if(trials_dict[i][type] == 'checked'){
                msg = 1
            }
        })
        return msg
    },

    remove_row : function(){
        var me =this;
        $(this.div).find('.remove').click(function(){
            $(this).parent().parent().remove()
        })
    },
    add_branch : function(doc, cdt, cdn){
        var d =locals[cdt][cdn]
        status = this.check_duplicate(d)
        if (status=='true' && d.warehouse){
            if(d.branch_list){
                d.branch_list += '\n'+d.warehouse   
            }
            else{
                d.branch_list=d.warehouse
            }
        }
        else{
            alert("process already available or process not selected")
        }
        refresh_field('process_item')
    },
    check_duplicate: function(data){
        if(data.branch_list){
            branches = (data.branch_list).split('\n')
            for(i=0;i<branches.length;i++){
                  if(data.warehouse == branches[i]){
                      return 'false'      
                  }
            }
        }
        return 'true'
    },
    price_list: function(doc, cdt, cdn){
        var s;
        // new frappe.CustomerRate(doc, cdt, cdn)
    },
    is_clubbed_product : function(doc){
        doc.has_serial_no = 'No'
        refresh_field('has_serial_no')
    },
    auto_checked_actual_fabric: function(){
        var me = this
        $(me.div).find('[name="actual_fabric"]').click(function(){
            var s= $(this).parent().parent().index();
            var count = $('#mytable').children('tbody').children('tr').length;
            for(i=s+1 ; i<count;i++)
            {
                $(me.div).find('#mytable tbody tr:eq('+i+') td:eq(3) .quality_check').prop('checked','checked')
            }
        })
    },

    define_cost_to_tailor:function(doc, cdt, cdn){
        this.d = locals[cdt][cdn]
        this.init_cost_to_tailor()
        this.render_cost_to_tailor_form()
        this.add_cost_to_tailor()
        this.save_tailor_cost()

    },
    init_cost_to_tailor:function(){
         this.dialog = new frappe.ui.Dialog({
            title:__('Cost To Tailor'),
            fields: [
                {fieldtype:'Link', fieldname:'process',options:'Process', label:__('Process'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'add_tailor_cost', label:__('Add'), reqd:false,
                    description: __("")},
                {fieldtype:'HTML', fieldname:'tailor_cost_name', label:__('Styles'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
            ]
        })
        $('.modal-content').css('width', '800px')
        $('[data-fieldname = "create_new"]').css('margin-left','100px')
        this.control_tailor_cost = this.dialog.fields_dict;
        this.div = $('<div id="myGrid" style="width:100%;height:200px;margin:10px;overflow-y:scroll;"><table class="table table-bordered" style="background-color: #f9f9f9;height:10px" id="mytable">\
                    <thead><tr ><td>Process</td><td>Tailor Cost</td><td>Remove</td></tr></thead><tbody></tbody></table></div>').appendTo($(this.control_tailor_cost.tailor_cost_name.wrapper))

        
        this.dialog.show();


    },
    render_cost_to_tailor_form:function(){
        var me = this
        if(me.d.process_wise_tailor_cost){
            tailor_dict = JSON.parse(me.d.process_wise_tailor_cost)
            $.each(tailor_dict,function(key,value){
                $(me.div).find('#mytable tbody').append('<tr id="my_row"><td>'+key+'</td>\
                <td id="cost"><input class="text_box" data-fieldtype="Int" type="Textbox" value='+value+'>\
                </td><td>&nbsp;<button  class="remove">X</button></td></tr>')
                 me.remove_row()
            })
        }   



    },
    add_cost_to_tailor:function(){

        var me = this;
        this.table;
        $(this.control_tailor_cost.add_tailor_cost.input).click(function(){
            this.table = $(me.div).find('#mytable tbody').append('<tr id="my_row"><td>'+me.control_tailor_cost.process.input.value+'</td>\
                <td><input class="text_box" data-fieldtype="Int" type="Textbox">\
                </td><td>&nbsp;<button  class="remove">X</button></td></tr>')
            me.remove_row()
        })

    },
     save_tailor_cost:function(){

       var me = this
        $(this.control_tailor_cost.create_new.input).click(function(){
             this.tailor_cost_dict = {}
             var inner_me = this
             $(me.div).find('#mytable tr#my_row').each(function(i,value){
                var $td = $(this).find('td')
                  var process_name = ''
                $($td).each(function(inner_index){
                  
                    if(inner_index == 0){
                        process_name = $(this).text()
                        inner_me.tailor_cost_dict[$(this).text()]=[]
                    }
                    if(inner_index == 1){
                        inner_me.tailor_cost_dict[process_name]=$(this).find('input').val()
                    }
                   
                })


             })
    
        me.d.process_wise_tailor_cost = JSON.stringify(this.tailor_cost_dict)
        refresh_field('style_item')
        refresh_field(['wo_style',me.d.name,'process_wise_tailor_cost'])
        me.dialog.hide()

        })
        
        
    }



})


frappe.CustomerRate = Class.extend({
    init: function(doc, cdt, cdn){
        this.data = locals[cdt][cdn] 
        this.make()
        this.render_data()
        this.add_rate()
        this.save_data()
        this.remove_rates()
    },

    make: function(){
        this.dialog = new frappe.ui.Dialog({
            title:__(' Customer Rate'),
            fields: [
                {fieldtype:'Link', fieldname:'price_list', label:__('Price List'), reqd:false,
                    description: __(""), options:'Service'},
                {fieldtype:'Currency', fieldname:'rate', label:__('Rate'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'add', label:__('Add'), reqd:false,
                    description: __("")},
                {fieldtype:'HTML', fieldname:'customer_rate', label:__('Customer Rate'), reqd:false,
                    description: __("")},
                {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
            ]
        })
        this.control_trials = this.dialog.fields_dict;
        this.div = $('<div id="myGrid" style="width:100%;height:200px;margin:10px;overflow-y:scroll;"><table class="table table-bordered" style="background-color: #f9f9f9;height:10px" id="mytable">\
                    <thead><tr><td>Service</td><td>Rate</td><td>Remove</td></tr></thead><tbody></tbody></table></div>').appendTo($(this.control_trials.customer_rate.wrapper))
        this.dialog.show();
    },

    render_data: function(){
        var me = this;
        if(this.data.costing_dict){
            column = JSON.parse(me.data.costing_dict);
            $.each(column, function(i){
                me.table = $(me.div).find('#mytable tbody').append('<tr><td>'+column[i].price_list+'</td><td><input type="Textbox" class="text_box" value="'+column[i].rate+'"></td><td>&nbsp;<button  class="remove">X</button></td></tr>')
            })
        }
    },

    add_rate: function(data){
        var me = this;
        this.price_list = []
        $(this.control_trials.add.input).click(function(){
            status = me.check_duplicate_price_list(me.dialog.get_values().price_list)
            if(me.dialog.get_values().price_list && me.control_trials.rate.last_value && status=='true'){
                me.price_list.push(me.dialog.get_values().price_list)
                me.table = $(me.div).find('#mytable tbody').append('<tr><td>'+me.dialog.get_values().price_list+'</td><td><input type="Textbox" class="text_box" value="'+me.control_trials.rate.last_value+'"></td><td>&nbsp;<button  class="remove">X</button></td></tr>')
                me.remove_rates()
            }
        })
    },

    save_data: function(){
        var me =this;
        $(this.control_trials.create_new.input).click(function(){
            var $rate_dict = {} 
            $(me.div).find('#mytable tbody tr').each(function(i) {
                var key = ['price_list', 'rate','close']
                var cells = $(this).find('td')
                var $data ={}
                $(cells).each(function(i){
                    $data[key[i]] = $(this).find('.text_box').val() || $(this).text(); 
                })
                $rate_dict[i] = $data
            })
            me.data.costing_dict = JSON.stringify($rate_dict)
            refresh_field('costing_item')
            me.dialog.hide()
        })
    },

    check_duplicate_price_list : function(price_list){
        var me = this;
        status = 'true'
        if(this.price_list){
            $.each(this.price_list, function(i){
                if(price_list == me.price_list[i]){
                    status = 'false'
                    return status
                }
            })
        }
        return status
    },

    remove_rates: function(){
        $(this.div).find('.remove').click(function(){
            $(this).parent().parent().remove()
        })
    }
})


erpnext.stock.SplitQty = frappe.ui.form.Controller.extend({
    split_qty : function(doc, cdt, cdn){
        this.data = locals[cdt][cdn]
        this.split_init()
    },

    split_init: function(){
        this.make_structure()
        this.render_split_data()
        this.add_new_split_data()
        this.save_data()
        this.remove_qty()
    },

    make_structure: function(){
        if(this.data.check_split_qty=='1')
        {
            this.dialog = new frappe.ui.Dialog({
                title:__(' Styles'),
                fields: [
                {fieldtype:'Int', fieldname:'qty', label:__('Qty'), reqd:false,
                        description: __("")},
                        {fieldtype:'Button', fieldname:'add_qty', label:__('Add'), reqd:false,
                        description: __("")},
                    {fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
                        description: __("")},
                        {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
                ]
            })
            this.fd = this.dialog.fields_dict;
            this.div = $('<div id="myGrid" style="width:100%;height:200px;margin:10px;overflow-y:scroll">\
                        <table class="table table-bordered" style="background-color: #f9f9f9;height:10px" id="mytable">\
                        <thead><tr><td>Item</td><td>Qty</td><td>Remove</td></tr>\
                        </thead><tbody></tbody></table></div>').appendTo($(this.fd.styles_name.wrapper))
            this.dialog.show()
        }else{
            alert("Click on check split qty")
        }
    },

    render_split_data: function(){
        var me = this;
        if(this.data.split_qty_dict){
            column = JSON.parse(me.data.split_qty_dict)
            $.each(column, function(i){
                this.table = $(me.div).find('#mytable tbody').append('<tr><td style="background-color:#FFF">'+column[i].tailoring_item_code+'</td><td style="background-color:#FFF"><input type="Textbox" class="text_box" value="'+column[i].qty+'"></td><td>&nbsp;<button  class="remove">X</button></td></tr>')
            })
        }
    },

    add_new_split_data: function(){
        var me = this;
        $(this.fd.add_qty.input).click(function(){
            if(me.fd.qty.last_value){
                this.table = $(me.div).find('#mytable tbody').append('<tr><td style="background-color:#FFF">'+me.data.tailoring_item_code+'</td><td style="background-color:#FFF"><input type="Textbox" class="text_box" value="'+me.fd.qty.last_value+'"></td><td>&nbsp;<button  class="remove">X</button></td></tr>')
                me.remove_qty()                
            }    
        })
        
    },

    save_data: function(){
        var me =this;
        $(this.fd.create_new.input).click(function(){
            me.split_dict={}
            var sum = 0
            $(me.div).find('#mytable tbody tr').each(function(i){
                var key = ['tailoring_item_code', 'qty', 'cancel'];
                var qty_data={}
                cells = $(this).find('td')
                $(cells).each(function(i){
                    qty_data[key[i]] = $(this).find('.text_box').val() || $(this).text();
                    val = parseInt($(this).find('.text_box').val())
                    if(val){
                        sum += val;
                    }
                })
                me.split_dict[i] = qty_data
            })
            me.validate_data(sum)
        })
    },

    validate_data: function(qty){
        var me = this;
        if(parseInt(qty)==parseInt(me.data.tailoring_qty)){
            me.data.split_qty_dict = JSON.stringify(me.split_dict)
            refresh_field('sales_invoice_items_one')
            me.dialog.hide()
        }else{
            alert("Split qty should be equal to Taiiloring Product Qty")
            me.dialog.show()
        }
    },

    remove_qty: function(){
        var me = this;
        $(this.div).find('.remove').click(function(){
            $(this).parent().parent().remove()
        })
    }
})










erpnext.stock.ReserveFabric = frappe.ui.form.Controller.extend({

    reserve_fabric:function(doc,cdt,cdn){
        this.data = locals[cdt][cdn]
        this.init_reserve_fabric()
        this.doc = doc
        this.cdt = cdt
        this.cdn = cdn
    },
    init_reserve_fabric:function(){
        this.check_for_fabric_qty()

    },
    check_for_fabric_qty:function(){
      
      if (this.data.fabric_qty){
        this.render_reserve_fabric_dialog()
        this.render_existing_reserved_fabric()
      }else{
        alert("Fabric qty must be given to reserve fabric {0}".replace('{0}',this.data.fabric_code))
      } 


    },
    render_reserve_fabric_dialog:function(){
        this.dialog = new frappe.ui.Dialog({
                 title:__('Reserve Fabric'),
                 fields: [
                     {fieldtype:'HTML', fieldname:'reserve', reqd:false,
                         description: __("")},
                         {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
                 ]
             })
            
        this.fd = this.dialog.fields_dict;
        this.table = $("<table id='fabric_reserve' class='table table-bordered'>\
                       <thead><tr></tr></thead>\
                       <tbody></tbody>\
                       </table>").appendTo($(this.fd.reserve.wrapper))

        columns =[['Branch','40'],['Qty','40'], ['Reserve Qty', 50]]
        
        this.dialog.show()


    },
    render_existing_reserved_fabric:function(){
        var me =this
        if (this.data.reserve_fabric_qty){
            me.head = $("<th style='width:100px'>Branch</th><th style='width:100px'>Reserve Qty</th>").appendTo($(me.table).find('thead tr')) 
            $.each(JSON.parse(this.data.reserve_fabric_qty),function(key,value){
                $.each(JSON.parse(value),function(index,inner_value){
                   var row = $("<tr>").appendTo($(me.table).find("tbody"));
                    
                     $("<td>").html(index).appendTo(row);

                     $("<td>").html(inner_value[1]).appendTo(row); 


                })
            })
        
            $(me.fd.create_new.input).click(function() {
                me.dialog.hide()
            })


        }
        else{

             this.add_reserve_fabric()
        }


    },
    add_reserve_fabric:function(){
      var me = this

       return frappe.call({
            type: "GET",
            method: "tools.tools_management.custom_methods.get_warehouse_wise_stock_balance",
            args: {
                "item": this.data.fabric_code,
                "qty": this.data.fabric_qty
            },
            callback: function(r) {
                if(r.message) {
                    
                    var result_set = r.message;
                
                    
                    me.head = $("<th style='width:100px'>Branch</th><th style='width:100px'>Qty</th><th style='width:100px'>Reserve Qty</th>").appendTo($(me.table).find('thead tr')) 
                    $.each(result_set, function(i, d) {
                        var row = $("<tr>").appendTo($(me.table).find("tbody"));
                        $("<td>").html(d[2]).appendTo(row);
                        $("<td>").html(d[1]).appendTo(row); 
                        if(me.doc.branch == d[2]){
                            if (parseInt(d[1]) < parseInt(me.data.fabric_qty)){
                            $("<td>").html('<input type="Textbox" class="text_box" value='+d[1]+'>').appendTo(row); 
                            }
                            else{
                                $("<td>").html('<input type="Textbox" class="text_box" value='+me.data.fabric_qty+'>').appendTo(row);
                            }   
                            

                        }else{
                              $("<td>").html('<input type="Textbox" class="text_box">').appendTo(row);
                        }
                      
                     
                      
               });

                                
                    $(me.fd.create_new.input).click(function() {
                        this.total_qty = 0.0
                        this.fabric_detail ={}
                        var inner_me = this   
                        $.each($(me.table).find('input.text_box'),function(){
                            if ($(this).val()){
                                inner_me.fabric_detail[$(this).closest("tr").find('td:first').text()] = [me.data.fabric_code, $(this).closest("tr").find('.text_box').val(), me.data.tailoring_item_code]                            
                                inner_me.total_qty = parseFloat($(this).val()) + parseFloat(inner_me.total_qty)
                            }
                            
                        })

                         if (inner_me.total_qty > parseFloat(me.data.fabric_qty)){
                                alert("Sum of Total Quantity entered i.e {0} is exceeding Fabric Quantity {1}".replace('{1}',me.data.fabric_qty).replace('{0}',inner_me.total_qty))       
                        
                            }

                        else{

                            var check = confirm(__("This is Permanent Action. Are you sure you want to reserve fabric ?"))
                            if (check){
                                     
                                    this.my_fabric_details = {}
                                    this.my_fabric_details[me.data.tailoring_item_code] = JSON.stringify(this.fabric_detail) 
                                    frappe.model.set_value(me.cdt, me.cdn, 'reserve_fabric_qty', JSON.stringify(this.my_fabric_details));
                                    refresh_field('reserve_fabric_qty',me.data.name,'sales_invoice_items_one')
                                    me.data.reservation_status = 'Reserved';
                                    refresh_field('reservation_status', me.data.name, 'sales_invoice_items_one')  
                                    me.dialog.hide()

                                            
                                 }       
                                        
                            }   
                        
                        
                    })
                }
            }
        })  




    }



})