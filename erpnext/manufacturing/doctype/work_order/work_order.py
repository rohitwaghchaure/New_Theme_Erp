# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

# from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt, getdate, comma_and, cint
from erpnext.accounts.accounts_custom_methods import generate_serial_no, release_work_order
from frappe.model.naming import make_autoname
from frappe import _, msgprint, throw

class WorkOrder(Document):
	def autoname(self):
		if self.work_order_no:
			self.name = self.work_order_no
		else:
			self.name = make_autoname(self.naming_series+'.#####')

	def validate(self):
		self.validate_style_measur_details()
		if not self.work_order_name:
			self.work_order_name = self.name

	def validate_style_measur_details(self):
		table_dict={'wo_style':'Style Options','measurement_item':'Measurement Details'}
		style_list=[]
		for key in table_dict:
			for d in self.get(key):
				style_list.append(d.field_name if key=='wo_style' else d.parameter)
			if style_list:
				for style in style_list:
					count=style_list.count(style)
					if count > 1:
						frappe.throw("Duplicate entry of %s in %s Table"%(style,table_dict[key]))


	def on_update(self):
		self.update_process_in_production_dashboard()
		# self.update_branch_in_trials()

	def update_process_in_production_dashboard(self):
		for d in self.get('process_wise_warehouse_detail'):
			if d.warehouse:
				frappe.db.sql("""update `tabProcess Log` p, `tabProduction Dashboard Details` pd set p.branch = '%s' 
					where p.parent = pd.name and p.process_name='%s' and pd.work_order='%s' 
					and pd.sales_invoice_no='%s'"""%(d.warehouse, d.process, self.name, self.sales_invoice_no))


	def update_branch_in_trials(self):
		name = frappe.db.get_value('Work Order Distribution', {'tailor_work_order':self.name, 'tailoring_item':self.item_code}, 'trials')
		for d in self.get('process_wise_warehouse_detail'):
			if cint(d.actual_fabric) == 1 and d.warehouse and d.process:
				frappe.db.sql("update `tabTrial Dates` set trial_branch = '%s' where parent ='%s' and process ='%s'"%(d.warehouse, name, d.process))

	# def make_serial_no(self):
	# 	if not self.serial_no_data:
	# 		generate_serial_no(self.item_code,self.item_qty)

	def get_details(self, template):
		self.get_measurement_details(template)
		# self.get_process(template)
		# self.get_raw_material(template)
		return "Done"

	# def on_update(self):
	# 	item_name = frappe.db.sql("select item_name from `tabItem` where item_code='%s'"%(self.item_code))
	# 	for d in self.get('wo_process'):
	# 		task_list = frappe.db.sql("select name from `tabTask` where subject='%s'"%(d.process),as_list=1)
	# 		if not task_list:
	# 			c = frappe.new_doc('Task')
	# 			c.subject = d.process
	# 			c.process_name =d.process
	# 			c.item_name =item_name[0][0]
	# 			c.sales_order_number = self.sales_invoice_no
	# 			c.save()

	def get_measurement_details(self, template):
		self.set('measurement_item', [])
		args = frappe.db.sql("""select * from `tabMeasurement Item`
			where parent='%s'"""%(template),as_dict=1)
		if args:
			for data in args:
				mi = self.append('measurement_item', {})
				mi.parameter = data.parameter
				mi.abbreviation = data.abbreviation
				mi.image_view = data.image_view
				mi.value = data.value
				mi.default_value = data.default_value
		return "Done"

	def get_process(self, item):
		self.set('wo_process', [])
		args = frappe.db.sql("""select * from `tabProcess Item`
			where parent='%s'"""%(item),as_dict=1)
		if args:
			for data in args:
				prd = self.append('wo_process', {})
				prd.process = data.process_name
				prd.trial = data.trial
				prd.quality_check = data.quality_check
		return "Done"

	def get_raw_material(self, item):
		self.set('raw_material', [])
		args = frappe.db.sql("""select * from `tabRaw Material Item`
			where parent='%s'"""%(item),as_dict=1)
		if args:
			for data in args:
				prd = self.append('raw_material', {})
				prd.item_code = data.item
				prd.item_name = frappe.db.get_value('Item', data.item, 'item_name')
		return "Done"

	def apply_rules(self, args):
		apply_measurement_rules(self.get('measurement_item'), args)

	def before_submit(self):
		from erpnext.accounts.accounts_custom_methods import make_schedule_for_trials
		make_schedule_for_trials(self,'before_submit')


	def on_submit(self):
		self.update_status('Completed')
		self.validate_mandatory_fields()
		# self.validate_nonzero_measurement()
		# self.set_work_order()
		# release_work_order(self)
		self.add_total_cost_to_customer()
		self.amend_work_order()

	def amend_work_order(self):
		if self.amended_from:
			frappe.db.sql(""" update `tabWork Order Distribution` set tailor_work_order = "%s"
				where tailor_work_order = "%s" """%(self.name, self.amended_from))

	def validate_mandatory_fields(self):
		mandatory_field = {'Measured By': self.measured_by}
		for key in mandatory_field:
			if not mandatory_field[key]:
				frappe.throw(_('{0} field is mandatory field').format(key))

	def validate_nonzero_measurement(self):
		for d in self.measurement_item:
			if flt(d.value) <= 0.0:
				frappe.throw(_('For measurement "{0}" value must be grater than zero').format(d.parameter)) 
	
	def add_total_cost_to_customer(self):
		if self.sales_invoice_no and self.item_qty:
			total_customer_cost = self.get_total_customer_cost() * flt(self.item_qty)
			if total_customer_cost != 0.0:
				company = frappe.db.get_value('Global Defaults',None,'default_company')
				if company:
					bank_account = frappe.db.get_value('Company',company,'default_bank_account')
					if bank_account: 
						si = frappe.get_doc('Sales Invoice',self.sales_invoice_no)	
						for d in si.get('other_charges'):
							if d.charge_type == 'Actual':
								d.rate = flt(d.rate) + flt(total_customer_cost)
								si.save()
								break
						else:				
							doc = si.append('other_charges',{})		
							doc.charge_type = 'Actual'
							doc.description = 'Cost to customer for tailoring product'
							doc.account_head = bank_account
							doc.rate = flt(total_customer_cost)
							si.save()
					else:
						frappe.throw("Set Default Bank Account For Company {0} ".format(company))
				else:
					frappe.throw("Set Default Company in Global Defaults")				


	def get_total_customer_cost(self):
		total_cost_to_customer = 0.0
		for d in self.get('wo_style'):
			total_cost_to_customer += flt(d.cost_to_customer)
		return total_cost_to_customer	 	


	def on_cancel(self):
		self.update_status('Pending')
		self.set_to_null()
		self.check_trials()

	def check_trials(self):
		if self.trial_date:
			trial = frappe.db.get_value('Trials', {'work_order': self.name}, 'name')
			if trial:
				frappe.throw(_("Delete the linked trials no {0}").format(trial))

	def validate_trial_serial_no(self):
		if self.serial_no_data and not self.trial_serial_no:
			frappe.throw(_("Mandatory Field: select trial serial no").format(self.trial_serial_no))

	def update_status(self, status):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order_status='%s'
					where sales_invoice_no='%s' and article_code='%s' 
					and work_order='%s'"""%(status,self.sales_invoice_no, self.item_code, self.name))

	def set_to_null(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order=(select name from tabCustomer where 1=2)
					where sales_invoice_no='%s' and article_code='%s' 
					and work_order='%s'"""%(self.sales_invoice_no, self.item_code, self.name))

	def set_work_order(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order= '%s', work_order_status ='Completed'
					where sales_invoice_no='%s' and article_code='%s' 
					"""%(self.name, self.sales_invoice_no, self.item_code))

	def fill_measurement_details(self):
		wo = frappe.get_doc('Work Order', self.work_orders)
		self.set('measurement_item', [])
		for d in wo.get('measurement_item'):
			e = self.append('measurement_item', {})
			e.parameter = d.parameter
			e.abbreviation = d.abbreviation
			e.image_view = d.image_view
			e.value = d.value

	def fill_cust_measurement_details(self):
		wo = frappe.get_doc('Customer', self.customer)
		self.set('measurement_item', [])
		for d in wo.get('body_measurements'):
			e = self.append('measurement_item', {})
			e.parameter = d.parameter
			e.value = d.value

	def fetch_previuos_Wo_Style(self):
		wo = frappe.get_doc('Work Order', self.style_work_order)
		self.set('wo_style', [])
		for d in wo.get('wo_style'):
			e = self.append('wo_style', {})
			e.field_name = d.field_name
			e.abbreviation = d.abbreviation
			e.image_viewer = d.image_viewer
			e.default_value = d.default_value
			e.table_view = d.table_view
		return True

@frappe.whitelist()
def apply_measurement_rules(measurement_details=None, param_args=None):
	result_list = []
	if isinstance(measurement_details, basestring):
		measurement_details = eval(measurement_details)
	if isinstance(param_args, basestring):
		param_args = eval(param_args)

	for d in measurement_details:
			if isinstance(d, dict):
				d = type('new_dict', (object,), d)

			measurement_formula_template = frappe.db.get_value('Item', param_args.get('item'),'measurement_formula_template')
			measurement_data = frappe.db.sql("select * from `tabMeasurement Rules` where parent='%s'"%(measurement_formula_template),as_dict=1)

			for data in measurement_data:
				if data.target_parameter == d.parameter and param_args.get('parameter') == data.parameter:
					value = (data.formula).replace('S',cstr(param_args.get('value')))
					d.value = cstr(flt(eval(value)))
					result_list.append({'parameter': data.target_parameter, 'value': d.value})
					
	return result_list

def get_prev_wo(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("select name from `tabWork Order` where customer = '%s' and item_code='%s'"%(filters.get('customer'), filters.get('item_code')),as_list=1)