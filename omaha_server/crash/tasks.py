# coding: utf8

"""
This software is licensed under the Apache 2 license, quoted below.

Copyright 2014 Crystalnix Limited

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""

import os
import logging

from furl import furl
from clom.shell import CommandError

from omaha_server.celery import app
from crash.models import Crash
from crash.settings import S3_MOUNT_PATH
from crash.utils import (
    get_stacktrace,
    FileNotFoundError,
    parse_stacktrace,
    get_signature,
    send_stacktrace_sentry,
)


logger = logging.getLogger(__name__)


@app.task(name='tasks.processing_crash_dump', ignore_result=True, max_retries=12, bind=True)
def processing_crash_dump(self, crash_pk):
    try:
        crash = Crash.objects.get(pk=crash_pk)
        url = furl(crash.upload_file_minidump.url)
        path = url.pathstr
        crash_dump_path = os.path.join(S3_MOUNT_PATH, *path.split('/'))
        stacktrace, errors = get_stacktrace(crash_dump_path)
        crash.stacktrace = stacktrace
        crash.stacktrace_json = parse_stacktrace(stacktrace)
        crash.signature = get_signature(crash.stacktrace_json)
        crash.save()
        send_stacktrace_sentry(crash)
    except FileNotFoundError as exc:
        logger.error('Failed processing_crash_dump',
                     exc_info=True,
                     extra=dict(crash_pk=crash_pk,
                                crash_dump_path=crash_dump_path))
        raise self.retry(exc=exc, countdown=2 ** processing_crash_dump.request.retries)
    except CommandError as exc:
        logger.error('Failed processing_crash_dump',
                     exc_info=True,
                     extra=dict(crash_pk=crash_pk,
                                crash_dump_path=crash_dump_path))
        raise exc
