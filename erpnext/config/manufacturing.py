from frappe import _

def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "BOM",
					"description": _("Bill of Materials (BOM)"),
					"label": _("Bill of Material")
				},
				{
					"type": "doctype",
					"name": "Production Order",
					"description": _("Orders released for production."),
				},
				# {
				# 	"type": "doctype",
				# 	"name": "Item",
				# 	"description": _("All Products or Services."),
				# },
				{
					"type": "doctype",
					"name": "Work Management",
					"description": _("Where manufacturing operations are carried out."),
				},
				{
					"type": "doctype",
					"name": "Process Allotment",
					"description": _("Cut Order"),
				},
				{
					"type": "doctype",
					"name": "Cut Order Dashboard",
					"description": _("Cut Order"),
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
					"description": _("Quality Inspection"),
				},
				{
					"type": "doctype",
					"name": "Work Order",
					"description": _("Work Order"),
				},
				{
					"type": "doctype",
					"name": "Stock Entry",
					"description": _("Stock Entry"),
				},


			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Production Planning Tool",
					"description": _("Generate Material Requests (MRP) and Production Orders."),
				},
				{
					"type": "doctype",
					"name": "BOM Replace Tool",
					"description": _("Replace Item / BOM in all BOMs"),
				},
			]
		},
		{
			"label": _("Standard Reports"),
			"icon": "icon-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Open Production Orders",
					"doctype": "Production Order",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Production Orders in Progress",
					"doctype": "Production Order",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Issued Items Against Production Order",
					"doctype": "Production Order",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Completed Production Orders",
					"doctype": "Production Order",
					"icon":"icon-file-text"
				},
			]
		},
	]
