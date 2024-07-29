from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Sum, F
from django.http.response import HttpResponse

from rest_framework import filters, viewsets, status
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import ClientUser, Referral, Transaction
from .serializers import ClientUserSerializer, ReferralSerializer, TransactionSerializer, ClientWalletDetialSerailizer, ClaimSerializer, NodePassAuthorizedSerializer
from .utils import generate_referral_code, get_chain_node_type, distribute_to_partners, handle_commission_transfer
from StashAdmin.models import BaseUser, AdminUser, NodePartner, NodeSetup, MasterNode
from StashAdmin.serializers import NodeSetupSerializer
import requests
from StashBackend.settings import api_key



class ClientUserViewSet(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = ClientUserSerializer
    lookup_field = 'wallet_address'

    def create(self, request):
        # ref_code = request.data.get('ref')
        # print("reff", ref_code)
        # if not ref_code:
        #     return Response({"error": "Referral code is required"}, status=status.HTTP_400_BAD_REQUEST)
        # try:
        #     user_with_referral_code = ClientUser.objects.get(
        #         referral_code=ref_code)
        #     try:
        #         referral = Referral.objects.create(
        #             user=user_with_referral_code)
        #     except Referral.DoesNotExist:
        #         return Response({"error": "Error to create ref."}, status=status.HTTP_400_BAD_REQUEST)
        # except ClientUser.DoesNotExist:
        #     return Response({"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST)
        new_user_referral_code = generate_referral_code()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(referral_code=new_user_referral_code)
        # user.referred_by = referral
        # user.save()
        # referral.increase_referred_users()
        serializer_data = serializer.data
        # try:

        # serializer_data['referral_address'] = user.referred_by.user.wallet_address
        # serializer_data['referred_user_code'] = user.referred_by.user.referral_code
        return Response(serializer_data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = ClientUser.objects.select_related('referred_by').prefetch_related('transactions').get(wallet_address=wallet_address_from_cookie)

        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        try:
            referrals = Referral.objects.filter(user=instance)
            total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0
            total_commission_earned = referrals.aggregate(total_commission=models.Sum('commission_earned'))['total_commission'] or 0


        except: 
            referrals = 0
        serializer_data = serializer.data
        nodes = Transaction.objects.filter(sender = instance, transaction_type = 'ETH 2.0 Node').count()
        generated_subnodes = Transaction.objects.filter(sender = instance, transaction_type = 'Generated SubNode' ).count()
        serializer_data['referral'] = total_referred_users
        serializer_data['total_nodes'] = nodes
        serializer_data['total_generated_subnodes'] = generated_subnodes
        serializer_data['generated_subnode_reward'] = total_commission_earned

        return Response(serializer_data, status=status.HTTP_200_OK)        


class UserLoginViewset(viewsets.ViewSet):
    def create(self, request):
        wallet_address = request.query_params.get('address')

        try:
            user = BaseUser.objects.get(wallet_address=wallet_address)
            response = Response({'message': 'Login successful'})
            max_age_30_days = timedelta(days=30)
            response.set_cookie(
                'wallet_address', wallet_address, max_age=max_age_30_days)
            return response
        except ClientUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class GetRefAdressViewset(viewsets.GenericViewSet, ListModelMixin):

    def list(self, request, *args, **kwargs):
        ref_code = request.query_params.get('ref')
        if not ref_code:
            return Response({"error": "Referral code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_with_referral_code = ClientUser.objects.get(referral_code=ref_code)
        except ClientUser.DoesNotExist:
            return Response({"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            admin_node = NodeSetup.objects.first().node_id
        except:
            return Response({"error": "Invalid node setup"}, status=status.HTTP_400_BAD_REQUEST)
        
        referral = user_with_referral_code.referred_by
        super_node_ref = getattr(referral.super_node_ref, 'wallet_address', "")
        master_node_ref = getattr(referral.master_node_ref, 'wallet_address', "")
        sub_node_ref = getattr(referral.sub_node_ref, 'wallet_address', "")
        admin_node_ref = admin_node

        response_data = {
            'super_node_ref': super_node_ref,
            'master_node_ref': master_node_ref,
            'sub_node_ref': sub_node_ref,
            'admin_node_ref': admin_node_ref,

        }

        return Response(response_data, status=status.HTTP_200_OK)



class ClientWalletDetialViewset(viewsets.GenericViewSet, ListModelMixin):

    serializer_class = ClientUserSerializer

    def list(self, request, *args, **kwargs):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = ClientUser.objects.select_related('referred_by').prefetch_related('transactions').get(wallet_address=wallet_address_from_cookie)

        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)

        try:
            referrals = Referral.objects.filter(user=instance)
            total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0

        except: 
            referrals = 0
        instance.save()
        serializer = self.get_serializer(instance)
        serializer_data = serializer.data
        serializer_data['referral'] = total_referred_users
        return Response(serializer_data, status=status.HTTP_200_OK)


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer

    def list(self, request, pk=None):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = ClientUser.objects.get(
                wallet_address=wallet_address_from_cookie)
        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)

        try:
            referrals = Referral.objects.filter(user=instance)
        except Referral.DoesNotExist:
            return Response({"error": "Referral not found for this user"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(referrals, many = True)
        total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0
        total_commission_earned = referrals.aggregate(total_commission=models.Sum('commission_earned'))['total_commission'] or 0
        
        return Response({"no_of_referred_users": total_referred_users,
            "commission_earned": total_commission_earned})


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = ClaimSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['sender__wallet_address', 'sender__referred_by__user__wallet_address', 'transaction_type']

    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data['sender']
        user_referral = sender.referred_by
        node = serializer.validated_data['node']
        total_amount = serializer.validated_data['amount']
        transaction_type = serializer.validated_data['transaction_type']
        # node_quantity = serializer.validated_data.get('node_quantity')
        block_id = serializer.validated_data.get('block_id')
        # setup_charges = serializer.validated_data.get('setup_charges', 100)
        # server_type = serializer.validated_data.get('server_type')
        trx_hash = serializer.validated_data.get('trx_hash')
        # stake_swim_quantity = serializer.validated_data.get('stake_swim_quantity', 0)
        # supernode_quantity = serializer.validated_data.get('supernode_quantity', 0)

        # total_amount_node = ((node_quantity * node.cost_per_node))
        # total_amount_stake = stake_swim_quantity * node.booster_node_1_cost if stake_swim_quantity else 0
        # total_amount_super = supernode_quantity * node.booster_node_2_cost if supernode_quantity else 0
        # total_amount = total_amount_node + total_amount_stake + total_amount_super
        

        node_id = serializer.validated_data.get('node_id')
        node = serializer.validated_data.get('node')
        referral_commission = total_amount * node.reward_claim_percentage/100
        print("refff", referral_commission)
        if total_amount < node.minimal_claim:
            return Response({"message": f"Minimal claim is {node.minimal_claim}"})

        try:
            referred_by_user = sender.referred_by
            referred_super_node = referred_by_user.super_node_ref
            referred_master_node = referred_by_user.master_node_ref
            admin_user = node.user

        except AttributeError:
            referred_by_user = None
            referred_super_node = None
            referred_master_node = None

            if not referred_by_user:
                return Response({'message': 'User dont have referral'}, status=status.HTTP_400_BAD_REQUEST)
        
        if referred_super_node:
            if referred_master_node:
                referral_commission_super_node = referral_commission * node.extra_super_node_reward_claim_percentage/100
                referral_commission_master_node = referral_commission * node.extra_master_node_reward_claim_percentage/100
                referral_commission_admin_user = referral_commission - referral_commission_super_node - referral_commission_master_node
            else:
                referral_commission_super_node = referral_commission * node.extra_super_node_reward_claim_percentage/100
                referral_commission_admin_user = referral_commission - referral_commission_super_node
        
        elif referred_master_node:
                referral_commission_master_node = referral_commission * node.extra_master_node_reward_claim_percentage/100
                referral_commission_admin_user = referral_commission  - referral_commission_master_node


        else:
            referral_commission_admin_user = referral_commission 

        if referral_commission_super_node:
            Transaction.objects.create(sender=referred_super_node, amount=referral_commission_super_node, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedSuperSubNode', trx_hash = trx_hash, node_id = node_id, node = node, block_id = block_id)


        if referral_commission_master_node:

            Transaction.objects.create(sender=referred_master_node, amount=referral_commission_master_node, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedMasterSubNode', trx_hash = trx_hash, node_id = node_id, node = node, block_id = block_id)

        if referral_commission_admin_user:

            Transaction.objects.create(sender=admin_user, amount=referral_commission_admin_user, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedAdminSubNode', trx_hash = trx_hash, node_id = node_id, node = node, block_id = block_id)


        Transaction.objects.create(sender=sender, amount=total_amount, transaction_type='Reward Claim', trx_hash = trx_hash, node_id = node_id, node = node, block_id = block_id)

        return Response({'message': 'Transaction created successfully'})
    
    def list(self, request, *args, **kwargs):
        wallet_address = request.query_params.get('walletadd')
        try:
            sender = ClientUser.objects.get(wallet_address = wallet_address)
        except:
            return Response({"Message": "Invalid wallet address...."})
        total_revenue = Transaction.objects.filter(sender = sender,transaction_type = 'Generated SubNode').aggregate(total_generated_trxs = Sum('amount'))['total_generated_trxs'] or 0

        return Response({"total_revenue":total_revenue}, status=status.HTTP_200_OK)

    
class TransactionViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['sender__wallet_address',
                        'sender__referred_by__user__wallet_address', 'transaction_type']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(transaction_type__in=[
                                    'SuperNode Boost', 'Generated SubNode', 'Stake & Swim Boost', 'ETH 2.0 Node'])
        wallet_address = self.request.query_params.get('address')
        all = self.request.query_params.get('all')
        if all:
            queryset = Transaction.objects.all()
        if wallet_address:
            queryset = queryset.filter(
                sender__wallet_address=wallet_address)
        return queryset
    

    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data['sender']
        user_referral = sender.referred_by
        node = serializer.validated_data['node']
        amount = serializer.validated_data.get('node_quantity', 0)
        transaction_type = serializer.validated_data['transaction_type']
        node_quantity = serializer.validated_data.get('node_quantity', 0)
        block_id = serializer.validated_data.get('block_id')
        setup_charges = serializer.validated_data.get('setup_charges', 100)
        server_type = serializer.validated_data.get('server_type')
        trx_hash = serializer.validated_data.get('trx_hash')
        stake_swim_quantity = serializer.validated_data.get('stake_swim_quantity', 0)
        supernode_quantity = serializer.validated_data.get('supernode_quantity', 0)
        master_node_eth2_quantity = serializer.validated_data.get('master_node_eth2', 0)
        super_node_eth2_quantity = serializer.validated_data.get('super_node_eth2', 0)
        if master_node_eth2_quantity :
            if sender.user_type != 'MasterNode':
                return Response({"message": "User is not masternode"})
            
        if super_node_eth2_quantity :
            if sender.user_type != 'SuperNode':
                return Response({"message": "User is not Supernode"})

        total_amount_node = node_quantity * node.cost_per_node if node_quantity else 0
        total_amount_stake = stake_swim_quantity * node.booster_node_1_cost if stake_swim_quantity else 0
        total_amount_super = supernode_quantity * node.booster_node_2_cost if supernode_quantity else 0
        master_node_eth2 = master_node_eth2_quantity * node.master_node_cost if master_node_eth2_quantity else 0
        super_node_eth2 = super_node_eth2_quantity * node.super_node_cost if super_node_eth2_quantity else 0
        total_amount = total_amount_node + total_amount_stake + total_amount_super + master_node_eth2 + super_node_eth2
      
        node_id = serializer.validated_data.get('node_id')
        node = serializer.validated_data.get('node')
        referral_commission_node = total_amount * node.node_commission_percentage/100 
        referral_commission_super = total_amount * node.extra_super_node_commission/100
        referral_commission_master = total_amount * node.extra_master_node_commission/100

        # referral_commission = referral_commission_node + referral_commission_master + referral_commission_super

        referral_commission_super_node = 0
        referral_commission_master_node = 0
        referral_commission_subnode_node = 0

        try:
            referred_by_user = sender.referred_by
            referred_super_node = referred_by_user.super_node_ref
            referred_master_node = referred_by_user.master_node_ref
            referred_sub_node = referred_by_user.sub_node_ref
            print("referralsss", referred_by_user, referred_master_node, referred_sub_node, referred_super_node)
        except AttributeError:
            referred_by_user = None
            referred_super_node = None
            referred_master_node = None
            referred_sub_node = None

            if not referred_by_user:
                return Response({'message': 'User dont have referral'}, status=status.HTTP_400_BAD_REQUEST)
            
        

        # if referred_super_node:
        #     if referred_master_node and referred_sub_node:
        #         referral_commission_super_node = referral_commission * Decimal(0.25)
        #         referral_commission_master_node = referral_commission * Decimal(0.25)
        #         referral_commission_subnode_node = referral_commission * Decimal(0.5)
        #     elif referred_sub_node:
        #         referral_commission_super_node = referral_commission * Decimal(0.25)
        #         referral_commission_subnode_node = referral_commission * Decimal(0.5)
        #     else:
        #         referral_commission_super_node = referral_commission * Decimal(0.25)
        
        # elif referred_master_node:
        #     if referred_sub_node:
                
        #         referral_commission_master_node = referral_commission * Decimal(0.25)
        #         referral_commission_subnode_node = referral_commission * Decimal(0.5)

        #     else:
        #         referral_commission_master_node = referral_commission * Decimal(0.25)

        # elif referred_sub_node:
        #     referral_commission_subnode_node = referral_commission * Decimal(0.5)

        
        # else:
        #     #admin is the referral!!!
        #     referral_commission = 0



        if referred_super_node:
            if referred_master_node and referred_sub_node:
                referral_commission_super_node = referral_commission_super
                referral_commission_master_node = referral_commission_master
                referral_commission_subnode_node = referral_commission_node
            elif referred_sub_node:
                referral_commission_super_node = referral_commission_super
                referral_commission_subnode_node = referral_commission_node
            else:
                referral_commission_super_node = referral_commission_super
        
        elif referred_master_node:
            if referred_sub_node:
                
                referral_commission_master_node = referral_commission_master
                referral_commission_subnode_node = referral_commission_node

            else:
                referral_commission_master_node = referral_commission_master

        elif referred_sub_node:
            referral_commission_subnode_node = referral_commission_node

        
        else:
            #admin is the referral!!!
            referral_commission = 0

        print("refff", referral_commission_master_node, referral_commission_subnode_node, referral_commission_super_node)

        if referral_commission_super_node:
            # Transaction.objects.create(sender=referred_super_node, amount=referral_commission_super_node, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedSuperSubNode', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)
            handle_commission_transfer(referred_super_node, referral_commission_super_node, block_id, node_id, node, server_type, trx_hash, generated_subnode_type = 'GeneratedSuperSubNode')


        if referral_commission_master_node:
            handle_commission_transfer(referred_master_node, referral_commission_master_node, block_id, node_id, node, server_type, trx_hash, generated_subnode_type = 'GeneratedMasterSubNode')


            # Transaction.objects.create(sender=referred_master_node, amount=referral_commission_master_node, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedMasterSubNode', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)

        if referral_commission_subnode_node:
            # print("reffereddd",referred_sub_node.referred_by.commission_received)

            handle_commission_transfer(referred_sub_node, referral_commission_subnode_node, block_id, node_id, node, server_type, trx_hash,generated_subnode_type = 'GeneratedClientSubNode')
            referral = Referral.objects.get(user = referred_sub_node)
            referral.mark_commission_received()
            referral.save()

            # print("reffereddd",referred_sub_node.commission_received)

            # Transaction.objects.create(sender=referred_sub_node, amount=referral_commission_subnode_node, transaction_type='Generated SubNode', generated_subnode_type = 'GeneratedClientSubNode', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)


        if super_node_eth2_quantity:
            Transaction.objects.create(sender=sender, amount=super_node_eth2, transaction_type='Generated SuperNode', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type, super_node_eth2 = super_node_eth2_quantity)
            sender.is_purchased = True
            sender.save()
            
        elif master_node_eth2_quantity:
            Transaction.objects.create(sender=sender, amount=master_node_eth2, transaction_type='Generated MasterNode', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type, master_node_eth2 = master_node_eth2_quantity)
            sender.is_purchased = True
            sender.save()
        else:
            Transaction.objects.create(sender=sender, amount=total_amount_node, node_quantity = node_quantity, transaction_type='ETH 2.0 Node', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)

        if stake_swim_quantity:
            Transaction.objects.create(sender=sender, amount=total_amount_stake, transaction_type='Stake & Swim Boost', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)
        if supernode_quantity:
            Transaction.objects.create(sender=sender, amount=total_amount_super, transaction_type='SuperNode Boost', block_id = block_id, trx_hash = trx_hash, node_id = node_id, node = node, server_type = server_type)

        distribute_to_partners(node, setup_charges)
        print("distributeddd")

        # return Response(serializer.data, status=status.HTTP_201_CREATED)



        # if referred_by_user.user_type == 'Client':
        #     referral_commission = total_amount_node * 10 / 100 

        # elif referred_by_user.user_type == 'MasterNode':
        #     if master_node.master_node_id == referral.master_node_id:
        #         referral_commission = total_amount_node * 5 / 100 

        #     elif master_node.parent_node and master_node.parent_node.master_node_id == referral.master_node_id:
        #         referral_commission = total_amount_node * 5 / 100  

        # elif referred_by_user.user_type == 'Admin':
        #     referral_commission = total_amount_node * 10 / 100 

        # if transaction_type == 'ETH 2.0 Node':
        #     f sender.referred_by and sender.referred_by.commission_received == False:i
                
        #         referral = sender.referred_by
        #         referred_by_user = sender.referred_by.user
        #         referred_by_maturity = referred_by_user.maturity
        #         user_ref_commision = referral.commission_earned

        #         if referred_by_maturity - referred_by_user.claimed_reward >= referral_commission:
        #             referral_commission = Decimal(referral_commission)
        #             referred_by_user.claimed_reward += referral_commission
        #             referred_by_user.save()
        #             referral.increase_commission_earned(referral_commission)
        #             commission_transaction = Transaction.objects.create(
        #                 # sender=sender,
        #                 sender=referral.user,
        #                 amount=referral_commission,
        #                 transaction_type='Generated SubNode',
        #                 block_id = block_id,
        #                 node_id = node_id,
        #                 node = node,
        #                 server_type = server_type,
        #                 trx_hash = trx_hash,
        #                 stake_swim_quantity = 0, supernode_quantity = 0, node_quantity=0

        #             )
                    
        #             referral.commission_transactions = commission_transaction
        #             referral.user.claimed_reward += referral_commission
        #             referral.save()
        #             serializer.save(amount = total_amount_node)
        #             sender.maturity += total_amount*2
        #             if referred_by_user.user_type == 'Client':
        #                 sender.referred_by.mark_commission_received()
        #             sender.total_deposit += total_amount
        #             sender.save()

        #         elif referred_by_maturity - referred_by_user.claimed_reward < referral_commission and referred_by_maturity- referred_by_user.claimed_reward != 0:
        #             commision_added = referred_by_maturity - referred_by_user.claimed_reward
        #             commision_added = Decimal(commision_added)
        #             referred_by_user.claimed_reward += commision_added
        #             referred_by_user.save()
        #             referral.increase_commission_earned(commision_added)
        #             commission_transaction = Transaction.objects.create(
        #                 sender=referral.user,
        #                 # sender=sender,
        #                 amount=commision_added,
        #                 transaction_type='Generated SubNode',
        #                 block_id = block_id,
        #                 node_id = node_id,
        #                 node = node,
        #                 server_type = server_type,
        #                 trx_hash = trx_hash,
        #                 stake_swim_quantity = 0, supernode_quantity = 0, node_quantity=0

        #             )
        #             referral.commission_transactions = commission_transaction
        #             referral.save()
        #             serializer.save(amount = total_amount_node)
        #             sender.maturity += total_amount*2
        #             sender.total_deposit += total_amount
        #             if referred_by_user.user_type == 'Client':
        #                 sender.referred_by.mark_commission_received()
        #             sender.save()
                
        #         else:
        #             sender.maturity += total_amount*2
        #             sender.total_deposit += total_amount
        #             sender.save()
        #             serializer.save(amount = total_amount_node,     stake_swim_quantity = 0, supernode_quantity = 0 )

        #     else:
        #         sender.maturity += total_amount*2
        #         sender.total_deposit += total_amount
        #         sender.save()
        #         serializer.save(amount = total_amount_node, stake_swim_quantity = 0, supernode_quantity = 0)
            # if supernode_quantity:
            #     Transaction.objects.create(sender=sender, amount=total_amount_super, transaction_type='SuperNode Boost', block_id = block_id, node_id = node_id,node = node, supernode_quantity = supernode_quantity, server_type = server_type,
            #             trx_hash = trx_hash, node_quantity = 0)
            # if stake_swim_quantity:
            #     Transaction.objects.create(sender=sender, amount=total_amount_stake, transaction_type='Stake & Swim Boost', node_id = node_id,block_id = block_id, node = node, stake_swim_quantity = stake_swim_quantity,server_type = server_type,
            #             trx_hash = trx_hash, node_quantity = 0)
        sender.is_purchased = True
        sender.save()
        return Response({'message':'Transaction successfully created'}, status=status.HTTP_201_CREATED)


class ServerInformationViewset(viewsets.GenericViewSet, ListModelMixin):

    def list(self, request, *args, **kwargs):
        try:
            node = NodeSetup.objects.all()[-1]
            node_id = node.node_id
            transactions = Transaction.objects.all()
            
            generated_subnodes = transactions.filter(transaction_type='Generated SubNode').count() or 0
            return Response({"node_id":node_id, "generated_subnodes": generated_subnodes}, status= status.HTTP_200_OK)
        except:
            return Response({"detail": "No node found"}, status=status.HTTP_404_NOT_FOUND)


class AuthorizedNodeViewset(viewsets.ModelViewSet):
    # queryset = ClientUser.objects.all()  
    serializer_class = NodePassAuthorizedSerializer

    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        ref_code = serializer.validated_data.get('referral_code')
        user_wallet_address = serializer.validated_data.get('user_wallet_address')
        print("reff", ref_code)
        if not ref_code:
            return Response({"error": "Licensed node pass is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_with_referral_code = ClientUser.objects.get(
                referral_code=ref_code)
            print("user", user_with_referral_code)
            try:
                referral = Referral.objects.create(
                    user=user_with_referral_code)
            except Referral.DoesNotExist:
                return Response({"error": "Error to create ref."}, status=status.HTTP_400_BAD_REQUEST)
        except ClientUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = ClientUser.objects.get(wallet_address = user_wallet_address)
        except ClientUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        user.referred_by = referral
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
                    
        user.save()
        referral.increase_referred_users()

        return Response("Liscenced Node is authorized", status=status.HTTP_200_OK)
        
        
class ExhaustedNodeViewset(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = ClientUserSerializer

    def list(self, request, *args, **kwargs):
        try:
            exhausted_users = ClientUser.objects.filter(maturity=F('claimed_reward'))
            print("exhausted user", exhausted_users)
            transactions_list = Transaction.objects.filter(sender__in=exhausted_users, transaction_type='ETH 2.0 Node')
            eth_node_sum = transactions_list.aggregate(node_quantity = Sum('node_quantity'))['node_quantity'] or 0
            stake_boost_sum = Transaction.objects.filter(sender__in=exhausted_users, transaction_type='Stake & Swim Boost').aggregate(stake_swim_quantity = Sum('stake_swim_quantity'))['stake_swim_quantity'] or 0
            super_boost_sum = Transaction.objects.filter(sender__in=exhausted_users, transaction_type='SuperNode Boost').aggregate(supernode_quantity = Sum('supernode_quantity'))['supernode_quantity'] or 0
            revenue_generated = Transaction.objects.filter(sender__in = exhausted_users, transaction_type = 'ETH 2.0 Node').aggregate(amount = Sum('amount'))['amount'] or 0
            timestamp = transactions_list.first().timestamp
            print(eth_node_sum)
            return Response({'eth_node_sum': eth_node_sum, 'stake_boost_sum': stake_boost_sum,'super_boost_sum': super_boost_sum, 'revenue_generated': revenue_generated, 'timestamp': timestamp})
        except:
            return Response({"detail": "No exhausted nodes found"}, status=status.HTTP_404_NOT_FOUND)


class GeneratedSubNodesViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.filter(transaction_type = 'Generated SubNode')
    serializer_class = TransactionSerializer

    def list(self, request, *args, **kwargs):
        generated_trxs = Transaction.objects.filter(transaction_type = 'Generated SubNode')
        total_subnodes = Transaction.objects.filter(transaction_type = 'Generated SubNode').count()
        total_revenue = Transaction.objects.filter(transaction_type = 'Generated SubNode').aggregate(total_generated_trxs = Sum('amount'))['total_generated_trxs'] or 0
        serializer = self.get_serializer(generated_trxs, many = True)
        return Response({'generated_trxs': serializer.data, 'total_subnodes': total_subnodes, 'total_revenue': total_revenue})
        
class EthereumDataVewiset(viewsets.GenericViewSet, ListModelMixin):
    def list(self, request, *args, **kwargs):
        api = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH'
        headers = {
            "X-CMC_PRO_API_KEY": api_key,
            }
        try:
            response = requests.get(url = api, headers = headers)
        except Exception as e:
            return Response({"detail": str(e) + "Unable to fetch Ethereum data"}, status=status.HTTP_400_BAD_REQUEST)
        return HttpResponse(response._content, status=status.HTTP_200_OK)
        
