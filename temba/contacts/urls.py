from .views import ContactCRUDL, ContactGroupCRUDL, ContactFieldCRUDL

from django.conf.urls import url
from .views import StopFreshchatAttendance

urlpatterns = ContactCRUDL().as_urlpatterns()
urlpatterns += ContactGroupCRUDL().as_urlpatterns()
urlpatterns += ContactFieldCRUDL().as_urlpatterns()

urlpatterns += [
    url(r'^contact/freshchat/stop-attendance/(?P<uuid>[^/]+)/?$', StopFreshchatAttendance.as_view(), name='contacts.freshchat_stop_attendance'),
]