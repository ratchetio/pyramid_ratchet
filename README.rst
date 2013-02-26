This library is deprecated, please use pyrollbar_
=================================================

pyramid_ratchet
===============

pyramid_ratchet is a simple middleware for reporting errors from Pyramid apps to Ratchet.io_. 

If pyramid_debugtoolbar is available, it will be monkey-patched so that exception pages show a link to the relevant item in Ratchet.io.


Requirements
------------
pyramid_ratchet requires:

- Python 2.6 or 2.7
- Pyramid 1.2+
- requests 0.12+
- a Ratchet.io `error reporting`_ account


Installation
------------
Install using pip::
    
    pip install pyramid_ratchet


Configuration
-------------
Add pyramid_ratchet to the *end* of your ``pyramid.includes``::
    
    [app:main]
    pyramid.includes =
        pyramid_debugtoolbar
        pyramid_ratchet

Add the bare minimum configuration variables::

    [app:main]
    ratchet.access_token = 32charactertoken

Most users will want a few extra settings to take advantage of more features::

    [app:main]
    ratchet.access_token = 32charactertoken
    ratchet.environment = production
    ratchet.branch = master
    ratchet.root = %(here)s

To enable Person tracking (to associate errors with users), attach a "ratchet_person" property to your ``request`` objects. It should return a dictionary containing an 'id' identifying the user (any string up to 40 characters), and may optionally include 'username' and 'email' (255-char strings). For example:

    class MyRequest(pyramid.request.Request):
        @property
        def ratchet_person(self):
            return {
                'id': get_user_id(self),
                'username': get_username(self),
                'email': get_user_email(self)
            }

    # when setting up your Configurator:
    config = Configurator(settings=settings, request_factory=MyRequest)

If your request objects don't have a ratchet_person object, pyramid_ratchet will look for request.user_id instead.


Here's the full list of configuration variables:

access_token
    Access token from your Ratchet.io project
handler
    One of:

    - blocking -- runs in main thread
    - thread -- spawns a new thread
    - agent -- writes messages to a log file for consumption by ratchet-agent_

    **default:** ``thread``
environment
    Environment name. Any string up to 255 chars is OK. For best results, use "production" for your production environment.
root
    Absolute path to the root of your application, not including the final ``/``. ``%(here)s`` is probably what you want.
branch
    Name of the checked-out branch.

    **default:** ``master``
agent.log_file
    If ``handler`` is ``agent``, the path to the log file. Filename must end in ``.ratchet``
allow_test
    When true, adds a hook to send a test error report (but not interrupt the request in any other way) whenever the query string contains ``pyramid_ratchet_test=true``.

    **default:** ``true``
endpoint
    URL items are posted to.
    
    **default:** ``https://submit.ratchet.io/api/1/item/``
web_base
    Base URL of the Ratchet.io web interface (used for links on the exception debug page)

    **default** ``https://ratchet.io``
patch_debugtoolbar
    If true, pyramid_debugtoolbar will be monkeypatched so that exception debug pages include a link to the item in Ratchet.io

    **default** ``true``
scrub_fields
    List of field names to scrub out of POST. Values will be replaced with astrickses. If overridiing, make sure to list all fields you want to scrub, not just fields you want to add to the default. Param names are converted to lowercase before comparing against the scrub list.

    **default** ``['passwd', 'password', 'secret']``


Contributing
------------

Contributions are welcome. The project is hosted on github at http://github.com/ratchetio/pyramid_ratchet


Additional Help
---------------
If you have any questions, feedback, etc., drop us a line at support@ratchet.io


.. _pyrollbar: https://github.com/rollbar/pyrollbar
.. _Ratchet.io: http://ratchet.io/
.. _error reporting: http://ratchet.io/
.. _ratchet-agent: http://github.com/ratchetio/ratchet-agent
