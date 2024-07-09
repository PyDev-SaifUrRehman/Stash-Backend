from rest_framework.routers import DefaultRouter
from .views import NodeSetupViewset, AdminUserViewset, AdminReferralViewSet, NodePartnerViewset, NodeMasterViewset, NodeManagerViewset, AdminNodeOverview
router = DefaultRouter()

router.register(r'user-signup', AdminUserViewset, basename='admin-signup')
router.register(r'user-ref', AdminReferralViewSet, basename='refer')
router.register(r'node-setup', NodeSetupViewset, basename='node-setup')
router.register(r'node-partner', NodePartnerViewset, basename='node-partner')
router.register(r'node-master', NodeMasterViewset, basename='node-master')
router.register(r'node-manager', NodeManagerViewset, basename='node-manager')
router.register(r'node-overview', AdminNodeOverview, basename='node-overview')


urlpatterns = router.urls
