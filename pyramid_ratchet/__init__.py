"""
Plugin for pyramid apps to submit errors to ratchet
"""

import json
import logging
import socket
import sys
import time
import traceback

from pyramid.httpexceptions import WSGIHTTPException
from pyramid.tweens import EXCVIEW
import requests


log = logging.getLogger(__name__)


def handle_error(settings, request):
    """
    Handle an error.

    Wrapper around _handle_error. Unless debug mode is on, calls _handle_error in a try-catch
    so that errors while reporting the error do not cause the application itself to crash.
    """
    if settings.get('debug') == 'true':
        _handle_error(settings, request)
    else:
        try:
            _handle_error(settings, request)
        except:
            log.exception("Error while reporting error to ratchet")


def _handle_error(settings, request):
    payload = {}
    payload['access_token'] = settings['access_token']
    payload['timestamp'] = int(time.time())

    cls, exc, trace = sys.exc_info()
    payload['body'] = "".join(traceback.format_exception(cls, exc, trace))

    params = {}
    params['request.url'] = request.url
    params['request.GET'] = dict(request.GET)
    params['request.POST'] = dict(request.POST)
    params['server.host'] = socket.gethostname()
    params['server.environment'] = settings.get('environment')
    params['server.branch'] = settings.get('branch')
    params['server.root'] = settings.get('root')
    params['server.github.account'] = settings.get('github.account')
    params['server.github.repo'] = settings.get('github.repo')
    params['notifier.name'] = 'pyramid_plugin'
    payload['params'] = json.dumps(params)

    requests.post(settings['endpoint'], data=payload, timeout=1)


def parse_settings(settings):
    prefix = 'ratchet.'
    out = {}
    for k, v in settings.iteritems():
        if k.startswith(prefix):
            out[k[len(prefix):]] = v
    return out


def ratchet_tween_factory(pyramid_handler, registry):
    settings = parse_settings(registry.settings)

    whitelist = ()
    blacklist = (WSGIHTTPException,)

    def ratchet_tween(request):
        try:
            response = pyramid_handler(request)
        except whitelist:
            handle_error(settings, request)
            raise
        except blacklist:
            raise
        except:
            handle_error(settings, request)
            raise
        return response

    return ratchet_tween


def includeme(config):
    config.add_tween('pyramid_ratchet.ratchet_tween_factory', under=EXCVIEW)

