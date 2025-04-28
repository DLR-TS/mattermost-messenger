"""
Copyright (C) DLR-TS 2024

Class :py:class:`MattermostSender` for sending messages to Mattermost

For documentation of Mattermost webhooks see
https://developers.mattermost.com/integrate/webhooks/incoming
"""


import os
import re
import json
from typing import Optional, cast
from urllib.parse import urlsplit
from http.client import HTTPConnection, HTTPSConnection, responses
from http import HTTPStatus
from threading import Lock



defaultTimeout:float = 10
"""Default timeout for :py:class:`MattermostSender`"""

envVarHttpsProxy = 'HTTPS_PROXY'
envVarHttpProxy = 'HTTP_PROXY'
envVarNoProxy = 'NO_PROXY'



class MattermostError(Exception):
    """Exception raised on any connection or sending problems"""



class MattermostSender:
    """Basic class to use a Mattermost webhook

    This class provides methods to connect to and disconnect from Mattermost,
    and to send messages to Mattermost.

    Connecting to Mattermost can also be done in a with context:

    .. code-block:: python

        with MattermostSender(webhook) as sender:
            sender.send(msg)
            sender.send(msg2)

    In that case the connection is kept until leaving the with statement.
    """

    def __init__(self, url:str, *, timeout:Optional[float]=None, defaultEmoji:Optional[str]=None,
                 channel:Optional[str]=None, proxy:Optional[str]=None):
        """
        :param url: URL of a Mattermost webhook
        :param timeout: Timeout for connecting and sending
        :param defaultEmoji: Mattermost emoji to use if none passed to :py:meth:`send`
        :param channel: Mattermost channel to post in. If set to :py:const:`None` (default)
            messages appear in the webhook's configured channel. Enter channel name
            as in the channel URL, *not* as displayed by Mattermost
        :param proxy: Address (including port) of a proxy server for http(s) requests
        """
        self._url = url
        splitResult = urlsplit(self._url, scheme='https')
        self._host = splitResult.netloc
        self._isHttps = ('https' == splitResult.scheme)
        self._timeout = timeout if timeout else defaultTimeout
        self._defaultEmoji = defaultEmoji
        self.channel = channel
        self._proxy = self._getFinalProxy(proxy)
        self._connection:Optional[HTTPConnection] = None
        self._lock = Lock()


    def _getFinalProxy(self, configProxy:Optional[str]) -> Optional[str]:
        """Determine final proxy setting

        If configProxy is set return that, else check for proxy environment
        variables.
        """
        if configProxy:
            return configProxy

        proxyVar = envVarHttpsProxy if self._isHttps else envVarHttpProxy
        envProxy = os.getenv(proxyVar)
        if not envProxy:
            return None

        envNoProxy = os.getenv(envVarNoProxy)
        if envNoProxy:
            noProxyPatterns = [ p.strip().replace('.', '\\.').replace('*', '[^.]*') for p in envNoProxy.split(',') ]
            for pattern in noProxyPatterns:
                if re.match(pattern, self._host):
                    return None
        return envProxy


    def __enter__(self):
        """Calls :py:meth:`connect` on entering the context

        :return: :py:class:`self`
        """
        self.connect()
        return self


    def __exit__(self, excType, excValue, traceback) -> None:
        """Calls :py:meth:`disconnect` on leaving the context

        :param excValue: see :py:meth:`object.__exit__` in `Python docs`_
        :param excType: see :py:meth:`object.__exit__` in `Python docs`_
        :param traceback: see :py:meth:`object.__exit__` in `Python docs`_

        .. _Python docs: https://docs.python.org/3/reference/datamodel.html#object.__exit__
        """
        self.disconnect()


    @property
    def timeout(self):
        """Timeout for http calls"""
        return self._timeout


    def isConnected(self) -> bool:
        """:return: Return :py:const:`True` if :py:obj:`self` is currently connected"""
        return bool(self._connection)


    def connect(self) -> None:
        """Establish a connection to the Mattermost webhook

        Successive calls are ignored if :py:meth:`isConnected` returns :py:const:`True`.

        :raise MattermostError: on any error
        """
        if self.isConnected():
            return

        try:
            ConnectionClass = HTTPSConnection if self._isHttps else HTTPConnection

            if self._proxy:
                proxyParts = urlsplit(self._proxy)
                assert isinstance(proxyParts.hostname, str)
                self._connection = ConnectionClass(proxyParts.hostname, port=proxyParts.port, timeout=self.timeout)
                assert isinstance(self._connection , HTTPConnection)
                self._connection.set_tunnel(self._host)
            else:
                self._connection = ConnectionClass(self._host, timeout=self.timeout)
        except Exception as ex:
            self._connection = None
            raise MattermostError(str(ex)) from ex


    def disconnect(self) -> None:
        """Disconnect from Mattermost webhook

        Successive calls are ignored if :py:meth:`isConnected` returns :py:const:`False`.

        :raise MattermostError: on any error
        """
        if not self.isConnected():
            return
        assert isinstance(self._connection, HTTPConnection)

        try:
            self._connection.close()
        except Exception as ex:
            raise MattermostError(str(ex)) from ex
        finally:
            self._connection = None


    def _makeHttpBody(self, msg:str, emoji:Optional[str]) -> str:
        """Creates an http body

        :param msg:   message to send to Mattermost
        :param emoji: Mattermost emoji for the message
        :return:      body as JSON string.

        If :py:obj:`emoji` evaluates to :py:const:`False` the :py:obj:`defaultEmoji`
        passed to :py:class:`MattermostSender` will be used instead.
        """
        data = { 'text': msg }

        if emoji:
            data['icon_emoji'] = emoji
        elif self._defaultEmoji:
            data['icon_emoji'] = self._defaultEmoji

        if self.channel:
            data['channel'] = self.channel

        return json.dumps(data)


    def _sendMessage(self, msg:str, emoji:Optional[str]) -> None:
        """Post message to the current connection

        :param msg:   passed to :py:meth:`_makeHttpBody`
        :param emoji: passed to :py:meth:`_makeHttpBody`
        :raise MattermostError: if the returned http status is not OK

        :py:obj:`self` has to be connected, otherwise an assertion fails.

        Calls :py:meth:`_makeHttpBody` to create the http request body.
        """
        assert self.isConnected()
        # Required to satisfy mypy type checker
        assert self._connection is not None

        headers = { 'Content-Type': 'application/json' }
        body = self._makeHttpBody(msg, emoji)
        self._connection.request('POST', self._url, body=body, headers=headers)

        response = self._connection.getresponse()
        # cleanup response (raises http.client.ResponseNotReady if not done)
        response.read()
        if HTTPStatus.OK != response.status:
            raise MattermostError(f"Mattermost replied with http status "
                        f"{response.status} ({responses[response.status]})"
            )


    def send(self, msg:str, *, emoji:Optional[str]=None) -> None:
        """Send message to Mattermost with or without existing connection

        :param msg:   passed to :py:meth:`_sendMessage`
        :param emoji: passed to :py:meth:`_sendMessage`
        :raise MattermostError: on any error

        Makes sure that :py:obj:`self` is connected and calls :py:meth:`_sendMessage`.
        """

        try:
            with self._lock:
                with self:
                    self._sendMessage(msg, emoji)
        except MattermostError:
            raise
        except Exception as ex:
            raise MattermostError(f"Sending a message raised an exception of type {type(ex)}: {ex}") from ex

