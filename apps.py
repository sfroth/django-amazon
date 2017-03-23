from appconf import AppConf
from django.apps import AppConfig


class AmazonConfig(AppConfig):
	name = 'amazon'
	verbose_name = "Amazon"

	def ready(self):
		from . import checks


class AmazonConf(AppConf):
	SELLER_ID = None
	ACCESS_KEY = None
	SECRET_KEY = None
	MARKETPLACE_IDS = []
	SHIPPING_MAP = {
		'Standard': 'USPS Mail',
		'SecondDay': '2nd Day',
	}
	MERCHANT_ID = None
	COLOR_MAPS = {}
	SIZE_MAPS = {}
	ITEM_TYPES = {}
	DEFAULT_ITEM_TYPE = None
	PRODUCT_TYPES = {}
	DEFAULT_PRODUCT_TYPE = None
	CLOTHING_TYPES = {}
	DEFAULT_CLOTHING_TYPE = None
	DEPARTMENTS = {}
	DEFAULT_DEPARTMENT = None
	OVERRIDE_CUSTOMER_EMAIL = None
	FBA_ENABLED = False
	DEFAULT_BRAND = None
	DEFAULT_MANUFACTURER = None
	VARIATION_CODE = '{variation_code}'
	ITEM_CODE = '{variation_code} {item_name}'
	ITEM_LOOKUP_REGEX = '^(?P<variation_code>[^ ]*) (?P<item_name>[^ ]*)$'
	SHOW_FEED_ADMIN = False

	class Meta:
		prefix = 'amazon'
