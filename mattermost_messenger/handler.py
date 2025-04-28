"""
Copyright (C) DLR-TS 2024

Special :py:class:`logging.Handler` sending log messages to Mattermost with :py:class:`MattermostSenderThreaded`
"""


import sys
import logging
from typing import Optional, Any
from .threaded import MattermostSenderThreaded
from .sender import MattermostError



defaultEmojis = {
    logging.NOTSET: ':grey_exclamation:',
    logging.ERROR: ':exclamation:',
    logging.CRITICAL: ':bangbang:'
}
"""Default for :py:class:`MattermostHandler` emoji param"""



class MattermostHandlerError(MattermostError):
    """Exception raised when an internal error occurs"""



class MattermostHandler(logging.Handler):
    """:py:class:`logging.Handler` sending its messages to a Mattermost webhook

    An error logger that contains :py:obj:`self` directly or indirectly as
    handler will raise a :py:exc:`MattermostHandlerError` exception when used,
    see :py:meth:`_error`. The errorlogger can be changed at any time by assigning to
    :py:attr:`errorLogger` property. To remove the error logger set it
    to :py:const:`None`.
    """

    def __init__(self, url:str, *,
                 name:str='MattermostHandler',
                 level:int=logging.NOTSET,
                 queueSize:Optional[int]=None,
                 timeout:Optional[float]=None,
                 errorLogger:Optional[logging.Logger]=None,
                 emojis:dict[int, str]=defaultEmojis,
                 channel:Optional[str]=None,
                 proxy:Optional[str]=None,
                 ):
        """
        :param url:         URL of the Mattermost webhook
        :param name:        Name to distinguish multiple :py:class:`MattermostHandler` instances
        :param level:       Minimum log level, if set to :py:const:`logging.NOTSET`
                            (default) it inherits the log level of the Logger this
                            handler is added to
        :param timeout:     Passed to :py:class:`MattermostSenderThreaded`
        :param errorLogger: Logger to be notified about internal errors, see :py:meth:`_error`
        :param queueSize:   Passed to :py:class:`MattermostSenderThreaded`
        :param emojis:      :py:class:`dict` assigning log levels to Mattermost emojis, see :py:meth:`_getEmoji`
        :param channel:     Passed to :py:class:`MattermostSenderThreaded`
        :param proxy:       Passed to :py:class:`MattermostSenderThreaded`
        """
        super().__init__(level)
        self.name = name
        self.errorLogger = errorLogger
        self._emojis = emojis
        self._sender = MattermostSenderThreaded(
            url=url,
            errorCallback=self._threadErrorCallback,
            timeout=timeout,
            channel=channel,
            proxy=proxy,
            queueSize=queueSize,
            name=name,
        )


    def _isSelfInLogger(self, logger:Optional[logging.Logger]) -> bool:
        """Recursive check if :py:obj:`self` is a handler for :py:obj:`logger` or its parents

        :param logger: A :py:class:`logging.Logger` instance or :py:const:`None`
        :return:       :py:const:`True` if :py:obj:`self` is handler for :py:obj:`logger`
        """
        if not logger:
            return False
        if self in logger.handlers:
            return True
        if logger.propagate and logger.parent:
            return self._isSelfInLogger(logger.parent)
        return False


    @property
    def errorLogger(self) -> Optional[logging.Logger]:
        """:py:class:`logging.Logger` to be notified about internal errors, see :py:meth:`_error`

        :raise MattermostHandlerError: if set, :py:meth:`_isSelfInLogger` returns
                                       :py:const:`True` for a new logger
        """
        return self._errorLogger

    @errorLogger.setter
    def errorLogger(self, newErrorLogger:Optional[logging.Logger]):
        """Setter for :py:attr:`errorLogger` property"""
        if self._isSelfInLogger(newErrorLogger):
            # Assertion for mypy check
            assert isinstance(newErrorLogger, logging.Logger)
            raise MattermostHandlerError(f"Attempted to set logger '{newErrorLogger.name}' "
                                         "as error logger for MattermostHandler "
                                         f"'{self.name}', but that logger contains "
                                         "self as handler creating a cycle.")
        self._errorLogger = newErrorLogger

    @errorLogger.deleter
    def errorLogger(self):
        """Deleter for :py:attr:`errorLogger` property"""
        self._errorLogger = None


    def close(self) -> None:
        """Shut down internal :py:class:`MattermostSenderThreaded` object

        This will also be called by :py:meth:`logging.shutdown`.
        """
        self._sender.shutdown()
        super().close()


    def _threadErrorCallback(self, data:object, msg:str) -> None:
        """Passed to internal :py:class:`MattermostSenderThreaded` object as error callback

        :param data: optional record that caused the error
        :param msg:  error message from :py:class:`MattermostSenderThreaded`
                     passed to :py:meth:`_error`

        :py:meth:`emit` passes the record as data to :py:meth:`MattermostSenderThreaded.send`
        so we assume that data is either the :py:class:`logging.LogRecord` of the message causing
        the error or :py:const:`None`.

        Calls :py:meth:`_error` with the record in :py:obj:`data`.
        """
        assert isinstance(data, logging.LogRecord) or data is None
        self._error(record=data, msg=msg)


    def _error(self, record:Optional[logging.LogRecord], msg:str) -> None:
        """Handle error when sending a message failed

        :param record: :py:class:`logging.LogRecord` of the failed message
        :param msg:    string with further details to be included in final error message
        :raise MattermostHandlerError: If :py:attr:`errorLogger` would send
                                       the messages back to :py:obj:`self`. In
                                       that case :py:attr:`self.errorLogger` will
                                       be removed.

        Sends a message including :py:obj:`msg` as error to :py:attr:`errorLogger` if
        it exists else to :py:const:`stderr`.
        """

        errorMsg = f"Error sending a message to Mattermost in Handler '{self.name}': \"{msg}\""
        if record:
            errorMsg += f", original message: \"{self.format(record)}\""

        if not self._errorLogger:
            print(errorMsg, file=sys.stderr)
            return

        if self._isSelfInLogger(self._errorLogger):
            del self.errorLogger
            raise MattermostHandlerError(f"Handler '{self.name}' called itself "
                                         "to handle an internal error. Removing "
                                         f"error logger. Error message: {errorMsg}")

        self._errorLogger.error(errorMsg)


    def _getEmoji(self, levelno:int) -> Optional[str]:
        """Retrieve from :py:attr:`emoji` the element with the highest level <= :py:obj:`levelno`

        :param levelno: levelno of the :py:class:`logging.LogRecord` to get an emoji for
        :return:        Mattermost emoji name

        Emojis are retrieved from the emojis dict passed to :py:class:`MattermostHandler`. The dict
        must have log levels as keys, for example :py:attr:`logging.ERROR` or a numerical
        level. Values are the names of Mattermost emojis, for example *:smile:*
        (with the colons).

        Find out possible names by hovering over an emoji in the Mattermost
        emoji table. See :py:data:`defaultEmojis` for an example.
        """

        result = None
        lastFoundLevel = 0
        for level, emoji in self._emojis.items():
            if levelno >= level >= lastFoundLevel:
                result = emoji
                lastFoundLevel = level
        return result


    def emit(self, record:logging.LogRecord) -> None:
        """Overridden :py:meth:`Handler.emit` calling :py:meth:`MattermostSenderThreaded.send`

        :param record: :py:class:`logging.LogRecord` to log

        Passes the formatted record message as :py:obj:`msg`, the result of
        :py:meth:`_getEmoji` for :py:attr:`record.levelno` as emoji, and the
        :py:obj:`record` itself as data.
        """
        self._sender.send(msg=self.format(record), emoji=self._getEmoji(record.levelno), data=record)


