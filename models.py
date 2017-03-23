from django.db import models
from jsonfield import JSONField


class FeedSubmission(models.Model):
	ACKNOWLEDGE = '_POST_ORDER_ACKNOWLEDGEMENT_DATA_'
	ADJUSTMENT = '_POST_PAYMENT_ADJUSTMENT_DATA_'
	FULFILLMENT = '_POST_ORDER_FULFILLMENT_DATA_'
	PRODUCT = '_POST_PRODUCT_DATA_'
	PRICES = '_POST_PRODUCT_PRICING_DATA_'
	INVENTORY = '_POST_INVENTORY_AVAILABILITY_DATA_'
	RELATIONSHIP = '_POST_PRODUCT_RELATIONSHIP_DATA_'
	IMAGE = '_POST_PRODUCT_IMAGE_DATA_'
	FEED_TYPES = (
		(ACKNOWLEDGE, 'Order Acknowledgement'),
		(ADJUSTMENT, 'Order Adjustment'),
		(FULFILLMENT, 'Order Fulfillment'),
		(PRODUCT, 'Products'),
		(PRICES, 'Prices'),
		(INVENTORY, 'Inventory'),
		(RELATIONSHIP, 'Relationships'),
		(IMAGE, 'Images'),
	)
	SUBMITTED = '_SUBMITTED_'
	DONE = '_DONE_'
	CANCELLED = '_CANCELLED_'
	IN_PROCESS = '_IN_PROGRESS_'
	SUBMISSION_STATUSES = (
		(SUBMITTED, 'Submitted'),
		(DONE, 'Done'),
		(CANCELLED, 'Cancelled'),
		(IN_PROCESS, 'In Process'),
	)
	feed_type = models.CharField(max_length=40, choices=FEED_TYPES)
	submission_id = models.CharField(max_length=15)
	processing_status = models.CharField(max_length=15, choices=SUBMISSION_STATUSES)
	messages_processed = models.PositiveIntegerField(null=True)
	messages_successful = models.PositiveIntegerField(null=True)
	messages_errored = models.PositiveIntegerField(null=True)
	messages_warned = models.PositiveIntegerField(null=True)


class FeedSubmissionDetail(models.Model):
	submission = models.ForeignKey(FeedSubmission)
	message_id = models.CharField(max_length=15)
	result = models.CharField(max_length=15)
	code = models.CharField(max_length=15)
	description = models.TextField(blank=True)
	additional_info = JSONField()
