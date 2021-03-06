# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded ,date_diff
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.setup.utils import get_company_currency
from erpnext.hr.utils import set_employee_name
import datetime

from erpnext.utilities.transaction_base import TransactionBase

class WeeklySalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname('Week Sal Slip/' +self.employee + '/.#####')

	def get_emp_and_leave_details(self):
		if self.employee:
			self.get_leave_details()
			# struct = self.check_sal_struct()
			# if struct:
			self.pull_sal_struct()
			self.pull_emp_details()

	def check_sal_struct(self):
		struct = frappe.db.sql("""select name from `tabSalary Structure`
			where employee=%s and is_active = 'Yes'""", self.employee)
		if not struct:
			msgprint(_("Please create Salary Structure for employee {0}").format(self.employee))
			self.employee = None
		return struct and struct[0][0] or ''

	def get_week_details(self,args):
		holidays = self.get_holidays_for_employee(args)
		self.total_days_in_month=7-len(holidays)

	def set_to_date(self,args):
		d2=add_days(args['month_start_date'],6)
		self.to_date=d2


	def pull_sal_struct(self):
		earnings_details, drawings_overtime_details ,loan_details = self.get_mapper_details()

		mapper = {'wages': ['Wages', earnings_details[0].get('wages') if len(earnings_details) > 0 else 0.0 ], 
		'extra_amt': ['Extra Charges', earnings_details[0].get('extra_amt') if len(earnings_details) > 0 else 0.0 ], 
		'overtime': ['Overtime', drawings_overtime_details[0].get('overtime') if len(drawings_overtime_details) > 0 else 0.0]}


		self.set('earning_details',[])
		for types in mapper:
			d = self.append('earning_details', {})
			d.e_type =mapper.get(types)[0]
			d.e_amount = mapper.get(types)[1]
			d.e_modified_amount = mapper.get(types)[1]

		mapper = {'drawings': ['Drawings', drawings_overtime_details[0].get('drawings') if len(drawings_overtime_details) > 0 else 0.0], 
				'loan': ['Loan',loan_details[0].get('emi')], 
				'late_work':['Late Work', earnings_details[0].get('cost') if len(earnings_details) > 0 else 0.0 ]}

		self.set('deduction_details',[])
		for types in mapper:
			d = self.append('deduction_details', {})
			d.d_type = mapper.get(types)[0]
			d.d_amount = mapper.get(types)[1]
			d.d_modified_amount = mapper.get(types)[1]

	def get_mapper_details(self):
		earnings_details = frappe.db.sql("""select ifnull(sum(tailor_wages),0.0) as wages , ifnull(sum(tailor_extra_amt),0.0) as extra_amt , ifnull(sum(cost),0.0) as cost, group_concat(ed.name) as name
						from `tabEmployee Details` ed, `tabTime Log` tl
							where employee_status = 'Completed' 
								and tailor_task is not null 
								and date(tl.to_time) BETWEEN date('%s') AND date('%s')
								and ed.tailor_task = tl.task
								and tl.name = ed.time_log_name
								and ed.employee = '%s'
						"""%(self.from_date,self.to_date, self.employee), as_dict=1)

		drawings_overtime_details = frappe.db.sql("""select sum(dd.drawing_amount) as drawings, sum(dd.overtime) as overtime, group_concat(name) as name from `tabDaily Drawing` dd 
				where dd.employee_id = '%(employee)s' 
					and ifnull(dd.flag, 'No') != 'Yes'
					and dd.date between STR_TO_DATE('%(from_date)s','%(format)s') 
						and  STR_TO_DATE('%(to_date)s','%(format)s')"""%{'format': '%Y-%m-%d', 
						'from_date': self.from_date, 'to_date': self.to_date, 'employee':self.employee},as_dict=1)

		loan_details=frappe.db.sql(""" select  group_concat(name) as name,sum(emi) as emi from `tabLoan` where employee_id='%(employee)s' and payment_type='Weekly'  and pending_amount > 0 AND docstatus !=2 and  ( STR_TO_DATE('%(from_date)s','%(format)s') between from_date and to_date  or  STR_TO_DATE('%(to_date)s','%(format)s') between from_date and to_date )"""
			%{'format': '%Y-%m-%d','from_date':self.from_date,'to_date':self.to_date,'employee':self.employee},as_dict=1)

		return earnings_details, drawings_overtime_details ,loan_details

	def pull_emp_details(self):
		emp = frappe.db.get_value("Employee", self.employee,
			["bank_name", "bank_ac_no",'branch','department','designation'], as_dict=1)
		if emp:
			self.bank_name = emp.bank_name
			self.bank_account_no = emp.bank_ac_no
			self.branch = emp.branch
			self.department = emp.department
			self.designation = emp.designation

	def get_leave_details(self, lwp=None):
		if not self.fiscal_year:
			self.fiscal_year = frappe.get_default("fiscal_year")
		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month

		"""code for holidays"""

		m = frappe.get_doc('Salary Manager').get_month_details(self.fiscal_year, self.month)
		holidays = self.get_holidays_for_employee(m)
		m["month_days"]=7

		if not cint(frappe.db.get_value("HR Settings", "HR Settings",
			"include_holidays_in_total_working_days")):
				m["month_days"] -= len(holidays)
				# week_days -= len(holidays)
				if m["month_days"] < 0:
					frappe.throw(_("There are more holidays than working days this month."))
		if not lwp:
			lwp = self.calculate_lwp(holidays, m)
		self.total_days_in_month = m['month_days']
		self.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(m)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0


	def get_payment_days(self, m):
		payment_days = m['month_days']
		emp = frappe.db.sql("select date_of_joining, relieving_date from `tabEmployee` \
			where name = %s", self.employee, as_dict=1)[0]
		if emp['relieving_date']:
			if getdate(emp['relieving_date']) > m['month_start_date'] and \
				getdate(emp['relieving_date']) < m['month_end_date']:
					payment_days = getdate(emp['relieving_date']).day
			elif getdate(emp['relieving_date']) < m['month_start_date']:
				frappe.throw(_("Employee relieved on {0} must be set as 'Left'").format(emp["relieving_date"]))

		if emp['date_of_joining']:
			if getdate(emp['date_of_joining']) > m['month_start_date'] and \
				getdate(emp['date_of_joining']) < m['month_end_date']:
					payment_days = payment_days - getdate(emp['date_of_joining']).day + 1					
			elif getdate(emp['date_of_joining']) > m['month_end_date']:
				payment_days = 0
		return payment_days

	def get_holidays_for_employee(self, m):

		holidays = frappe.db.sql("""select t1.holiday_date
			from `tabHoliday` t1, tabEmployee t2
			where t1.parent = t2.holiday_list and t2.name = %s
			and t1.holiday_date between %s and %s """,
			(self.employee,self.from_date ,self.to_date))
		if not holidays:
			holidays = frappe.db.sql("""select t1.holiday_date
				from `tabHoliday` t1, `tabHoliday List` t2
				where t1.parent = t2.name and ifnull(t2.is_default, 0) = 1
				and t2.fiscal_year = %s
				and t1.holiday_date between %s and %s""", (self.fiscal_year,
					self.from_date ,self.to_date))
		holidays = [cstr(i[0]) for i in holidays]
		return holidays

	def calculate_lwp(self, holidays, m):
		lwp = 0
		for d in range(m['month_days']):
			dt = add_days(cstr(m['month_start_date']), d)
			if dt not in holidays:
				leave = frappe.db.sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2
					where t2.name = t1.leave_type
					and ifnull(t2.is_lwp, 0) = 1
					and t1.docstatus = 1
					and t1.employee = %s
					and %s between from_date and to_date
				""", (self.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
		return lwp

	def check_existing(self):
		ret_exist = frappe.db.sql("""SELECT
									    name
									FROM
									    `tabWeekly Salary Slip`
									WHERE
									    employee='%(employee)s'
									AND docstatus =1 AND salary_type='%(type_of_sal)s'
									AND (
									        STR_TO_DATE('%(from_date)s','%(format)s') BETWEEN from_date AND to_date
									    OR  STR_TO_DATE('%(to_date)s','%(format)s') BETWEEN from_date AND to_date
									    OR  from_date BETWEEN STR_TO_DATE('%(from_date)s','%(format)s') AND STR_TO_DATE('%(to_date)s',
									        '%(format)s')
									    OR  from_date BETWEEN STR_TO_DATE('%(from_date)s','%(format)s') AND STR_TO_DATE('%(to_date)s',
									        '%(format)s')  )
									AND fiscal_year = '%(fiscal_year)s'
									AND company = '%(company)s' """%{'format': '%Y-%m-%d','from_date':self.from_date,'to_date':self.to_date,'employee':self.employee,'fiscal_year':self.fiscal_year,'company':self.company,'type_of_sal':self.salary_type},as_list=1)					
		if ret_exist:
			frappe.throw(_(" Weekly Salary Slip of employee {0} already created for this month").format(self.employee))

	def validate(self):
		from frappe.utils import money_in_words
		self.check_existing()
		self.check_valid_dates()
		if not (len(self.get("earning_details")) or
			len(self.get("deduction_details"))):
				self.get_emp_and_leave_details()
		else:
			self.get_leave_details(self.leave_without_pay)

		if not self.net_pay:
			self.calculate_net_pay()

		if self.rounded_total < 0:
			frappe.throw("Weekly salary Slip can not be created for Employee {0} from period  {1} to {2} beacause Rounded Total Is less than 0 i.e [{3}] ".format(self.employee,self.from_date,self.to_date,self.rounded_total))	
		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

		set_employee_name(self)

	def check_valid_dates(self):
		if self.salary_type == 'Weekly':
			diff = date_diff(self.to_date,self.from_date)
			if diff != 6:
				frappe.throw("Dates not in same week")

	def calculate_earning_total(self):
		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		for d in self.get("earning_details"):
			if cint(d.e_depends_on_lwp) == 1:
				d.e_modified_amount = rounded(flt(d.e_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month), 2)
			elif not self.payment_days:
				d.e_modified_amount = 0
			else:
				d.e_modified_amount = d.e_amount
			self.gross_pay += flt(d.e_modified_amount)

	def calculate_ded_total(self):
		self.total_deduction = 0
		for d in self.get('deduction_details'):
			if cint(d.d_depends_on_lwp) == 1:
				d.d_modified_amount = rounded(flt(d.d_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month), 2)
			elif not self.payment_days:
				d.d_modified_amount = 0
			else:
				d.d_modified_amount = d.d_amount

			self.total_deduction += flt(d.d_modified_amount)

	def calculate_net_pay(self):
		self.calculate_earning_total()
		self.calculate_ded_total()
		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = rounded(self.net_pay)

	def on_submit(self):
		if(self.email_check == 1):
			self.send_mail_funct()

		earnings_details, drawings_overtime_details,loan_details = self.get_mapper_details()

		if len(earnings_details) > 0 and earnings_details[0].get('name') != None:
			for name in earnings_details[0].get('name').split(','):
				frappe.db.sql("""update `tabEmployee Details` set flag = 'Yes' where name = '%s'"""%name)
				frappe.db.sql("commit")

		if len(drawings_overtime_details) > 0 and drawings_overtime_details[0].get('name') != None:
			for name in drawings_overtime_details[0].get('name').split(','):
				frappe.db.sql("""update `tabDaily Drawing` set flag = 'Yes' where name = '%s'"""%name)
				frappe.db.sql("commit")

		if len(loan_details) > 0 and loan_details[0].get('name') != None:
			for name in loan_details[0].get('name').split(','):
				frappe.db.sql("""update `tabLoan` set pending_amount = (pending_amount - emi) where name = '%s'"""%name)
				frappe.db.sql("commit")


	def on_cancel(self):

		earnings_details, drawings_overtime_details,loan_details = self.get_mapper_details()
		
		if len(earnings_details) > 0 and earnings_details[0].get('name') != None:
			for name in earnings_details[0].get('name').split(','):
				frappe.db.sql("""update `tabEmployee Details` set flag = 'No' where name = '%s'"""%name)
				frappe.db.sql("commit")

		if len(drawings_overtime_details) > 0 and drawings_overtime_details[0].get('name') != None:
			for name in drawings_overtime_details[0].get('name').split(','):
				frappe.db.sql("""update `tabDaily Drawing` set flag = 'No' where name = '%s'"""%name)
				frappe.db.sql("commit")

		if len(loan_details) > 0 and loan_details[0].get('name') != None:
			for name in loan_details[0].get('name').split(','):
				frappe.db.sql("""update `tabLoan` set pending_amount = (pending_amount + emi) where name = '%s'"""%name)
				frappe.db.sql("commit")


	def send_mail_funct(self):
		from frappe.utils.email_lib import sendmail

		receiver = frappe.db.get_value("Employee", self.employee, "company_email")
		if receiver:
			subj = 'Salary Slip - ' + cstr(self.month) +'/'+cstr(self.fiscal_year)
			sendmail([receiver], subject=subj, msg = _("Please see attachment"),
				attachments=[{
					"fname": self.name + ".pdf",
					"fcontent": frappe.get_print_format(self.doctype, self.name, as_pdf = True)
				}])
		else:
			msgprint(_("Company Email ID not found, hence mail not sent"))
