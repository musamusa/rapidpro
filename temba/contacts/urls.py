from .views import ContactCRUDL, ContactGroupCRUDL, ContactFieldCRUDL

from django.conf.urls import url
from .views import ResumeFreshchatLiveChat

urlpatterns = ContactCRUDL().as_urlpatterns()
urlpatterns += ContactGroupCRUDL().as_urlpatterns()
urlpatterns += ContactFieldCRUDL().as_urlpatterns()

urlpatterns += [
    url(r'^contact/freshchat/resume-live-chat/(?P<uuid>[^/]+)/?$', ResumeFreshchatLiveChat.as_view(), name='contacts.freshchat_resume_live_chat'),
]