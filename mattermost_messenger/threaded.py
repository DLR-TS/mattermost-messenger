"""
Copyright (C) DLR-TS 2024

Class :py:class:`MattermostSenderThreaded` for creating a thread to send
messages to Mattermost
"""


import threading
import dataclasses
import queue
from typing import Optional, Any
from collections.abc import Callable
from .sender import MattermostSender, MattermostError



class MattermostSenderThreaded:
    """Variation of :py:class:`MattermostSender` using an independent thread for sending

    This is not derived from :py:class:`MattermostSender`, because (dis)connect
    is handled internally.

    The class uses a queue of given or unlimited size to pass messages to the
    send thread. The send thread applies :py:class:`MattermostSender` to send
    the message.

    In case of an error a callback function passed as :py:obj:`errorCallback`
    will be called with the data object passed to :py:meth:`send` and an error
    message. This prevents termination of the send thread in case of an error.

    Call :py:meth:`shutdown` when the instance is no more needed to terminate
    the send thread. Calls to :py:meth:`send` after that will be ignored and
    cause a call of the error callback.

    .. attention::

        This class is not thread-safe itself. Make sure that :py:meth:`send` and
        :py:meth:`shutdown` are not called concurrently.

    For testing purposes :py:meth:`Queue.task_done` is called after sending
    an item from the send queue, so test code may apply :py:meth:`Queue.join` on
    the private send queue object to wait until all current items are sent.
    """

    _shutdownTimeoutFactor = 2
    """Factor on :py:meth:`MattermostSender.timeout` to wait until termination signal can be put in send queue on shutdown"""


    @dataclasses.dataclass
    class _SendItem:
        """Dataclass for internal queue item to be sent"""

        msg: str
        """Message"""

        emoji: Optional[str] = None
        """Name of a Mattermost emoji for the message"""

        data: Optional[object] = None
        """Arbitrary object passed to error callback in case of an internal error"""


    def __init__(self, url:str, *, errorCallback:Callable[[object, str], None],
                 timeout:Optional[float]=None, defaultEmoji:Optional[str]=None,
                 channel:Optional[str]=None, proxy:Optional[str]=None,
                 queueSize:Optional[int]=None, name:str='Mattermost sender'):
        """
        :param url:           Passed to :py:class:`MattermostSender`
        :param errorCallback: Function to notify internal errors to the caller.
                              Will be called with the data object passed to
                              :py:meth:`send` and an error message.
        :param timeout:       Timeout passed to :py:class:`MattermostSender`
        :param defaultEmoji:  Passed to :py:class:`MattermostSender`
        :param channel:       Passed to :py:class:`MattermostSender`
        :param proxy:         Passed to :py:class:`MattermostSender`
        :param queueSize:     Max size of the queue for messages to send,
                              :py:const:`None` means unlimited
        :param name:          Name passed as thread name to distinguish different
                              instances of this class, doesn't have to be unique.
                              Also used in error messages.

        :py:meth:`MattermostSender.timeout` multiplied by :py:attr:`_shutdownTimeoutFactor`
        will be used as :py:meth:`shutdown` timeout.
        """
        self._sender = MattermostSender(url, timeout=timeout, defaultEmoji=defaultEmoji,
                                        channel=channel, proxy=proxy)
        self._shutdownTimeout = self._shutdownTimeoutFactor * self._sender.timeout
        if queueSize is None:
            queueSize = 0
        self._sendQueue:queue.Queue = queue.Queue(maxsize=queueSize)
        self._errorCallback = errorCallback
        self.name = name
        self._thread = threading.Thread(target=self._run, name=name)
        self._thread.start()


    def __del__(self):
        """Calls :py:meth:`shutdown` to be sure"""
        self.shutdown()


    def send(self, msg:str, *, emoji:Optional[str]=None, data:Optional[object]=None) -> None:
        """Put a message into the send queue and return immediately

        :param msg:   Message to send
        :param emoji: Optional Mattermost emoji
        :param data:  Optional arbitrary object, which will be passed to the error
                      callback in case of an error. This allows the caller to relate an error
                      callback call to the original send call.

        If :py:meth:`shutdown` was called prior to this call :py:meth:`_error` is called
        instead of sending the message.

        If the send queue is full :py:meth:`_error` will be called instead.
        """
        item = MattermostSenderThreaded._SendItem(msg=msg, emoji=emoji, data=data)

        if not self._thread.is_alive():
            self._error(item, f"MattermostSenderThreaded.send() called on '{self.name}' although it is shut down")
            return

        try:
            self._sendQueue.put(item, block=False)
        except queue.Full:
            self._error(item,
                        f"Message queue of '{self.name}' full. Consider to "
                        "increase the queueSize passed to MattermostSenderThreaded.",
            )


    def shutdown(self) -> None:
        """Signal the send thread to terminate and then wait for that

        Puts a termination signal into the send queue and waits until all
        current messages are processed and the thread terminates.

        If the send queue is full for more than a shutdown timeout (see
        :py:class:`MattermostSenderThreaded`) a log record is discarded to make
        space for the termination signal and :py:meth:`_error` is called.
        See :py:class:`MattermostSenderThreaded` for the shutdown timeout.
        """
        while self._thread.is_alive():
            try:
                self._sendQueue.put(None, timeout=(self._shutdownTimeout))
                break
            except queue.Full:
                self._error(None,
                            "Timeout on sending termination signal "
                            f"to MattermostSender thread '{self.name}'")
                # Make space for next try
                self._sendQueue.get()
        self._thread.join()


    def _error(self, item:Optional[_SendItem], msg:str) -> None:
        """Call error callback with :py:obj:`item`'s data if available

        :param item: Item from the send queue that is related to the error
        :param msg:  error message to be passed to error callback

        If :py:obj:`item` is given its :py:attr:`data` attribute will be passed
        to the error callback, of not :py:const:`None` will be passed.
        """
        data = item.data if item else None
        self._errorCallback(data, msg)


    def _sendAvailabelItems(self, firstItem:Optional[_SendItem]) -> None:
        """Send :py:obj:`firstItem` and all currently in the queue available items

        :param firstItem: first item to send if not :py:const:`None`

        Calls :py:meth:`MattermostSender.send` on :py:obj:`firstItem` and each
        successive item in the queue. In case that this raises a
        :py:exc:`MattermostError` :py:meth:`_error` will be called and the next
        item will be sent.

        If the queue is empty the method returns. If a termination item (item that
        evaluates to :py:const:`False`) is found in the queue (including
        :py:obj:`firstItem`) it is put back and the method returns. That ensures
        that the thread function :py:meth:`_run` will receive it.
        """
        item = firstItem
        while item:
            assert isinstance(item, MattermostSenderThreaded._SendItem)
            try:
                self._sender.send(item.msg, emoji=item.emoji)
            except MattermostError as ex:
                emojiMsg = f" with emoji '{item.emoji}'" if item.emoji else ""
                channelMsg = f" to channel '{self._sender.channel}'" if self._sender.channel else ""
                dataMsg = f" with message data: {item.data}" if item.data else ""
                errMsg = f"Error in '{self.name}' sending message \"{item.msg}\"{emojiMsg}{channelMsg}: \"{ex}\"{dataMsg}"
                self._error(item, errMsg)
            finally:
                self._sendQueue.task_done()

            try:
                item = self._sendQueue.get(block=False)
            except queue.Empty:
                return

        self._sendQueue.put(None)


    def _run(self) -> None:
        """Thread function getting items from the queue and sending them to Mattermost

        If an item is available a connection to Mattermost is established and
        :py:meth:`_sendAvailabelItems` is called to send all items at once before
        disconnecting from Mattermost until the next item is available.

        Calls :py:meth:`_error` if a :py:exc:`MattermostError` is catched due to
        connection problems. After that it tries again with the next item.

        When a termination item (item that evaluates to :py:const:`False`) is
        found in the queue the method returns after calling :py:meth:`Queue.task_done`
        as often as possible. Note, that :py:meth:`_sendAvailabelItems` puts a
        termination item back into the queue so that this method would receive it.
        """

        while item := self._sendQueue.get():
            try:
                with self._sender:
                    self._sendAvailabelItems(item)
            except MattermostError as ex:
                self._error(item, f"Error connecting to Mattermost in '{self.name}': {ex}")

        # Call self._sendQueue.task_done() for final None items
        try:
            while True:
                self._sendQueue.task_done()
        except ValueError:
            # self._sendQueue.task_done() called too often
            pass

