"""
Copyright (C) DLR-TS 2024

Unit tests for MattermostSender
"""



import os
import unittest
import json

from mattermost_messenger import MattermostSender, MattermostError


webhookUrl = 'https://example.com/hooks/broken'
msg404 = "Mattermost replied with HTTP status 404 (Not Found)"



class TestMattermostSender(unittest.TestCase):
    """Tests for class MattermostSender"""

    def setUp(self):
        """Create a MattermostSender object for testing"""
        self.sender = MattermostSender(webhookUrl, timeout=12, channel='channel')

    def testInit(self):
        """Test __init__ results"""
        self.assertEqual(self.sender._host, 'example.com')
        self.assertTrue(self.sender._isHttps)
        self.assertEqual(self.sender._timeout, 12)
        self.assertEqual(self.sender.channel, 'channel')
        self.assertFalse(self.sender.isConnected())

        httpSender = MattermostSender('http://example.com/hooks/broken')
        self.assertFalse(httpSender._isHttps)

    def testProxy(self):
        self.assertIsNone(self.sender._proxy)
        senderWithProxy = MattermostSender(webhookUrl, proxy='https://proxy.example.com')
        self.assertEqual(senderWithProxy._proxy, 'https://proxy.example.com')

        os.environ['HTTPS_PROXY'] = 'https://proxy2.example.com'
        senderWithEnvProxy = MattermostSender(webhookUrl)
        self.assertEqual(senderWithEnvProxy._proxy, 'https://proxy2.example.com')

        os.environ['NO_PROXY'] = '*ple.com'
        senderWithNoProxy = MattermostSender(webhookUrl)
        self.assertIsNone(senderWithNoProxy._proxy)

        os.environ['NO_PROXY'] = '*.com'
        senderWithNoProxy2 = MattermostSender(webhookUrl)
        self.assertIsNone(senderWithNoProxy2._proxy)

        os.environ['NO_PROXY'] = '*com'
        senderWithNoProxy3 = MattermostSender(webhookUrl)
        self.assertEqual(senderWithNoProxy3._proxy, 'https://proxy2.example.com')

    def testHttpBody(self):
        """Test _makeHttpBody method"""
        body = self.sender._makeHttpBody("my message", ':emoji:')
        content = json.loads(body)
        expected = {
            'text': "my message",
            'icon_emoji': ':emoji:',
            'channel': 'channel',
        }
        self.assertDictEqual(content, expected)

        body = self.sender._makeHttpBody("my message", None)
        content = json.loads(body)
        expected = {
            'text': "my message",
            'channel': 'channel',
        }
        self.assertDictEqual(content, expected)

        senderWithoutChannel = MattermostSender(webhookUrl)
        body = senderWithoutChannel._makeHttpBody("my message", ':emoji:')
        content = json.loads(body)
        expected = {
            'text': "my message",
            'icon_emoji': ':emoji:',
        }
        self.assertDictEqual(content, expected)

        body = senderWithoutChannel._makeHttpBody("my message", None)
        content = json.loads(body)
        expected = {
            'text': "my message",
        }
        self.assertDictEqual(content, expected)

    def testConnect(self):
        """Test connect and disconnect methods"""
        self.sender.disconnect()

        self.sender.connect()
        self.assertTrue(self.sender.isConnected())

        self.sender.disconnect()
        self.assertFalse(self.sender.isConnected())

        with self.sender:
            self.assertTrue(self.sender.isConnected())
        self.assertFalse(self.sender.isConnected())

    def testSendMessage(self):
        """Test _sendMessage method"""
        with self.assertRaises(AssertionError):
            self.sender._sendMessage("my message", ':emoji:')

        with self.sender:
            with self.assertRaises((MattermostError, OSError), msg=msg404):
                self.sender._sendMessage("my message", ':emoji:')

    def testSend(self):
        """Test send method"""
        with self.assertRaises((MattermostError, OSError), msg=msg404):
            self.sender.send("my message", emoji=':emoji:')

        with self.sender:
            with self.assertRaises((MattermostError, OSError), msg=msg404):
                self.sender.send("my message", emoji=':emoji:')


