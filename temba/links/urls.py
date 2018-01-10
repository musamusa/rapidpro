from __future__ import unicode_literals

from .views import FlowCRUDL

urlpatterns = FlowCRUDL().as_urlpatterns()
