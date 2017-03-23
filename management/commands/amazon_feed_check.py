from mws.mws import MWSError

from django.core.management.base import BaseCommand

from amazon.client import AmazonClient
from amazon.models import FeedSubmission, FeedSubmissionDetail


class Command(BaseCommand):
	args = '<submission_id submission_id ...>'
	help = 'Update feed submission status'
	pending_statuses = [FeedSubmission.SUBMITTED, FeedSubmission.IN_PROCESS]

	def handle(self, *args, **options):
		arg_submission_ids = [submission_id for submission_id in args]
		submissions = FeedSubmission.objects.filter(processing_status__in=self.pending_statuses)
		if arg_submission_ids:
			submissions = submissions.filter(submission_id__in=arg_submission_ids)
		client = AmazonClient()
		submission_ids = submissions.values_list('submission_id', flat=True)
		list_results = client.get_feed_list(submission_ids)
		for submission in submissions:
			if submission.submission_id in list_results and list_results[submission.submission_id]['processing_status'] not in self.pending_statuses:
				if list_results[submission.submission_id]['processing_status'] == FeedSubmission.CANCELLED:
					submission.processing_status = list_results[submission.submission_id]['processing_status']
					submission.save()
				else:
					try:
						result = client.get_feed_result(submission.submission_id)
						if result:
							submission.processing_status = list_results[submission.submission_id]['processing_status']
							submission.messages_processed = result['processed']
							submission.messages_successful = result['success']
							submission.messages_errored = result['error']
							submission.messages_warned = result['warning']
							for detail in result['detail']:
								submission.feedsubmissiondetail_set.add(FeedSubmissionDetail(**detail))
							submission.save()
					except MWSError:
						# Error getting result from Amazon. Try again later.
						pass
