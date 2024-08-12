from rest_framework.routers import DefaultRouter
from .views import ClientUserViewSet, ReferralViewSet, ClaimViewSet, ClientWalletDetialViewset, UserLoginViewset, GetRefAdressViewset, ServerInformationViewset, TransactionViewset, AuthorizedNodeViewset, ExhaustedNodeViewset, GeneratedSubNodesViewset, EthereumDataVewiset

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
router.register(r'node-auth', AuthorizedNodeViewset, basename='node-auth')
router.register(r'exhausted-node', ExhaustedNodeViewset, basename='exhausted')
router.register(r'sub-node', GeneratedSubNodesViewset, basename='gen-sub-node')
router.register(r'eth-data', EthereumDataVewiset, basename='eth-data')

urlpatterns = router.urls
