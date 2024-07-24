from django.contrib import admin
from .models import AdminReferral, AdminUser, MasterNode, NodeManager, NodePartner, NodeSetup, NodeSuperNode

admin.site.register(AdminUser)
admin.site.register(AdminReferral)
admin.site.register(NodeSetup)
admin.site.register(NodePartner)
admin.site.register(NodeManager)
admin.site.register(MasterNode)
admin.site.register(NodeSuperNode)

