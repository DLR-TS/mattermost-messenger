"""
Copyright (C) DLR-TS 2024

Unit tests for MattermostSenderThreaded
"""



import unittest
from mattermost_messenger import MattermostSenderThreaded


webhookUrl = 'https://example.com/hooks/broken'
msg404 = "Mattermost replied with HTTP status 404 (Not Found)"



class TestMattermostSenderThreaded(unittest.TestCase):
    """Tests for MattermostSenderThreaded class

    ValueError is raised when self.sender._sendQueue.task_done() is called
    more often than items were received from the queue.
    """

    def setUp(self):
        """Create a MattermostSenderThreaded object for testing

        Sets self.errorCallback as error callback.
        """
        self.resetError()
        self.sender = MattermostSenderThreaded(webhookUrl, errorCallback=self.errorCallback)

    def tearDown(self):
        """Shut down MattermostSenderThreaded object"""
        self.sender.shutdown()

    def waitSent(self):
        """Helper to wait until the send queue is empty

        ATTENTION: This will block if not all messages are properly processed
        """
        self.sender._sendQueue.join()

    def resetError(self):
        """Helper to reset results of the last _error call"""
        self.lastErrorData = None
        self.lastErrorMsg = None

    def errorCallback(self, data, msg):
        """Error callback storing data and msg as self attributes"""
        self.lastErrorData = data
        self.lastErrorMsg = msg

    def testInit(self):
        """Test __init__ results"""
        self.assertEqual(self.sender._sendQueue.maxsize, 0)
        self.assertEqual(self.sender._errorCallback, self.errorCallback)
        self.assertIsNone(self.sender._sender.channel)
        self.assertTrue(self.sender._thread.is_alive())
        self.assertTrue(self.sender._sendQueue.empty())

    def testSendItem(self):
        """Test _SendItem method"""
        item = MattermostSenderThreaded._SendItem(msg="my message", emoji=':emoji:', data=123)
        self.assertEqual(item.msg, "my message")
        self.assertEqual(item.emoji, ':emoji:')
        self.assertEqual(item.data, 123)

    def testShutdown(self):
        """Test shutdown method"""
        self.assertTrue(self.sender._thread.is_alive())
        self.sender.shutdown()
        self.assertFalse(self.sender._thread.is_alive())
        self.assertTrue(self.sender._sendQueue.empty())
        self.sender.shutdown()
        self.assertFalse(self.sender._thread.is_alive())
        self.assertTrue(self.sender._sendQueue.empty())

    def testError(self):
        """Test _error method"""
        item = MattermostSenderThreaded._SendItem(msg="my message", emoji=':emoji:', data=123)
        self.resetError()
        self.sender._error(item, "my error")
        self.assertEqual(self.lastErrorMsg, "my error")
        self.assertEqual(self.lastErrorData, 123)

    def testSendAvailabelItems(self):
        """Test _sendAvailabelItems method"""
        self.sender.shutdown()
        testItem = MattermostSenderThreaded._SendItem(msg="my message", emoji=':emoji:', data=123)

        self.resetError()
        with self.assertRaises(ValueError):
            self.sender._sendAvailabelItems(testItem)
        self.assertTrue(self.sender._sendQueue.empty())
        self.assertRegex(self.lastErrorMsg, "Error.+sending message \"my message\" with emoji ':emoji:'")
        self.assertEqual(self.lastErrorData, 123)

        self.sender._sendQueue.put(testItem)
        item = self.sender._sendQueue.get()
        self.sender._sendAvailabelItems(item)
        self.assertTrue(self.sender._sendQueue.empty())
        with self.assertRaises(ValueError):
            self.sender._sendQueue.task_done()

        testItem2 = MattermostSenderThreaded._SendItem(msg="my message 2", emoji=':emoji:', data=456)
        self.sender._sendQueue.put(testItem)
        self.sender._sendQueue.put(testItem2)
        item = self.sender._sendQueue.get()
        self.sender._sendAvailabelItems(item)
        self.assertTrue(self.sender._sendQueue.empty())
        with self.assertRaises(ValueError):
            self.sender._sendQueue.task_done()

        # For None item no task_done() should be called
        self.sender._sendQueue.put(None)
        item = self.sender._sendQueue.get()
        self.sender._sendAvailabelItems(item)
        # task_done() for original None item
        self.sender._sendQueue.task_done()
        # task_done() for None item put back in queue
        self.sender._sendQueue.task_done()
        with self.assertRaises(ValueError):
            self.sender._sendQueue.task_done()

    def testRun(self):
        """Test _run method"""
        self.sender.shutdown()
        testItem = MattermostSenderThreaded._SendItem(msg="my message", emoji=':emoji:', data=123)
        self.sender._sendQueue.put(testItem)
        self.sender._sendQueue.put(None)

        self.sender._run()

        self.assertTrue(self.sender._sendQueue.empty())
        # we cannot call task_done any more
        with self.assertRaises(ValueError):
            self.sender._sendQueue.task_done()

    def testSend(self):
        """Test send method"""
        self.resetError()
        self.sender.send("my message", emoji=':emoji:', data=123)
        self.waitSent()
        self.assertRegex(self.lastErrorMsg, "Error.+sending message \"my message\" with emoji ':emoji:'")
        self.assertEqual(self.lastErrorData, 123)



class TestMattermostSenderThreadedMoreArgs(unittest.TestCase):
    """Additional tests for MattermostSenderThreaded class with more optional init arguments"""

    def setUp(self):
        """Create a MattermostSenderThreaded object for testing ...

        with specific channel, queueSize, and name.

        Sets self.errorCallback as error callback.
        """
        self.resetError()
        self.sender = MattermostSenderThreaded(webhookUrl, errorCallback=self.errorCallback,
                                               defaultEmoji=':defemoji:', channel='channel',
                                               queueSize=10, name='mythread')

    def tearDown(self):
        """Shut down MattermostSenderThreaded object"""
        self.sender.shutdown()

    def resetError(self):
        """Helper to reset results of the last _error call"""
        self.lastErrorData = None
        self.lastErrorMsg = None

    def errorCallback(self, data, msg):
        """Error callback storing data and msg as self attributes"""
        self.lastErrorData = data
        self.lastErrorMsg = msg

    def testName(self):
        """Test name passed to __init__"""
        self.sender.shutdown()
        self.assertEqual(self.sender.name, 'mythread')
        self.assertEqual(self.sender._thread.name, 'mythread')

    def testChannel(self):
        """Test channel passed to __init__"""
        self.resetError()
        self.sender.send("my message", emoji=':emoji:', data=123)
        self.sender._sendQueue.join()
        self.assertRegex(self.lastErrorMsg, "Error.+sending message \"my message\" with emoji ':emoji:' to channel 'channel'")
        self.assertEqual(self.lastErrorData, 123)

    def testDefaultEmoji(self):
        """Test channel passed to __init__"""
        self.resetError()
        self.sender.send("my message", data=123)
        self.sender._sendQueue.join()
        self.assertRegex(self.lastErrorMsg, "Error.+sending message \"my message\" to channel 'channel'")
        self.assertEqual(self.lastErrorData, 123)

    def testQueueSize(self):
        """Test queueSize passed to __init__"""
        self.assertEqual(self.sender._sendQueue.maxsize, 10)

        for i in range(12):
            self.sender.send("my message", emoji=':emoji:', data=123)
        self.assertEqual(self.lastErrorMsg, "Message queue of 'mythread' full. Consider to increase the queueSize passed to MattermostSenderThreaded.")
        self.assertEqual(self.lastErrorData, 123)


