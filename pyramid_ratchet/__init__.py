"""
Plugin for pyramid apps to submit errors to ratchet
"""

import json
import logging
import socket
import sys
import threading
import time
import traceback

from pyramid.httpexceptions import WSGIHTTPException
from pyramid.tweens import EXCVIEW
import requests


log = logging.getLogger(__name__)
agent_log = None


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
    # expand headers, plays more nicely for processing
    for k, v in request.headers.iteritems():
        params['request.headers.%s' % k] = v
    params['request.user_ip'] = _extract_user_ip(request)
    params['server.host'] = socket.gethostname()
    params['server.environment'] = settings.get('environment')
    params['server.branch'] = settings.get('branch')
    params['server.root'] = settings.get('root')
    params['server.github.account'] = settings.get('github.account')
    params['server.github.repo'] = settings.get('github.repo')
    params['notifier.name'] = 'pyramid_ratchet'
    payload['params'] = json.dumps(params)

    handler = settings.get('handler', 'thread')
    if handler == 'blocking':
        _send_payload(settings, payload)
    elif handler == 'thread':
        thread = threading.Thread(target=_send_payload, args=(settings, payload))
        thread.start()
    elif handler == 'agent':
        _write_for_agent(settings, payload)


def _send_payload(settings, payload):
    requests.post(settings['endpoint'], data=payload, timeout=1)


def _write_for_agent(settings, payload):
    # create log if it doesn't exist
    global agent_log
    if not agent_log:
        agent_log = logging.getLogger('ratchet_agent')
        handler = logging.FileHandler(settings.get('agent.log_file', 'log.ratchet'), 'a', 'utf-8')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        agent_log.addHandler(handler)
        agent_log.setLevel(logging.WARNING)

    # write json line
    agent_log.error(json.dumps(payload))


def _extract_user_ip(request):
    # some common things passed by load balancers... will need more of these.
    real_ip = request.headers.get('X-Real-Ip')
    if real_ip:
        return real_ip
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for
    return request.remote_addr


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

