from frappe import _

def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Material Request",
					"description": _("Requests for items."),
				},
				{
					"type": "doctype",
					"name": "Stock Entry",
					"description": _("Record item movement."),
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"description": _("Shipments to customers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"description": _("Goods received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Item",
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"description": _("Where items are stored."),
				},
				{
					"type": "doctype",
					"name": "Serial No",
					"description": _("Single unit of an Item."),
				},
				{
					"type": "doctype",
					"name": "Batch",
					"description": _("Batch (lot) of an Item."),
				},
				{
					"type": "doctype",
					"icon": "icon-file-text",
					"name": "Barcode Label Print",
					"label": "Tailoring Product Barcode Label Print",
					"description": _("Batch (lot) of an Item."),
				},
			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Reconciliation",
					"description": _("Upload stock balance via csv.")
				},
				{
					"type": "doctype",
					"name": "Installation Note",
					"description": _("Installation record for a Serial No.")
				},
				{
					"type": "doctype",
					"name": "Packing Slip",
					"description": _("Split Delivery Note into packages.")
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
					"description": _("Incoming quality inspection.")
				},
				{
					"type": "doctype",
					"name": "Landed Cost Voucher",
					"description": _("Update additional costs to calculate landed cost of items"),
				},
				{
					"type": "doctype",
					"name": "Stock UOM Replace Utility",
					"description": _("Change UOM for an Item."),
				},
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Settings",
					"description": _("Default settings for stock transactions.")
				},
				{
					"type": "page",
					"name": "Sales Browser",
					"icon": "icon-sitemap",
					"label": _("Item Group Tree"),
					"link": "Sales Browser/Item Group",
					"description": _("Tree of Item Groups."),
					"doctype": "Item Group",
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
					"description": _("e.g. Kg, Unit, Nos, m")
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"description": _("Warehouses.")
				},
				{
					"type": "doctype",
					"name": "Brand",
					"description": _("Brand master.")
				},
				{
					"type": "doctype",
					"name": "Price List",
					"description": _("Price List master.")
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _("Multiple Item prices."),
					"route": "Report/Item Price"
				},
			]
		},
		{
			"label": _("Main Reports"),
			"icon": "icon-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ledger",
					"doctype": "Item",
					"icon":"icon-file-text"
				},
				{
					"type": "page",
					"name": "stock-balance",
					"label": _("Stock Balance"),
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Projected Qty",
					"doctype": "Item",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ageing",
					"doctype": "Item",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": False,
					"name": "Item-wise Price List Rate",
					"doctype": "Item Price",
					"icon":"icon-file-text"
				},
				{
					"type": "page",
					"name": "stock-analytics",
					"label": _("Stock Analytics"),
					"icon":"icon-file-text"
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
					"name": "Ordered Items To Be Delivered",
					"doctype": "Delivery Note",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Items To Be Received",
					"doctype": "Purchase Receipt",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"name": "Item Shortage Report",
					"route": "Report/Bin/Item Shortage Report",
					"doctype": "Purchase Receipt",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"name": "Serial No Service Contract Expiry",
					"doctype": "Serial No",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"name": "Serial No Status",
					"doctype": "Serial No",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"name": "Serial No Warranty Expiry",
					"doctype": "Serial No",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Transferred",
					"doctype": "Material Request",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Batch-Wise Balance History",
					"doctype": "Batch",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Warehouse-Wise Stock Balance",
					"doctype": "Warehouse",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Prices",
					"doctype": "Price List",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Itemwise Recommended Reorder Level",
					"doctype": "Item",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Delivery Note Trends",
					"doctype": "Delivery Note",
					"icon":"icon-file-text"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Receipt Trends",
					"doctype": "Purchase Receipt",
					"icon":"icon-file-text"
				},
			]
		},
	]
