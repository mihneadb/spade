"""
Item pipeline.

"""
from django.core.files.base import ContentFile
from hashlib import sha256
from spade import model


class ScraperPipeline(object):
    def __init__(self):
        """Initialize pipeline with user agents."""
        # Get user agents from database


    def process_item(self, item, spider):
        """Called whenever an item is yielded by the spider"""

        # Javascript MIME types
        js_mimes = ('text/javascript',
                    'application/x-javascript',
                    'application/javascript')

        # Parse each file based on what its MIME specifies
        if 'text/html' == item['content_type']:
            # First save the request contents into a URLContent
            urlcontent = model.URLContent.objects.create(
                url_scan=item['urlscan'], user_agent=item['user_agent'])

            # Store raw markup
            file_content = ContentFile(item['raw_content'])
            urlcontent.raw_markup.save(item['filename'], file_content)
            urlcontent.raw_markup.close()

            # Store raw headers
            file_content = ContentFile(item['headers'])
            urlcontent.headers.save(item['filename'], file_content)
            urlcontent.headers.close()

            urlcontent.save()

        elif any(mime == item['content_type'] for mime in js_mimes):
            urlcontent = model.URLContent.objects.get(
                url_scan=item['urlscan'],
                user_agent=item['user_agent'])

            # If the linked file already exists, don't save another copy
            try:
                linkedjs = model.LinkedJS.objects.get(
                    url_hash=sha256(item['url']).hexdigest())

            except model.LinkedJS.DoesNotExist:
                print "DNE"
                # Create the item since it doesn't exist
                linkedjs = model.LinkedJS.objects.create(
                    url=item['url'],
                    url_hash=sha256(item['url']).hexdigest())

                # Store raw js
                file_content = ContentFile(item['raw_content'])
                linkedjs.raw_js.save(item['filename'], file_content)
                linkedjs.raw_js.close()

                linkedjs.save()

            # Create relationship with url content
            linkedjs.linked_from.add(urlcontent)

        elif 'text/css' == item['content_type']:
            urlcontent = model.URLContent.objects.get(
                url_scan=item['urlscan'],
                user_agent=item['user_agent'])

            # If the linked file already exists, don't save another copy
            try:
                linkedcss = model.LinkedCSS.objects.get(
                    url_hash=sha256(item['url']).hexdigest())

            except model.LinkedCSS.DoesNotExist:
                print "DNE"
                # Create the item since it doesn't exist
                linkedcss = model.LinkedCSS.objects.create(
                    url=item['url'],
                    url_hash=sha256(item['url']).hexdigest())

                # Store raw css
                file_content = ContentFile(item['raw_content'])
                linkedcss.raw_css.save(item['filename'], file_content)
                linkedcss.raw_css.close()

                linkedcss.save()

            # Create relationship with url content
            linkedcss.linked_from.add(urlcontent)

        return item

    def close_spider(self, spider):
        """ Executed on spider completion """
        # Update batch finish time, keep this last
        spider.batch.finish_time = spider.get_now_time()
        spider.batch.save()

    def open_spider(self, spider):
        """ Executed on spider launch """
        user_agents = list(model.UserAgent.objects.all())

        if not user_agents:
            raise ValueError(
                "No user agents; add some with 'manage.py useragents --add'")

        now = spider.get_now_time()

        # Create initial batch
        spider.batch = model.Batch.objects.create(
            kickoff_time=now, finish_time=now)
        spider.batch.save()

        # Give the spider a set of batch user agents, which preserve historical
        # user agent data
        for ua in user_agents:
            spider.batch_user_agents = []
            batch_user_agent = model.BatchUserAgent.objects.create(
                batch=spider.batch, ua_string=ua.ua_string)
            spider.batch_user_agents.append(batch_user_agent)

