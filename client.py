import re
import pytz
from datetime import datetime
from lxml import etree

from mws.mws import Orders, Reports, Feeds, Inventory, OutboundShipments, MWSError

from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.six import StringIO
from django.conf import settings

from .models import FeedSubmission


def get_item_from_amazon_sku(item_manager, amazon_sku):
	r = re.compile(settings.AMAZON_ITEM_LOOKUP_REGEX)
	m = r.match(amazon_sku)
	if not m:
		return None
	sku_dict = m.groupdict()
	items = item_manager.all()
	if 'item_code' in sku_dict:
		items = items.filter(code=sku_dict['item_code'])
	if 'item_name' in sku_dict:
		items = items.filter(name=sku_dict['item_name'])
	if 'variation_code' in sku_dict:
		items = items.filter(variation__code=sku_dict['variation_code'])
	if 'product_code' in sku_dict:
		items = items.filter(variation__product__code=sku_dict['product_code'])
	return items.first()


class AmazonClient(object):
	TIMEFORMAT = "%Y-%m-%dT%H:%M:%SZ"

	def __init__(self, *args, **kwargs):
		self.credentials = {
			'access_key': settings.AMAZON_ACCESS_KEY,
			'secret_key': settings.AMAZON_SECRET_KEY,
			'account_id': settings.AMAZON_SELLER_ID,
			'region': kwargs.pop('region', 'US'),
		}

	def get_orders(self, start, end):
		return self.order_client().list_orders(marketplaceids=settings.AMAZON_MARKETPLACE_IDS, lastupdatedafter=start.strftime(self.TIMEFORMAT), lastupdatedbefore=end.strftime(self.TIMEFORMAT), orderstatus=['Unshipped', 'PartiallyShipped'])

	def get_order(self, amazon_order_id):
		return self.order_client().get_order(amazon_order_ids=[amazon_order_id])

	def get_order_items(self, amazon_order_id):
		return self.order_client().list_order_items(amazon_order_id)

	def get_latest_settlement_report(self):
		return Reports(**self.credentials).get_report_list(max_count='1', types=['_GET_PAYMENT_SETTLEMENT_DATA_'])

	def get_report(self, report_id):
		return Reports(**self.credentials).get_report(report_id)

	def order_acknowledgement(self, items):
		self.submit_feed(FeedSubmission.ACKNOWLEDGE, self.build_feed_body('OrderAcknowledgement', items))

	def order_adjustment(self, items):
		self.submit_feed(FeedSubmission.ADJUSTMENT, self.build_feed_body('OrderAdustment', items))

	def order_fulfillment(self, items):
		self.submit_feed(FeedSubmission.FULFILLMENT, self.build_feed_body('OrderFulfillment', items))

	def product_feed(self, body):
		self.submit_feed(FeedSubmission.PRODUCT, body)

	def product_price_feed(self, body):
		self.submit_feed(FeedSubmission.PRICES, body)

	def product_inventory_feed(self, body):
		self.submit_feed(FeedSubmission.INVENTORY, body)

	def product_relationship_feed(self, body):
		self.submit_feed(FeedSubmission.RELATIONSHIP, body)

	def product_image_feed(self, body):
		self.submit_feed(FeedSubmission.IMAGE, body)

	def get_fba_inventory(self, skus=[], start=None):
		return Inventory(**self.credentials).list_inventory_supply(skus, start.strftime(self.TIMEFORMAT) if start else None)

	def order_client(self):
		return Orders(**self.credentials)

	def submit_feed(self, feed_type, body):
		result = Feeds(**self.credentials).submit_feed(feed=body.encode('utf-8'), feed_type=feed_type)
		try:
			FeedSubmission(feed_type=feed_type, submission_id=result.parsed['FeedSubmissionInfo']['FeedSubmissionId']['value'], processing_status=result.parsed['FeedSubmissionInfo']['FeedProcessingStatus']['value']).save()
		except (AttributeError, KeyError):
			pass

	def get_feed_list(self, feed_submission_ids):
		result = Feeds(**self.credentials).get_feed_submission_list(feedids=feed_submission_ids)
		response = {}
		submission_info = result.parsed['FeedSubmissionInfo']
		if not isinstance(submission_info, list):
			submission_info = [submission_info]
		for info in submission_info:
			# include other fields here later if necessary
			response[info['FeedSubmissionId']['value']] = {
				'processing_status': info['FeedProcessingStatus']['value'],
			}
		return response

	def get_feed_result(self, feed_submission_id):
		result = Feeds(**self.credentials).get_feed_submission_result(feed_submission_id)
		parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
		root = etree.fromstring(result.original.encode('UTF-8'), parser=parser)
		if root.find('Error') is not None:
			# error result
			raise MWSError(root.find('Error').find('Message').text)
		report = root.find('Message').find('ProcessingReport')
		summary = report.find('ProcessingSummary')
		response = {}
		# Purposely return empty response for incomplete - shouldn't happen, because Amazon returns a 404, which is raised as MWSError
		if report.find('StatusCode').text == 'Complete':
			response.update({
				'processed': int(summary.find('MessagesProcessed').text),
				'success': int(summary.find('MessagesSuccessful').text),
				'error': int(summary.find('MessagesWithError').text),
				'warning': int(summary.find('MessagesWithWarning').text),
				'detail': [],
			})
			for result in report.iter('Result'):
				detail = {
					'message_id': result.find('MessageID').text,
					'result': result.find('ResultCode').text,
					'code': result.find('ResultMessageCode').text,
					'description': result.find('ResultDescription').text,
					'additional_info': {},
				}
				if result.find('AdditionalInfo') is not None:
					for el in result.find('AdditionalInfo').iterchildren("*"):
						detail['additional_info'][el.tag] = el.text
				response['detail'].append(detail)
		return response

	def create_fulfillment_shipment(self, marketplaceid, order_id, order_reference, order_date, order_comment, address, items, fulfillment_action='Ship', shipping_speed='Standard', fulfillment_policy='FillOrKill', notification_emails=[]):
		return OutboundShipments(**self.credentials).create_fulfillment_order(marketplaceid, str(order_id), str(order_reference), order_date.strftime(self.TIMEFORMAT), order_comment, address, items, fulfillment_action, shipping_speed, fulfillment_policy, notification_emails)

	def preview_fulfillment_shipment(self, marketplaceid, address, items, shipping_speeds=['Standard', 'Expedited', 'Priority']):
		return OutboundShipments(**self.credentials).get_fulfillment_preview(marketplaceid, address, items, shipping_speeds)

	def update_fulfillment_shipment(self, marketplaceid, order_id, order_reference, order_date, order_comment, address, items, fulfillment_action='Ship', shipping_speed='Standard', fulfillment_policy='FillOrKill', notification_emails=[]):
		return OutboundShipments(**self.credentials).get_fulfillment_order(marketplaceid, str(order_id), str(order_reference), order_date.strftime(self.TIMEFORMAT), order_comment, address, items, fulfillment_action, shipping_speed, fulfillment_policy, notification_emails)

	def get_fulfillment_shipment(self, order_id):
		return OutboundShipments(**self.credentials).get_fulfillment_order(str(order_id))

	def list_fulfillment_shipments(self, start):
		return OutboundShipments(**self.credentials).list_all_fulfillment_orders(start.strftime(self.TIMEFORMAT))

	def get_fulfillment_package_details(self, package_number):
		return OutboundShipments(**self.credentials).get_package_tracking_details(package_number)

	def cancel_fulfillment_shipment(self, order_id):
		return OutboundShipments(**self.credentials).cancel_fulfillment_order(str(order_id))

	def build_feed_body(self, message_type, items):
		s = StringIO()
		handler = SimplerXMLGenerator(s, 'utf-8')
		handler.startDocument()
		handler.startElement('AmazonEnvelope', {'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xsi:noNamespaceSchemaLocation': 'amzn-envelope.xsd'})
		handler.startElement('Header', {})
		handler.addQuickElement('DocumentVersion', '1.01')
		handler.addQuickElement('MerchantIdentifier', settings.AMAZON_MERCHANT_ID)
		handler.endElement('Header')
		handler.addQuickElement('MessageType', message_type)
		handler.addQuickElement('PurgeAndReplace', 'false')

		for index, item in enumerate(items):
			handler.startElement('Message', {})
			handler.addQuickElement('MessageID', str(index + 1))
			handler.startElement(message_type, {})
			self.handle_dict(handler, item)
			handler.endElement(message_type)
			handler.endElement('Message')

		handler.endElement('AmazonEnvelope')
		return s.getvalue()

	def handle_dict(self, handler, items):
		for key, val in iter(items.items()):
			if isinstance(val, list):
				for item in val:
					if isinstance(val, dict):
						handler.startElement(key, {})
						self.handle_dict(handler, item)
						handler.endElement(key)
					else:
						handler.addQuickElement(key, str(val))
			else:
				if isinstance(val, dict):
					handler.startElement(key, {})
					self.handle_dict(handler, val)
					handler.endElement(key)
				else:
					handler.addQuickElement(key, str(val))
