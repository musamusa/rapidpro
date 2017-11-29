from __future__ import unicode_literals

from temba.msgs.handler import MessageHandler
from .models import Contact


class InvitationHandler(MessageHandler):
    def __init__(self):
        super(InvitationHandler, self).__init__('contacts')

    def handle(self, msg):
        return Contact.find_and_handle(msg)
