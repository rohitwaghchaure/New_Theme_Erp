# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, flt, getdate, comma_and, nowdate, cint, now, nowtime , get_datetime
from erpnext.accounts.accounts_custom_methods import delte_doctype_data, prepare_serial_no_list, check_for_reassigned, update_status_to_completed, stock_entry_for_out, add_to_serial_no, get_idx_for_serialNo, open_next_branch
from tools.custom_data_methods import get_user_branch, get_branch_cost_center, get_branch_warehouse, update_serial_no, find_next_process
import datetime
from tools.custom_data_methods import generate_barcode
from tools.custom_data_methods import gererate_QRcode
import pdb

class ProcessAllotment(Document):

	def validate(self):
		# self.assign_task()
		# self.update_process_status()
		self.make_IssueSTE()
		# self.update_task()
		self.prepare_for_time_log()
		# self.make_auto_ste()
		# self.auto_ste_for_trials()
		self.procees_allotment_qrcode()
		self.procees_allotment_barcode()
		self.check_extra_payment()

	def check_extra_payment(self):
		val = frappe.db.get_value('Costing Item', {'parent':self.item, 'branch': get_user_branch()}, 'max_extra_chg')
		if val:
			for d in self.get('employee_details'):
				if d.tailor_extra_charge=='Yes':
					if flt(d.tailor_extra_amt) > flt(val):
						frappe.throw(_("Extra Amount can not be greater than {0}").format(val))

	def make_IssueSTE(self):
		if self.get('issue_raw_material'):
			self.create_se(self.get('issue_raw_material'))
		return "Done"

	def procees_allotment_barcode(self):
		
		if cint(frappe.db.get_value('Global Defaults',None,'barcode'))==1:
			if not self.barcode:	
				#self.barcode=self.name
				self.bar= generate_barcode(self.name, self.doctype)
				self.barcode = '<img src="/files/Barcode/%s/%s.svg">'%(self.doctype,self.name.replace("/","-"))
		


	def procees_allotment_qrcode(self):
		if cint(frappe.db.get_value('Global Defaults',None,'qrcode'))==1:
			if not self.qrcode:	
				self.bar= gererate_QRcode(self.name,self.doctype)
				self.qrcode = '<img src="/files/QRCode/%s/%s.png">'%(self.doctype,self.name.replace("/","-"))	

		

	def show_trials_details(self):
		trials_data = frappe.db.sql("select * from `tabProcess Log` where (ifnull(status,'') = 'Open' or ifnull(status,'')='Closed') and process_name='%s' and process_data = '%s' and trials is not null order by trials"%(self.process, self.name), as_dict=1)
		self.set('trials_transaction', [])
		for data in trials_data:
			td = self.append('trials_transaction', {})
			td.trial_no = data.trials
			td.status = data.status
			td.work_order = data.pr_work_order

	def prepare_for_time_log(self):
		if self.get('employee_details'):
			for data in self.get('employee_details'):
				self.validate_trials(data)
				self.start_process_for_serialNo(data)
				if cint(data.idx) == cint(len(self.get('employee_details'))):
					status = 'Closed' if data.employee_status == 'Completed' else 'Open'
					frappe.db.sql("update `tabTask` set status ='%s' where name='%s'"%( status, data.tailor_task))

	def make_time_log(self, data, task):
		tl = frappe.new_doc('Time Log')
		tl.from_time = data.tailor_from_time
		tl.hours = flt(data.work_completed_time)/60
		tl.to_time = datetime.datetime.strptime(tl.from_time, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours = flt(tl.hours))
		tl.activity_type = self.process
		tl.task = task
		tl.project = self.sales_invoice_no
		tl.save(ignore_permissions=True)
		t = frappe.get_doc('Time Log', tl.name)
		t.submit()
		return tl.name

	def start_process_for_serialNo(self, data):
		if data.employee_status == 'Assigned':
			idx = get_idx_for_serialNo(data, self.pdd, self.process)
			details = open_next_branch(self.pdd, idx)
			add_to_serial_no(details, self.process_work_order, data.tailor_serial_no, data.qc_required, data.employee_name)
		else:
			self.update_sn_status(data)
			if data.employee_status == 'Completed' and not data.ste_no:
				details = find_next_process(self.pdd, self.process, data.tailor_process_trials)
				if cint(data.qc_required)==1:
					if data.tailor_process_trials and cint(frappe.db.get_value('Trial Dates',{'parent':self.trial_dates, 'trial_no':data.tailor_process_trials,'process':self.process}, 'quality_check')) != 1:
						data.ste_no = self.make_ste(details, data)
					else:
						data.ste_no = self.make_qc(details, data)
				else:
					data.ste_no = self.make_ste(details, data)

	def make_qc(self, details, data):
		sn_list = self.get_not_added_sn(data.tailor_serial_no, 'serial_no_data', 'Quality Inspection')
		if sn_list:
			qi = frappe.new_doc('Quality Inspection')
			qi.inspection_type = 'In Process'
			qi.report_date = nowdate()
			qi.item_code = self.item
			qi.inspected_by = frappe.session.user
			qi.sample_size = data.assigned_work_qty
			qi.customer_name = self.customer_name
			qi.sales_invoice_no =self.sales_invoice_no
			qi.serial_no_data = sn_list
			qi.process = self.process
			qi.work_order = self.process_work_order
			qi.pdd = self.pdd
			qi.trial_no = data.tailor_process_trials
			qi.tdd = self.trial_dates
			self.qa_specification_details(qi)
			qi.save(ignore_permissions=True)
			return qi.name

	def qa_specification_details(self, obj):
		qi_data = frappe.db.sql("""select * from `tabItem Quality Inspection Parameter`
			where parent='%s' and qi_process='%s'"""%(self.item, self.process), as_dict=1)
		if qi_data:
			for data in qi_data:
				qa = obj.append('qa_specification_details')
				qa.process = data.process
				qa.specification = data.specification
		return "Done"

	def make_ste(self, details, data):
		s= {'work_order': self.process_work_order, 'status': 'Release', 'item': self.item, 'trial_no': self.process_trials}
		sn_list = self.get_not_added_sn(data.tailor_serial_no, 'serial_no', 'Stock Entry Detail')
		if sn_list:
			branch, type_of_log = self.get_branch(details, data)
			dte_no = stock_entry_for_out(s, branch, sn_list, data.assigned_work_qty, type_of_log)
			return dte_no

	def get_branch(self, pdlog, args):
		type_of_log = 'No'
		if pdlog:
			branch = pdlog.branch
		elif not args.tailor_process_trials:
			branch = frappe.db.get_value('Production Dashboard Details', self.pdd, 'end_branch')
			if branch:
				self.Change_Completed_Status(args, branch)  #newly added
				type_of_log = 'Delivery'

		if args.tailor_process_trials and self.trial_dates: 
			branch = frappe.db.get_value('Trial Dates', {'parent': self.trial_dates, 'trial_no': args.tailor_process_trials}, 'trial_branch')
			type_of_log = 'Trial'

		return branch, type_of_log

	def Change_Completed_Status(self, args, branch):
		if args.tailor_serial_no:
			serial_no = cstr(args.tailor_serial_no).split('\n')
			for sn in serial_no:
				if sn:
					frappe.db.sql("update `tabSerial No` set completed = 'Yes' where name = '%s'"%(sn))

	def get_not_added_sn(self, sn_list, fieldname, table):
		new_sn_list = ''
		data = frappe.db.sql(""" select %s from `tab%s` where 
			work_order = '%s' and docstatus=0"""%(fieldname, table, self.process_work_order), as_list=1)
		if data:
			for sn in data:
				sn = cstr(sn[0]).split('\n')
				for s in sn:
					if s:
						serial_no = self.check_available(s, sn_list)
						if new_sn_list:
							new_sn_list = new_sn_list + '\n' + serial_no
						else:
							new_sn_list = serial_no
		else:
			new_sn_list = sn_list
		
		duplicate_list = new_sn_list.split('\n')
		unique_list = set(duplicate_list)
		new_sn_list = '\n'.join(unique_list)
		return new_sn_list

	def check_available(self, serial_no, sn_list):
		sn_data = ''
		sn_list = cstr(sn_list).split('\n')
		for sn in sn_list:
			if sn and sn != serial_no:
				if sn_data:
					sn_data = sn_data + '\n' + sn
				else:
					sn_data = sn
		return sn_data

	def update_sn_status(self, args):
		if args.tailor_serial_no:
			serial_no_list = cstr(args.tailor_serial_no).split('\n')
			for serial_no in serial_no_list:
				if args.employee_status == 'Completed' or  args.employee_status == 'Reassigned' and not args.ste_no:
					update_status_to_completed(serial_no, self.name, self.emp_status, args)

	def validate_trials(self, args):
		if self.process_trials and cint(args.assigned_work_qty) > 1:
			frappe.throw(_("Only one serial no is allocated for trial no"))
		if args.employee_status == 'Completed' and args.tailor_process_trials:
			details = frappe.db.sql("""select name, production_status from `tabTrial Dates` where
				parent='%s' and trial_no='%s' and process='%s' """%(self.trial_dates, args.tailor_process_trials,self.process), as_list=1)
			if details:
				if details[0][1] != 'Closed' and cint(self.qc) != 1:
					frappe.db.sql(""" update `tabTrial Dates` set production_status='Closed'
						where name='%s'	"""%(details[0][0]))
					if self.pdd:
						frappe.db.sql(""" update `tabProcess Log` set completed_status = 'Yes'
							where trials=%s and parent = '%s'	"""%(cint(self.process_trials), self.pdd))

	# def make_auto_ste(self):
	# 	if self.process_status == 'Closed':
	# 		self.validate_trials_closed()
	# 		cond = "1=1"
	# 		current_name, next_name = self.get_details(cond)
	# 		target_branch = frappe.db.get_value('Process Log', next_name, 'branch')
	# 		args = {'qty': self.finished_good_qty, 'serial_data': self.serials_data, 'work_order': self.process_work_order, 'item': self.item}
	# 		if get_user_branch() == target_branch:
	# 			self.update_status(current_name, next_name)
	# 			frappe.db.sql("""update `tabProcess Log` set status = 'Open' where name='%s' and trials is null"""%(next_name))
	# 		else:
	# 			parent = self.prepare_stock_entry_for_process(target_branch, args)
	# 			if parent:
	# 				self.update_status(current_name, next_name)
	# 				frappe.msgprint("Created Stock Entry %s"%(parent))
		
	# def validate_trials_closed(self):
	# 	count = frappe.db.sql("select ifnull(count(*),0) from `tabProcess Log` where process_data = '%s' and status = 'Open' and trials is not null"%(self.name), debug=1)
	# 	if count:
	# 		if cint(count[0][0])!=0	and self.process_status == 'Closed':
	# 			frappe.throw(_("You must have to closed all trials"))	

	# def update_status(self, current_name, next_name):
	# 	frappe.db.sql("""update `tabProcess Log` set status = 'Closed' where name='%s'"""%(current_name))

	# def prepare_stock_entry_for_process(self, target_branch, args):
	# 	if self.branch != target_branch and not frappe.db.get_value('Stock Entry Detail', {'work_order': self.process_work_order, 'target_branch':target_branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(self.branch)}, 'name'):
	# 		parent = frappe.db.get_value('Stock Entry Detail', {'target_branch':target_branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(self.branch)}, 'parent')			
	# 		if parent:
	# 			st = frappe.get_doc('Stock Entry', parent)
	# 			self.stock_entry_of_child(st, args, target_branch)
	# 			st.save(ignore_permissions= True)
	# 		else:
	# 			parent = self.make_stock_entry(target_branch, args)
	# 		frappe.msgprint(parent)
	# 		return parent

	# def auto_ste_for_trials(self):
	# 	for d in self.get('employee_details'):
	# 		cond = "1=1"
	# 		self.update_serial_no_status(d)
	# 		status = frappe.db.get_value('Process Log', {'process_data': self.name, 'trials': d.tailor_process_trials}, 'status')
	# 		if d.employee_status == 'Completed' and not d.ste_no and status!='Closed':
	# 			if d.tailor_process_trials:
	# 				cond = "trials ='%s'"%(d.tailor_process_trials)
	# 			current_name, next_name = self.get_details(cond)
	# 			target_branch = self.get_target_branch(d, next_name)

	# 			args = {'qty': d.assigned_work_qty, 'serial_data': d.tailor_serial_no, 'work_order': self.process_work_order, 'item': self.item}
	# 			d.ste_no = self.prepare_stock_entry_for_process(target_branch, args)
	# 			self.update_status(current_name, next_name)
	# 			if d.tailor_process_trials:
	# 				# trial_name = frappe.db.get_value('Trials',{'sales_invoice': self.sales_invoice_no, 'work_order': self.process_work_order, 'trial_no': d.tailor_process_trials}, 'name')
	# 				parent = frappe.db.sql(""" select name from `tabTrials` where sales_invoice='%s' and work_order='%s'"""%(self.sales_invoice_no, self.process_work_order), as_list=1)
	# 				if parent:
	# 					frappe.db.sql("""update `tabTrial Dates` set production_status = 'Closed' where
	# 						parent = '%s' and trial_no = '%s'"""%(parent[0][0], d.tailor_process_trials))

	# def get_target_branch(self, args, next_name):
	# 	if args.tailor_process_trials:
	# 		trial_name = frappe.db.get_value('Trials',{'sales_invoice': self.sales_invoice_no, 'work_order': self.process_work_order}, 'name')
	# 		trials = frappe.db.get_value('Trial Dates', {'parent': trial_name, 'process': self.process, 'trial_no': args.tailor_process_trials}, '*')
	# 		return trials.trial_branch
	# 	else:
	# 		return frappe.db.get_value('Process Log', next_name, 'branch')

	# def update_serial_no_status(self, args):
	# 	if args.tailor_serial_no:
	# 		serial_no = cstr(args.tailor_serial_no).split('\n')
	# 		for sn in serial_no:
	# 			msg = self.process + ' ' + self.emp_status
	# 			parent = frappe.db.get_value('Process Log', {'process_data': self.name}, 'parent')
	# 			update_serial_no(parent, sn, msg)

	def find_start_time(self):
		self.start_date = now()

		return "Done"

	def find_to_time(self, date_type=None):
		import math
		if not date_type:
			self.end_date = self.date_formatting(now())
		if self.start_date and self.end_date:
			self.start_date = self.date_formatting(self.start_date)
			self.end_date = self.date_formatting(self.end_date)
			after = datetime.datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S') 
			before = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
			self.completed_time = cstr(math.floor(((after - before).total_seconds()) / 60))
		else:
			frappe.msgprint("Start Date is not mentioned")
		return {
		"completed_time":self.completed_time,
		"end_date":self.end_date
		}

	def date_formatting(self,date):
		date = get_datetime(date)
		date = datetime.datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
		return date

	def calculate_wage(self):
		if self.process_tailor:
			amount = frappe.db.sql(""" SELECT
   							 type_of_payment,
							    CASE
							        WHEN type_of_payment='Amount'
							        THEN cost
							        WHEN type_of_payment='Percent'
							        THEN total_percentage
							    END  as amount
							FROM
							    `tabEmployeeSkill`
							WHERE
							    process='{0}'
							AND item_code='{1}' and parent='{2}'  """.format(self.process,self.item,self.process_tailor),as_dict=1)
			
			trial_cost = 0.0
			tailor_cost = 0.0
			
			serial_list = self.serial_no_data.split('\n')
			serial_list = [serial for serial in serial_list if serial]
			
			if self.process_trials:
				trial_cost = self.calculate_trial_cost()
			
			for serial_no in serial_list:
				check_dict = self.get_dic_List(serial_no)
				if frappe.db.get_value('Serial No Detail', check_dict, 'extra_style_cost_given') == 'Yes':
					break
			else:		
				if self.process_trials == 1 or not self.process_trials:
					tailor_cost = self.calculate_process_wise_tailor_cost()

			if amount:
				if amount[0].get('type_of_payment') == 'Percent' and self.payment=='Yes':
					self.wages_for_single_piece =  ( (( flt(self.total_invoice_amount) - flt(self.total_expense) ) * flt(amount[0].get('amount')/100))  +  trial_cost  + tailor_cost )
					self.wages = flt(self.wages_for_single_piece) * flt(len(serial_list))
				if amount[0].get('type_of_payment') == 'Amount' and self.payment =='Yes':
					self.wages_for_single_piece = flt(amount[0].get('amount')) + trial_cost + tailor_cost
					self.wages = flt(self.wages_for_single_piece) * flt(len(serial_list))
			else:
				self.wages_for_single_piece =  trial_cost + tailor_cost
				self.wages = flt(self.wages_for_single_piece) * flt(len(serial_list))			
	# def make_stock_entry(self, t_branch, args):
	# 	ste = frappe.new_doc('Stock Entry')
	# 	ste.purpose_type = 'Material Out'
	# 	ste.purpose ='Material Issue'
	# 	self.stock_entry_of_child(ste, args, t_branch)
	# 	ste.branch = get_user_branch()
	# 	ste.save(ignore_permissions=True)
	# 	return ste.name

	# def stock_entry_of_child(self, obj, args, target_branch):
	# 	ste = obj.append('mtn_details', {})
	# 	ste.s_warehouse = get_branch_warehouse(self.branch)
	# 	ste.target_branch = target_branch
	# 	ste.t_warehouse = get_branch_warehouse(target_branch)
	# 	ste.qty = args.get('qty')
	# 	ste.serial_no = args.get('serial_data')
	# 	ste.incoming_rate = 1.0
	# 	ste.conversion_factor = 1.0
	# 	ste.work_order = args.get('work_order')
	# 	ste.item_code = args.get('item')
	# 	ste.item_name = frappe.db.get_value('Item', ste.item_code, 'item_name')
	# 	ste.stock_uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
	# 	company = frappe.db.get_value('GLobal Default', None, 'company')
	# 	ste.expense_account = frappe.db.get_value('Company', company, 'default_expense_account')
	# 	return "Done"

	# def get_details(self , cond):
	# 	name = frappe.db.sql("""SELECT ifnull(foo.name, '') AS current_name,  (SELECT  ifnull(name, '') FROM `tabProcess Log` 
	# 							WHERE name > foo.name AND parent = foo.parent order by process_data, trials limit 1) AS next_name
	# 							FROM ( SELECT  name, parent  FROM  `tabProcess Log` WHERE   branch = '%s' 
	# 							and status != 'Closed' and process_data = '%s' and %s ORDER BY idx limit 1) AS foo """%(self.branch, self.name, cond), as_dict=1, debug=1)
	# 	if name:
	# 		return name[0].current_name, name[0].next_name
	# 	else:
	# 		'',''

	def calculate_trial_cost(self):
		trial_cost = 0.0
		branch_dict = frappe.db.sql(""" SELECT 
						    branch_dict
						FROM
						    `tabProcess Item` as si
						WHERE
						    parent = '%s'
						    and process_name = '%s'   """%(self.item,self.process),as_list=1)
		if branch_dict[0][0] and self.process_trials:
			self.process_trials = cint(self.process_trials)
			branch_dict[0][0] = eval(branch_dict[0][0])
			trial_cost = flt(branch_dict[0][0].get("{0}".format(  cint(self.process_trials) - 1  )   ).get('cost'))
		return trial_cost

	
	def calculate_process_wise_tailor_cost(self):
		tailor_cost = 0.0
		self.extra_style_cost_given = 'No'	
		process_wise_tailor_cost = frappe.db.sql(""" SELECT
							    process_wise_tailor_cost
							FROM
							    `tabWO Style`
							WHERE
							    parent = '{0}'
							AND process_wise_tailor_cost LIKE "%{1}%"    """.format(self.work_order,self.process),as_list=1)
		if process_wise_tailor_cost:
			self.extra_style_cost_given = 'Yes'
			for row in process_wise_tailor_cost:
				tailor_cost += flt(eval(row[0]).get(self.process))
		return tailor_cost		

	def update_task(self):
		if self.emp_status=='Assigned' and not self.get("__islocal") and self.process_tailor:
			self.task = self.create_task()
			# self.update_work_order()
			if self.get('employee_details'):
				for d in self.get('employee_details'):
					if not d.tailor_task:
						d.tailor_task = self.task

	def update_work_order(self):
		if self.process_trials:
			fabric = ''
			data = frappe.db.sql(""" select a.work_order as work_order, ifnull(a.actual_fabric, '') as actual_fabric, b.pdd as pdd from `tabTrial Dates` a, `tabTrials` b where a.parent= b.name 
									 and b.work_order ='%s' and process = '%s' and trial_no = '%s'"""%(self.process_work_order, self.process, self.process_trials), as_dict=1)
			if data:
				for d in data:
					if cint(d.actual_fabric) == 1:
						fabric = frappe.db.get_value('Production Dashboard Details', d.pdd, 'fabric_code')
					else:
						fabric = frappe.db.get_value('Production Dashboard Details', d.pdd, 'dummy_fabric_code')
					if fabric:
						frappe.db.sql(""" update `tabWork Order` set fabric__code = '%s' and trial_no = '%s'
							where name = '%s'"""%(fabric, self.process_trials, d.work_order))			

	def create_task(self):
		self.validate_dates()
		tsk = frappe.new_doc('Task')
		tsk.subject = '%s for %s'%(self.process, frappe.db.get_value('Item',self.item,'item_name'))
		tsk.project = self.sales_invoice_no
		tsk.exp_start_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S').date()
		tsk.exp_end_date = datetime.datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S').date()
		tsk.status = 'Open'
		tsk.process_name = self.process
		tsk.item_code = self.item
		tsk.process_allotment_number = self.name
		tsk.sales_order_number = self.sales_invoice_no
		tsk.save(ignore_permissions=True)
		return tsk.name

	# def assigned_to_user(self, data):
	# 	todo = frappe.new_doc('ToDo')
	# 	todo.description = data.task_details or 'Do process %s for item %s'%(data.process, frappe.db.get_value('Item',self.item,'item_name'))
	# 	todo.reference_type = 'Task'
	# 	todo.reference_name = data.task
	# 	todo.owner = data.user
	# 	todo.save(ignore_permissions=True)
	# 	return todo.name

	# def validate_process(self, index):
	# 	for data in self.get('wo_process'):
	# 		if cint(data.idx)<index:
	# 			if data.status == 'Pending' and cint(data.skip)!=1:
	# 				frappe.throw(_("Previous Process is Pending, please check row {0} ").format(cint(data.idx)))

	# def on_submit(self):
	# 	self.check_status()
	# 	self.change_status('Completed')
	# 	# self.make_stock_entry_for_finished_goods()

	# def check_status(self):
	# 	for d in self.get('wo_process'):
	# 		if d.status =='Pending' and cint(d.skip)!=1:
	# 			frappe.throw(_("Process is Pending, please check row {0} ").format(cint(d.idx)))

	# def on_cancel(self):
	# 	self.change_status('Pending')
	# 	self.set_to_null()
	# 	self.delete_dependecy()
	
	# def change_status(self,status):
	# 	frappe.db.sql(""" update `tabProduction Dashboard Details` 
	# 				set process_status='%s' 
	# 				where sales_invoice_no='%s' and article_code='%s' 
	# 				and process_allotment='%s'"""%(status, self.sales_invoice_no, self.item, self.name))

	# def set_to_null(self):
	# 	frappe.db.sql(""" update `tabProduction Dashboard Details` 
	# 				set process_allotment= (select name from tabCustomer where 1=2) 
	# 				where sales_invoice_no='%s' and article_code='%s' 
	# 				and process_allotment='%s'"""%( self.sales_invoice_no, self.item, self.name))

	# def delete_dependecy(self):
	# 	for d in self.get('wo_process'):
	# 		if d.task and d.user:
	# 			frappe.db.sql("delete from `tabToDo` where reference_type='%s' and owner='%s'"%(d.task, d.user))
	# 			production_dict = self.get_dict(d.task, d.user)
	# 			delte_doctype_data(production_dict)

	# def get_dict(self, task, user):
	# 	return {'Task':{'name':task}}

	# def on_status_trigger_method(self, args):
	# 	self.set_completion_date(args)
	# 	self.update_process_status(args)

	# def set_completion_date(self, args):
	# 	for d in self.get('wo_process'):
	# 		if cint(d.idx) == cint(args.idx) and d.status == 'Completed':
	# 			d.completion_date = cstr(nowdate())
	# 		else:
	# 			d.completion_date = ''
	# 	return True

	# def make_stock_entry(self):
	# 	if self.get('issue_raw_material'):
	# 		create_se(self.get('issue_raw_material'))

	# def make_stock_entry_for_finished_goods(self):
	# 	ste = frappe.new_doc('Stock Entry')
	# 	ste.purpose = 'Manufacture/Repack'
	# 	ste.branch = get_user_branch()
	# 	ste.save(ignore_permissions=True)
	# 	self.make_child_entry(ste.name)
	# 	ste = frappe.get_doc('Stock Entry',ste.name)
	# 	ste.submit()
	# 	self.make_gs_entry()
	# 	return ste.name

	# def make_child_entry(self, name):
	# 	ste = frappe.new_doc('Stock Entry Detail')
	# 	ste.t_warehouse = 'Finished Goods - I'
	# 	ste.item_code = self.item
	# 	ste.serial_no = self.serials_data
	# 	ste.qty = self.finished_good_qty
	# 	ste.parent = name
	# 	ste.conversion_factor = 1
	# 	ste.has_trials = 'No'
	# 	ste.parenttype = 'Stock Entry'
	# 	ste.uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
	# 	ste.stock_uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
	# 	ste.incoming_rate = 1.00
	# 	ste.parentfield = 'mtn_details'
	# 	ste.expense_account = 'Stock Adjustment - I'
	# 	ste.cost_center = 'Main - I'
	# 	ste.transfer_qty = self.finished_good_qty
	# 	ste.save(ignore_permissions = True)
	# 	return "Done"

	# def make_gs_entry(self):
	# 	if self.serials_data:
	# 		parent = frappe.db.get_value('Production Dashboard Details',{'sales_invoice_no':self.sales_invoice_no,'article_code':self.item,'process_allotment':self.name},'name')
	# 		sn = cstr(self.serials_data).splitlines()
	# 		for s in sn:
	# 			if not frappe.db.get_value('Production Status Detail',{'item_code':self.item, 'serial_no':s[0]},'name'):
	# 				if parent:
	# 					pd = frappe.new_doc('Production Status Detail')
	# 					pd.item_code = self.item
	# 					pd.serial_no = s
	# 					pd.status = 'Ready'
	# 					pd.parent = parent
	# 					pd.save(ignore_permissions = True)
	# 		if parent:
	# 			frappe.db.sql("update `tabProduction Dashboard Details` set status='Completed', trial_no=0 where name='%s'"%(parent))
	# 	return "Done"

	# def update_process_status(self, args=None):
	# 	self.update_parent_status()
	# 	self.update_child_status()

	# def update_parent_status(self):
	# 	if self.process_status_changes=='Yes':
	# 		cond = "a.parent=b.name and a.process_data='%s' and a.process_name='%s' and b.sales_invoice_no='%s'"%(self.name, self.process, self.sales_invoice_no)
	# 		frappe.db.sql("update `tabProcess Log` a, `tabProduction Dashboard Details` b set a.status='%s' where %s"%(self.process_status,cond))
	# 		if self.process_status=='Closed':
	# 			self.open_next_status(cond)
	# 		self.process_status_changes='No'
		
	# def update_child_status(self):
	# 	for s in self.get('trials_transaction'):
	# 		if s.trial_change_status=='Yes':
	# 			cond = "a.parent=b.name and a.process_data='%s' and a.process_name='%s' and a.trials='%s' and b.sales_invoice_no='%s'"%(self.name, self.process, s.trial_no, self.sales_invoice_no)
	# 			frappe.db.sql("update `tabProcess Log` a, `tabProduction Dashboard Details` b set a.status='%s' where %s"%(s.status, cond))
	# 			if s.status=='Closed':
	# 				self.open_next_status(cond)
	# 			s.trial_change_status='No'

	# def open_next_status(self, cond):
	# 	name = frappe.db.sql("""select a.* from `tabProcess Log` a, `tabProduction Dashboard Details` b where %s """%(cond), as_dict=1)
	# 	if name:
	# 		for s in name:
	# 			frappe.db.sql("update `tabProcess Log` set status='Open' where idx=%s and parent='%s'"%(cint(s.idx)+1, s.parent))

	def assign_task_to_employee(self):
		self.validate_WorkOrder_ReleaseStatus()
		self.validate_Status()
		self.validate_for_completed_process()
		emp = self.append('employee_details',{})
		emp.employee = self.process_tailor
		emp.employee_name = frappe.db.get_value('Employee', self.process_tailor, 'employee_name')
		emp.employee_status = self.emp_status
		emp.tailor_payment = self.payment
		emp.tailor_wages = self.wages
		emp.tailor_process_trials = self.process_trials
		emp.employee_work_order = self.work_order
		emp.tailor_extra_wages = self.extra_charge
		emp.tailor_extra_amt = self.extra_charge_amount
		emp.tailor_from_time = self.start_date
		emp.work_estimated_time = self.estimated_time
		emp.work_completed_time = self.completed_time
		emp.assigned_work_qty = self.work_qty
		emp.deduct_late_work = self.deduct_late_work
		emp.latework = self.latework
		emp.tailor_serial_no = self.serial_no_data
		emp.cost = self.cost
		emp.wages_per_single_piece = flt(self.wages_for_single_piece)
		emp.tailor_wages = flt(self.wages)
		emp.qc_required = cint(self.qc)
		emp.extra_style_cost_given = self.extra_style_cost_given
		if self.emp_status == 'Assigned':
			self.task = self.create_task()
		elif self.emp_status == 'Completed':
			self.task = self.get_task()
			if self.task:
				emp.time_log_name = self.make_time_log(emp, self.task)
		emp.tailor_task = self.task
		if self.emp_status == 'Completed':
			self.add_to_completed_list()

		self.save()
		
		return "Done"

	def get_task(self):
		data = frappe.db.sql(''' select tailor_task from `tabEmployee Details` where parent = "%s"
			and employee = "%s" and tailor_serial_no = "%s" and (employee_status = "Assigned" or employee_status = "Completed")'''%(self.name, self.process_tailor, self.serial_no_data), as_list=1)
		if data:
			return data[0][0]
		else:
			val = self.create_task()
			return val
	
	def add_to_completed_list(self):
		self.serial_no_list = cstr(self.serial_no_list)
		self.serial_no_list +=  self.serial_no_data	+ '\n'

	def validate_for_completed_process(self):
		if not self.process_trials and self.emp_status == 'Assigned':
			sn_data = self.serial_no_data.split('\n')
			sn_data = [serial for serial in sn_data if serial]
			completed_sn_data = cstr(self.serial_no_list).split('\n')
			if sn_data:
				for serial_no in completed_sn_data:
					if serial_no in sn_data:
						frappe.throw("Serial No {0} is already completed.Please Assign Status as 'Reassigned' not 'Assigned' ".format(serial_no))


	def validate_Status(self):
		sn_data = cstr(self.serial_no_data).split('\n')
		if sn_data:
			for s in sn_data:
				if s:
					self.validate_processStatus(s) # to avoid duplicate  process status
					if self.emp_status == 'Reassigned' or self.emp_status == 'Completed':
						self.check_PreviousStaus(s) # To check sequence of status
					if self.emp_status == 'Assigned':
						self.check_PrevStatus(s) # Check prev is completed 
						self.Next_process_assign(s) # If next process open then current has no
						self.check_previous_process_assign(s)
					
	def check_PrevStatus(self, serial_no):
		if frappe.db.get_value('Serial No Detail', {'parent': serial_no}, 'name'):
			if self.process_trials:
				pdd, trial_no = self.get_PA_details('trial')
				if frappe.db.get_value('Serial No Detail', {'process_data': pdd, 'trial_no': trial_no, 'parent': serial_no}, 'status') != 'Completed' and cint(self.process_trials) != 1:
					frappe.throw(_("Previous trial is incompleted"))
				elif frappe.db.get_value('Serial No Detail', {'process_data': pdd, 'parent': serial_no}, 'status') != 'Completed':
					frappe.throw(_("Previous process is incompleted"))
			else:
				pdd, trial_no = self.get_PA_details('nontrial')
				if pdd:
					if frappe.db.get_value('Serial No Detail', {'process_data': pdd, 'parent': serial_no}, 'status') != 'Completed':
						frappe.throw(_("Previous process is incompleted"))

	def get_PA_details(self, type_of_trial):
		msg = None
		if type_of_trial == 'trial' and cint(self.process_trials) > 1:
			return self.name, cint(self.process_trials) - 1
		elif cint(frappe.db.get_value('Process Log', {'process_data': self.name, 'parent': self.pdd}, 'idx'))> 1:
			data = frappe.db.sql("""select process_data from `tabProcess Log` where parent='%s' and 
				process_data < '%s' limit 1"""%(self.pdd, self.name), as_list=1)
			if data:
				msg = data[0][0]
			return msg, 0
		else:
			return msg, 0

	def Next_process_assign(self, serial_no):
		data = frappe.db.sql("""select process_data from `tabProcess Log` where parent='%s' and 
				process_data > '%s' limit 1"""%(self.pdd, self.name), as_list=1)
		if data:
			if frappe.db.get_value('Serial No Detail', {'parent': serial_no, 'process_data': data[0][0]}, 'name'):
				frappe.throw(_("Not allow to make changes in current process"))

	def check_previous_process_assign(self, serial_no):
		data = frappe.db.sql("""select process_data from `tabProcess Log` where parent='%s' and 
				process_data < '%s' limit 1"""%(self.pdd, self.name), as_list=1)
		if data:
			if not frappe.db.get_value('Serial No Detail', {'parent': serial_no, 'process_data': data[0][0]}, 'name'):
				frappe.throw(_("Previous Process are uncomplete"))			

	def validate_processStatus(self, serial_no):
		check_dict = self.get_dic_List(serial_no)
		check_dict.setdefault('status', self.emp_status)
		if frappe.db.get_value('Serial No Detail', check_dict, 'name'):
			frappe.throw(_("Status {0} already defined For Serial No {1}").format(self.emp_status,serial_no))

	def check_PreviousStaus(self, serial_no):
		val = ['Assigned']
		if self.emp_status=='Completed':
			val.append('Reassigned')
		if self.emp_status == 'Reassigned':
			val.append('Completed')
			val.append('Assigned')
			val.append('Reassigned')	 
		check_dict = self.get_dic_List(serial_no)
		if frappe.db.get_value('Serial No Detail', check_dict, 'status') not in val:
			frappe.throw(_("Sequence is not correct or previous process is not Completed").format(self.emp_status))

	def get_dic_List(self, serial_no):
		check_dict = {'parent': serial_no, 'process_data': self.name}
		if self.process_trials:
			check_dict = {'parent': serial_no, 'process_data': self.name, 'trial_no': self.process_trials}
		return check_dict	

	def validate_WorkOrder_ReleaseStatus(self):
		if not frappe.db.get_value('Work Order', self.process_work_order, 'status') == 'Release':
			frappe.throw(_('Work order {0} must be Release').format(self.process_work_order))

	def cal_extra_chg(self):
		process_data = frappe.db.get_value('Process Item',{'parent':self.item, 'process_name':self.process, 'trials':1}, 'branch_dict')
		if process_data:
			process_data = eval(process_data)
			for s in process_data:
				if cint(self.process_trials) == cint(process_data[s]['trial']):
					self.extra_charge_amount = process_data[s]['cost']
		return True

	def calculate_estimates_time(self):
		if self.work_qty and self.start_date:
			self.estimated_time = cint(self.work_qty) * cint(frappe.db.get_value('EmployeeSkill',{'parent':self.process_tailor, 'process':self.process, 'item_code': self.item},'time'))
			self.start_date = self.date_formatting(self.start_date)
			self.end_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(minutes = cint(self.estimated_time))

		return "Done"

	def calculate_wages(self):
		self.wages = 0.0
		if self.payment == 'Yes':
			self.wages = cint(self.work_qty) * cint(frappe.db.get_value('EmployeeSkill',{'parent':self.process_tailor, 'process':self.process, 'item_code': self.item},'cost'))

	def calc_late_work_amt(self):
		self.cost = flt(self.latework) * flt(frappe.db.get_value('Item',self.item,"late_work_cost"))
		return "Done"

	def validate_dates(self):
		if not self.start_date and not self.end_date:
			frappe.throw(_('Start and End Date is necessary to create task'))

	def get_trial_serial_no(self):
		get_trials = frappe.db.get_value('Trials', {'work_order':self.process_work_order}, '*')
		self.serial_no_data = get_trials.trials_serial_no_status
		self.work_qty = 1
		return "Done"

	def create_se(self, raw_material):
		se = frappe.new_doc('Stock Entry')
		se.naming_series = 'STE-'
		se.purpose = 'Material Issue'
		se.posting_date = nowdate()
		se.posting_time = nowtime().split('.')[0]
		se.company = frappe.db.get_value("Global Defaults", None, 'default_company')
		se.fiscal_year = frappe.db.get_value("Global Defaults", None, 'current_fiscal_year')
		item_list = self.make_ChildSTE_Issue(se, raw_material)
		if item_list:
			se.submit()
			self.update_child_STE(se.name)
		return "Done"

	def update_child_STE(self, name):
		data = self.get('issue_raw_material')
		for d in data:
			if not d.issue_stock_entry:
				d.issue_stock_entry = name

	def make_ChildSTE_Issue(self, obj, raw_material):
		item_list = []
		for item in raw_material:
			if cint(item.selected) == 1 and item.status!='Issued':
				sed = obj.append('mtn_details')
				sed.s_warehouse = get_branch_warehouse(get_user_branch())
				company = frappe.db.get_value('Global Defaults', None, 'default_company')
				sed.expense_account = frappe.db.get_value('Company', company, 'default_expense_account') or 'Stock Adjustment - '+frappe.db.get_value('Company', company, 'abbr')
				sed.cost_center = get_branch_cost_center(get_user_branch()) or 'Main - '+frappe.db.get_value('Company', company, 'abbr')
				sed.item_code = item.raw_material_item_code
				sed.item_name = frappe.db.get_value("Item", item.raw_material_item_code, 'item_name')
				sed.description = frappe.db.get_value("Item", item.raw_material_item_code, 'description')
				sed.stock_uom = item.uom
				sed.uom = item.uom
				sed.conversion_factor = 1
				sed.incoming_rate = 1.0
				sed.qty = flt(item.qty)
				sed.transfer_qty = flt(item.qty) * 1
				sed.serial_no = item.serial_no
				item.status = 'Issued'
				item_list.append(item.name)
		return item_list

	def update_IssueItem_status(self, IssuedItem_list):
		if IssuedItem_list:
			for name in IssuedItem_list:
				frappe.db.sql(""" update `tabIssue Raw Material` set status= 'Completed'
					where name = '%s'"""%(name))


def get_employee_details(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" select name, employee_name from `tabEmployee` where name in (select distinct parent from `tabEmployeeSkill` where
		process = "%(process)s" and item_code = "%(item_code)s") and (name like "%%%(name)s%%" or employee_name like "%%%(name)s%%")
		order by name limit %(start)s, %(page_len)s 
		"""%{'process': filters.get('process'), 'item_code': filters.get('item_code'), 'name': txt, 'start': start, 'page_len': page_len})

def get_raw_serial_no(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('item_code'):
		return frappe.db.sql(""" select name, item_name from `tabSerial No` where item_code = "%(item_code)s" and (name like "%%%(name)s%%" or item_name like "%%%(name)s%%")
			order by name limit %(start)s, %(page_len)s 
			"""%{'item_code': filters.get('item_code'), 'name': txt, 'start': start, 'page_len': page_len})
	else:
		return [['']]