from rest_framework.routers import DefaultRouter
from .views import ClientUserViewSet, ReferralViewSet, ClaimViewSet, ClientWalletDetialViewset, UserLoginViewset, GetRefAdressViewset, ServerInformationViewset, TransactionViewset

router = DefaultRouter()

router.register(r'user-signup', ClientUserViewSet, basename='user')
router.register(r'client-wallet', ClientWalletDetialViewset,
                basename='client-wallet')
router.register(r'get-ref-address', GetRefAdressViewset,
                basename='get-ref-address')
router.register(r'login', UserLoginViewset, basename='login')
router.register(r'user-ref', ReferralViewSet, basename='referral')
router.register(r'claim', ClaimViewSet, basename='client-trx')

router.register(r'server-info', ServerInformationViewset, basename='server-info')
router.register(r'transactions', TransactionViewset, basename='comm')

urlpatterns = router.urls
