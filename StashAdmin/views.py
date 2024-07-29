from django.shortcuts import render
from django.db.models import Value, Sum, F
from rest_framework import viewsets
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import mixins
from rest_framework.response import Response

from .models import MasterNode, NodeManager, NodePartner, NodeSetup, AdminUser, NodePayout, NodeSuperNode
from .serializers import NodeSetupSerializer, AdminUserSerializer, NodePartnerSerializer, MasterNodeSerializer, NodeManagerSerializer, NodePayoutSerializer, AddNodeToAdminSerializer, NodeSuperNodeSerializer
from StashClient.utils import generate_referral_code
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from StashClient.models import ClientUser, Transaction, Referral

class NodeSetupViewset(viewsets.ModelViewSet):
    queryset = NodeSetup.objects.all()
    serializer_class = NodeSetupSerializer

    def list(self, request, *args, **kwargs):
        user = request.query_params.get('address')
        try:
            user = ClientUser.objects.get(wallet_address = user)
        except Exception as e:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        node = NodeSetup.objects.first()
        if not node:
            node_id = user.referral_code  
            node, created = NodeSetup.objects.get_or_create(user = user, node_id = node_id
                                                         )
        serializer = self.get_serializer(node)
        return Response(serializer.data, status=status.HTTP_200_OK)
    @action(methods=['get'], detail=False)
    def getnode(self, request, *args, **kwargs):
        node = NodeSetup.objects.all()
        serializer = self.get_serializer(node, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminUserViewset(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = AdminUserSerializer
    lookup_field = 'wallet_address'
    def create(self, request):
        # ref_code = request.data.get('ref')

        # if not ref_code:
        #     return Response({"error": "Referral code is required"}, status=status.HTTP_400_BAD_REQUEST)
        # try:
        #     user_with_referral_code = AdminUser.objects.get(
        #         referral_code=ref_code)
        #     try:
        #         referral = AdminReferral.objects.create(
        #             user=user_with_referral_code)
        #     except AdminReferral.DoesNotExist:
        #         return Response({"error": "Error to create ref."})
        # except AdminUser.DoesNotExist:
        #     return Response({"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST)
        new_user_referral_code = generate_referral_code()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(referral_code=new_user_referral_code)
        # user.referred_by = referral
        user.save()
        # referral.increase_referred_users()
        serializer_data = serializer.data
        # serializer_data['referral_address'] = user.referred_by.user.wallet_address
        return Response(serializer_data, status=status.HTTP_201_CREATED)


# class AdminReferralViewSet(viewsets.ModelViewSet):
#     queryset = AdminReferral.objects.all()
#     serializer_class = AdminReferralSerializer

#     def list(self, request, pk=None):
#         try:
#             wallet_address_from_cookie = request.query_params.get('address')
#             instance = AdminUser.objects.get(
#                 wallet_address=wallet_address_from_cookie)
#         except (ObjectDoesNotExist, ValueError):
#             return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)

#         try:
#             referrals = AdminReferral.objects.filter(user=instance)
#         except AdminReferral.DoesNotExist:
#             return Response({"error": "Referral not found for this user"}, status=status.HTTP_404_NOT_FOUND)
        
#         serializer = self.get_serializer(referrals, many = True)
#         total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0
#         total_commission_earned = referrals.aggregate(total_commission=models.Sum('commission_earned'))['total_commission'] or 0
        
#         return Response({"no_of_referred_users": total_referred_users,
#             "commission_earned": total_commission_earned})


class NodePartnerViewset(viewsets.ModelViewSet):
    queryset = NodePartner.objects.all()
    serializer_class = NodePartnerSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']


class NodeMasterViewset(viewsets.ModelViewSet):
    queryset = MasterNode.objects.all()
    serializer_class = MasterNodeSerializer
    # lookup_field = 'node__user__referral_code'
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    # filterset_fields = ['node__user__referral_code']
    
    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
        
    #     node = serializer.validated_data['node']
        
        
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)

    # def perform_create(self, serializer):
    #     serializer.save()

class NodeManagerViewset(viewsets.ModelViewSet):
    queryset = NodeManager.objects.all()
    serializer_class = NodeManagerSerializer
    # lookup_field = 'node__user__referral_code'
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']
    

class AdminNodeOverview(viewsets.ModelViewSet):

    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer

    def list(self, request, *args, **kwargs):

        total_eth2_nodes_count = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').count() or 0
        stake_swim_boostcount = Transaction.objects.filter(transaction_type = 'Stake & Swim Boost').count() or 0
        total_super_nodes_count = Transaction.objects.filter(transaction_type = 'SuperNode Boost').count() or 0
        total_setup_fee = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').aggregate(setup_charges = Sum('setup_charges'))['setup_charges'] or 0
        total_super_nodes_count = 0
        # active_nodes_balance = 0  #node amount that are not exausted, mean maturity - withdrawal == 0 users
        active_nodes_balance = ClientUser.objects.exclude(maturity=F('claimed_reward')).aggregate(amount=Sum('total_deposit'))['amount'] or 0
        
        # active_nodes_balance = ClientUser.objects.filter(F('maturity') - F('claimed_reward') == Value(0))
        print("act", active_nodes_balance)
        # current_reward_balance = 0 # double the activenode balance
        current_reward_balance = 2 * active_nodes_balance
        # node_pass_revenue = 0 # amount deposited
        node_pass_revenue = Transaction.objects.all().aggregate(amount = Sum('amount'))['amount'] or 0
        # total_revenue = 0 # sum of these fees...
        total_revenue = total_setup_fee + node_pass_revenue 

        return Response({'total_eth2_nodes_count': total_eth2_nodes_count, 'stake_swim_boostcount': stake_swim_boostcount, 'total_setup_fee' : total_setup_fee, 'total_super_nodes_count' : total_super_nodes_count, 'active_nodes_balance':active_nodes_balance,'current_reward_balance':current_reward_balance, 'node_pass_revenue' :node_pass_revenue, 'total_revenue': total_revenue })


class AdminClaimViewset(viewsets.ModelViewSet):
    serializer_class = NodePayoutSerializer

    def list(self, request, *args, **kwargs):
        active_nodes_balance = ClientUser.objects.exclude(maturity=F('claimed_reward')).aggregate(amount=Sum('total_deposit'))['amount'] or 0
        claim_rewards = Transaction.objects.filter(transaction_type='Reward Claim').aggregate(amount=Sum('amount'))['amount'] or 0
        all_trx_balance= Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').aggregate(amount = Sum('amount'))['amount'] or 0
        current_net_balance = all_trx_balance - active_nodes_balance
        nodes_payout = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node') or 0
        node_payout, created = NodePayout.objects.get_or_create(pk=1)
        node_payout_amount = node_payout.amount
        return Response({'active_nodes_balance': active_nodes_balance, 'claim_rewards': claim_rewards, 'current_net_balance': current_net_balance, "node_payout_amount":node_payout_amount
        })

    @action(methods=['put'], detail=False)    
    def updatepayout(self, request, pk=None):
        node_payout, created = NodePayout.objects.get_or_create(pk=1)
        serializer = NodePayoutSerializer(
            node_payout, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddNodeToAdminViewset(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = AddNodeToAdminSerializer

    def create(self, request):

        serializer = AddNodeToAdminSerializer(
            data=request.data, context={'request': request})
        new_user_referral_code = generate_referral_code()
        serializer.is_valid(raise_exception=True)
        wallet_address = serializer.validated_data.get('wallet_address')
        node_quantity = serializer.validated_data.get('node_quantity')
        stake_swim_quantity = serializer.validated_data.get('stake_swim_quantity')
        supernode_quantity = serializer.validated_data.get('supernode_quantity')
        node_pass = serializer.validated_data.get('node_pass')
        # deposit_amount = serializer.validated_data.get('admin_added_deposit', 0)
        maturity_amount = serializer.validated_data.get('admin_maturity', 0)
        admin_added_claimed_reward = serializer.validated_data.get('admin_added_claimed_reward', 0)

        sender, created = ClientUser.objects.get_or_create(wallet_address = wallet_address, admin_added_claimed_reward = admin_added_claimed_reward, maturity = maturity_amount, referral_code = new_user_referral_code,node_type = 'Node')
        sender = ClientUser.objects.get(wallet_address = wallet_address)
        print("sender", sender)
        try:
            referral_node_pass = ClientUser.objects.get(referral_code = node_pass)
            try:
                referral = Referral.objects.create(
                    user=referral_node_pass)
            except Referral.DoesNotExist:
                return Response({"error": "Error to create ref."}, status=status.HTTP_400_BAD_REQUEST)
            print("referral", referral_node_pass)
            sender.referred_by = referral
            if referral.user.user_type == 'SuperNode':
                referral.super_node_ref = referral.user
                referral.save()
            if referral.user.user_type == 'MasterNode':
                referral.super_node_ref = referral.user.referred_by.user
                referral.master_node_ref = referral.user
                referral.save()
            if referral.user.user_type == 'Client':
                referral.super_node_ref = referral.user.referred_by.super_node_ref
                referral.master_node_ref = referral.user.referred_by.master_node_ref
                referral.sub_node_ref = referral.user
                referral.save()
                        
            sender.save()
        except:
            return Response({"messsage": "Invalid Node Pass."}, status = status.HTTP_400_BAD_REQUEST)
        try:
            node = NodeSetup.objects.first()
            node_id = node.node_id
            eth_node_price = node.cost_per_node
            stake_swim_booster_price = node.booster_node_1_cost
            supernode_booster_price = node.booster_node_2_cost
            print("sender", sender  )

            if node_quantity:
                Transaction.objects.create(sender = sender, amount = node_quantity*eth_node_price, transaction_type = 'ETH 2.0 Node',node = node)
            if supernode_booster_price:
                Transaction.objects.create(sender = sender, amount = supernode_quantity*supernode_booster_price, transaction_type = 'SuperNode Boost',node = node)
            if stake_swim_booster_price:
                Transaction.objects.create(sender=sender, amount=stake_swim_quantity*stake_swim_booster_price, transaction_type='Stake & Swim Boost',node = node)
        except Exception as e:
            return Response({"message": f"something went wrong {e}"}, status=status.HTTP_400_BAD_REQUEST)
        serializer_data = serializer.data
        return Response(serializer_data, status=status.HTTP_201_CREATED)
    

class SuperNodeViewset(viewsets.ModelViewSet):
    queryset = NodeSuperNode.objects.all()
    serializer_class = NodeSuperNodeSerializer
    # lookup_field = 'node__user__referral_code'
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']
    
class GetRevenueSearchViewset(viewsets.GenericViewSet, mixins.ListModelMixin):

    def list(self, request, *args, **kwargs):
        ref = request.query_params.get('ref')
        try:
            user = ClientUser.objects.get(referral_code=ref)
            
            if user.user_type == 'Client':
                return Response({'message': 'Client is not allowed'})
                
            transactions = Transaction.objects.filter(sender=user)
            
            subnode_generated = transactions.filter(generated_subnode_type='GeneratedClientSubNode')
            subnode_generated_count = subnode_generated.count()
            subnode_first_transaction = transactions.filter(generated_subnode_type='GeneratedClientSubNode').order_by('timestamp').first()
            subnode_generated_timestamp = subnode_first_transaction.timestamp if subnode_first_transaction else 0
            subnode_generated_revenue = subnode_generated.aggregate(subnode_generated_revenue = Sum('amount'))['subnode_generated_revenue'] or 0
            

            master_node_generated = transactions.filter(generated_subnode_type='GeneratedMasterSubNode')
            master_node_generated_count = master_node_generated.count()
            master_first_transaction = transactions.filter(generated_subnode_type='GeneratedMasterSubNode').order_by('timestamp').first()
            master_generated_timestamp = master_first_transaction.timestamp if master_first_transaction else 0
            master_node_generated_revenue = master_node_generated.aggregate(master_node_generated_revenue = Sum('amount'))['master_node_generated_revenue'] or 0

            
            super_node_generated = transactions.filter(generated_subnode_type='GeneratedSuperSubNode')
            super_node_generated_count = super_node_generated.count()
            super_first_transaction = super_node_generated.order_by('timestamp').first()
            super_node_generated_timestamp = super_first_transaction.timestamp if super_first_transaction else 0
            super_node_generated_revenue = super_node_generated.aggregate(super_node_generated_revenue = Sum('amount'))['super_node_generated_revenue'] or 0

            total_sub_nodes = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').aggregate(total_sub_nodes = Sum('node_quantity'))['total_sub_nodes'] or 0
            total_master_nodes = Transaction.objects.filter(transaction_type = 'Generated MasterNode').count()
            total_super_nodes = Transaction.objects.filter(transaction_type = 'Generated SuperNode').count()

            generated_revenue = Transaction.objects.filter(transaction_type__in=['Generated SubNode', 'Generated MasterNode', 'Generated SuperNode']).aggregate(revenue = Sum('amount'))['revenue'] or 0
            
            return Response({
                'total_sub_nodes': total_sub_nodes,
                'total_master_nodes': total_master_nodes,
                'total_super_nodes': total_super_nodes,
                'generated_revenue': generated_revenue,
                'subnode_generated_count': subnode_generated_count, 
                'subnode_generated_timestamp': subnode_generated_timestamp, 
                'subnode_generated_revenue': subnode_generated_revenue,
                'master_node_generated_count': master_node_generated_count, 
                'master_generated_timestamp': master_generated_timestamp, 
                'master_node_generated_revenue': master_node_generated_revenue,
                'super_node_generated_count': super_node_generated_count, 
                'super_node_generated_timestamp': super_node_generated_timestamp,
                'super_node_generated_revenue': super_node_generated_revenue
            })
        except ClientUser.DoesNotExist:
            return Response({'message': 'User not found.'})
        except Exception as e:
            return Response({"message": f"Error Occurred! {e}"})
