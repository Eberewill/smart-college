app_name = "college_management"
app_title = "College Management System"
app_publisher = "Willex Tech"
app_description = "Configurable production-grade college management system"
app_email = "support@willextech.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "college_management",
# 		"logo": "/assets/college_management/logo.png",
# 		"title": "College Management System",
# 		"route": "/college_management",
# 		"has_permission": "college_management.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/college_management/css/college_management.css"
# app_include_js = "/assets/college_management/js/college_management.js"

# include js, css files in header of web template
# web_include_css = "/assets/college_management/css/college_management.css"
# web_include_js = "/assets/college_management/js/college_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "college_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "college_management/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "college_management.utils.jinja_methods",
# 	"filters": "college_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "college_management.install.before_install"
after_install = "college_management.setup.install_roles"
after_migrate = "college_management.setup.install_roles"

standard_portal_menu_items = [
	{"title": "Admissions", "route": "/admissions", "role": "Applicant"},
]

# Uninstallation
# ------------

# before_uninstall = "college_management.uninstall.before_uninstall"
# after_uninstall = "college_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "college_management.utils.before_app_install"
# after_app_install = "college_management.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "college_management.utils.before_app_uninstall"
# after_app_uninstall = "college_management.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "college_management.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "college_management.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

AUDITED_DOCTYPES = (
	"Institution",
	"Campus",
	"Faculty",
	"Department",
	"Academic Session",
	"Academic Semester",
	"Academic Level",
	"Course Category",
	"Programme",
	"Course",
	"Curriculum Version",
	"Staff Profile",
	"Admission Cycle",
	"Admission Programme",
	"Applicant Profile",
	"Admission Application",
	"Payment Gateway Configuration",
	"Application Invoice",
	"Application Payment Transaction",
	"Payment Webhook Event",
	"Application Payment Receipt",
	"Admission Review",
	"Admission Decision",
	"Admission Letter",
	"Student Profile",
)

doc_events = {
	doctype: {
		"on_update": "college_management.audit.record_update",
		"after_delete": "college_management.audit.record_delete",
	}
	for doctype in AUDITED_DOCTYPES
}
doc_events["User"] = {"on_update": "college_management.identity.user_updated"}
doc_events["File"] = {
	"before_save": "college_management.college_management_system.doctype.admission_application.admission_application.protect_submitted_application_file",
	"on_trash": "college_management.college_management_system.doctype.admission_application.admission_application.protect_submitted_application_file",
}

has_permission = {
	"Admission Application": "college_management.college_management_system.doctype.admission_application.admission_application.has_permission",
	"Application Invoice": "college_management.college_management_system.doctype.application_invoice.application_invoice.has_permission",
	"Application Payment Transaction": "college_management.college_management_system.doctype.application_payment_transaction.application_payment_transaction.has_permission",
	"Application Payment Receipt": "college_management.college_management_system.doctype.application_payment_receipt.application_payment_receipt.has_permission",
	"Admission Review": "college_management.college_management_system.doctype.admission_review.admission_review.has_permission",
	"Admission Decision": "college_management.college_management_system.doctype.admission_decision.admission_decision.has_permission",
	"Admission Letter": "college_management.college_management_system.doctype.admission_letter.admission_letter.has_permission",
	"Student Profile": "college_management.college_management_system.doctype.student_profile.student_profile.has_permission",
	"File": "college_management.college_management_system.doctype.admission_application.admission_application.has_file_permission",
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"college_management.tasks.all"
# 	],
# 	"daily": [
# 		"college_management.tasks.daily"
# 	],
# 	"hourly": [
# 		"college_management.tasks.hourly"
# 	],
# 	"weekly": [
# 		"college_management.tasks.weekly"
# 	],
# 	"monthly": [
# 		"college_management.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "college_management.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "college_management.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "college_management.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "college_management.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["college_management.utils.before_request"]
# after_request = ["college_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["college_management.utils.before_job"]
# after_job = ["college_management.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"college_management.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
