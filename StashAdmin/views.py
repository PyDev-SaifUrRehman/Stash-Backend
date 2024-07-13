from django.shortcuts import render

from .models import MasterNode, NodeManager, NodePartner, NodeSetup, AdminUser, AdminReferral
from .serializers import NodeSetupSerializer, AdminUserSerializer, AdminReferralSerializer, NodePartnerSerializer, MasterNodeSerializer, NodeManagerSerializer
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from StashClient.utils import generate_referral_code
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend


class NodeSetupViewset(viewsets.ModelViewSet):
    queryset = NodeSetup.objects.all()
    serializer_class = NodeSetupSerializer


class AdminUserViewset(viewsets.ModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer
    def create(self, request):
        ref_code = request.data.get('ref')

        if not ref_code:
            return Response({"error": "Referral code is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_with_referral_code = AdminUser.objects.get(
                referral_code=ref_code)
            try:
                referral = AdminReferral.objects.create(
                    user=user_with_referral_code)
            except AdminReferral.DoesNotExist:
                return Response({"error": "Error to create ref."})
        except AdminUser.DoesNotExist:
            return Response({"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST)
        new_user_referral_code = generate_referral_code()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(referral_code=new_user_referral_code)
        user.referred_by = referral
        user.save()
        referral.increase_referred_users()
        serializer_data = serializer.data
        serializer_data['referral_address'] = user.referred_by.user.wallet_address
        return Response(serializer_data, status=status.HTTP_201_CREATED)


class AdminReferralViewSet(viewsets.ModelViewSet):
    queryset = AdminReferral.objects.all()
    serializer_class = AdminReferralSerializer

    def list(self, request, pk=None):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = AdminUser.objects.get(
                wallet_address=wallet_address_from_cookie)
        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)

        try:
            referrals = AdminReferral.objects.filter(user=instance)
        except AdminReferral.DoesNotExist:
            return Response({"error": "Referral not found for this user"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(referrals, many = True)
        total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0
        total_commission_earned = referrals.aggregate(total_commission=models.Sum('commission_earned'))['total_commission'] or 0
        
        return Response({"no_of_referred_users": total_referred_users,
            "commission_earned": total_commission_earned})


class NodePartnerViewset(viewsets.ModelViewSet):
    queryset = NodePartner.objects.all()
    serializer_class = NodePartnerSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']


class NodeMasterViewset(viewsets.ModelViewSet):
    queryset = MasterNode.objects.all()
    serializer_class = MasterNodeSerializer
    lookup_field = 'node__user__referral_code'
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        node = serializer.validated_data['node']
        master_node = MasterNode.objects.filter(node=node)
        master_node_count = master_node.count()
        
        if master_node_count >= 2:
            return Response({"message": 'A node can only have two master nodes.'}, status=status.HTTP_200_OK)
        
        if master_node_count == 1:
            parent_node = master_node.first()
            serializer.validated_data['parent_node'] = parent_node
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()

class NodeManagerViewset(viewsets.ModelViewSet):
    queryset = NodeManager.objects.all()
    serializer_class = NodeManagerSerializer
    lookup_field = 'node__user__referral_code'
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['node__user__referral_code']
    

from StashClient.models import Transaction, ClientUser
from django.db.models import Value, Sum, F
class AdminNodeOverview(viewsets.ModelViewSet):

    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer

    def list(self, request, *args, **kwargs):

        total_eth2_nodes_count = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').count() or 0
        stake_swim_boostcount = Transaction.objects.filter(transaction_type = 'Stake & Swim Boost').count() or 0
        total_super_nodes_count = Transaction.objects.filter(transaction_type = 'SuperNode Boost').count() or 0
        total_setup_fee = Transaction.objects.filter(transaction_type = 'ETH 2.0 Node').aggregate(setup_charges = models.Sum('setup_charges'))['setup_charges'] or 0
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

