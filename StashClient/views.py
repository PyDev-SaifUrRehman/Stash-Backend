from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import ClientUser, Referral, Transaction
from .serializers import ClientUserSerializer, ReferralSerializer, TransactionSerializer, ClientWalletDetialSerailizer
from .utils import generate_referral_code
from StashAdmin.models import BaseUser, AdminUser, AdminReferral, NodePartner, NodeSetup, MasterNode


class ClientUserViewSet(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = ClientUserSerializer

    def create(self, request):
        # ref_code = request.query_params.get('ref')
        ref_code = request.data.get('ref')
        print("reff", ref_code)
        if not ref_code:
            return Response({"error": "Referral code is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_with_referral_code = ClientUser.objects.get(
                referral_code=ref_code)
            try:
                referral = Referral.objects.create(
                    user=user_with_referral_code)
            except Referral.DoesNotExist:
                return Response({"error": "Error to create ref."}, status=status.HTTP_400_BAD_REQUEST)
        except ClientUser.DoesNotExist:
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

    def list(self, request, *args, **kwargs):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = ClientUser.objects.select_related('referred_by').prefetch_related('transactions').get(wallet_address=wallet_address_from_cookie)

        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        instance.update_balance()
        try:
            referrals = Referral.objects.filter(user=instance)
            total_referred_users = referrals.aggregate(total_users=models.Sum('no_of_referred_users'))['total_users'] or 0

        except: 
            referrals = 0
        instance.update_balance()
        serializer_data = serializer.data
        serializer_data['referral'] = total_referred_users
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
            user_with_referral_code = ClientUser.objects.get(
                referral_code=ref_code)
            return Response({"wallet_address": user_with_referral_code.wallet_address}, status=status.HTTP_200_OK)
        except ClientUser.DoesNotExist:
            return Response({"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST)


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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()

    serializer_class = TransactionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['sender__wallet_address',
                        'sender__referred_by__user__wallet_address', 'transaction_type']

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     queryset = queryset.filter(transaction_type__in=[
    #                                'Reward Claim', 'SuperNode Boost', 'Generated SubNode', 'Stake & Swim Boost', 'ETH 2.0 Node'])
    #     wallet_address = self.request.query_params.get('address')
    #     if wallet_address:
    #         queryset = queryset.filter(
    #             sender__wallet_address__in=wallet_address)
    #     return queryset
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node = serializer.validated_data.get('node')
        sender = serializer.validated_data.pop('sender')
        # amount = serializer.validated_data.get('amount')
        node_quantity = serializer.validated_data.get('node_quantity')
        stake_swim_quantity = serializer.validated_data.get('stake_swim_quantity')
        supernode_quantity = serializer.validated_data.get('supernode_quantity')
        transaction_type = serializer.validated_data.pop('transaction_type')
        block_id = serializer.validated_data.get('block_id')
        node_id = serializer.validated_data.get('node_id')
        amount = (node_quantity * node.cost_per_node +
                  stake_swim_quantity * node.booster_node_1_cost +
                  supernode_quantity * node.booster_node_2_cost)
        print("amount", amount)

        sender = ClientUser.objects.get(id=sender.id)
        if transaction_type == 'ETH 2.0 Node':
            
            try:
                referred_user_code = sender.referred_by.user.referral_code 
            except:
                return Response({"Message": "Invalid referral code...."})
                
            refered_user = sender.referred_by.user
            master_node = MasterNode.objects.filter(node = node).order_by('-pk')[0]

            print("node id",node.node_id)
            print("node id",node)
            print("referal code",sender.referral_code)

            if sender.referral_code == node.node_id:
                print("admin reff")
                claim_fee_per = node.reward_claim_percentage
                claim_fee = amount * claim_fee_per/100
                try:
                    node_partners = NodePartner.objects.filter(node = node)
                except:
                    return Response({"Message": "No node partners found...."})
                for partner in node_partners:
                    client , created = ClientUser.objects.get_or_create(wallet_address = partner.partner_wallet_address)
                    partner_sender_object = ClientUser.objects.get(wallet_address = partner.partner_wallet_address)
                    Transaction.objects.create(sender=partner_sender_object, amount=claim_fee*partner.share/100, transaction_type='Reward Claim', **serializer.validated_data)
                Transaction.objects.create(sender=sender, amount=stake_swim_quantity * node.booster_node_1_cost, transaction_type='Stake & Swim Boost', **serializer.validated_data)
                Transaction.objects.create(sender=sender, amount=node_quantity * node.cost_per_node, transaction_type='ETH 2.0 Node', **serializer.validated_data)
                Transaction.objects.create(sender=sender, amount=supernode_quantity * node.booster_node_2_cost, transaction_type='SuperNode Boost', **serializer.validated_data)
                Transaction.objects.create(sender=partner_sender_object, amount=amount, transaction_type='Generated SubNode', **serializer.validated_data)
            ### multiple nodes
            elif sender.referral_code == master_node.parent_node.master_node_id or (sender.referral_code == master_node.master_node_id and master_node.parent_node is None) :
                print('multiple master node but with masternode 1') 
                print("Booolll",sender.referral_code == master_node.parent_node.node_id)
                print("Booooolllll",sender.referral_code == master_node.node_id and master_node.parent_node is not None)
                print("parent nodeeeeee")

                master_node = MasterNode.objects.filter(node = node).order_by('-pk')[0]
                print("master node", master_node.pk)
                master_claim_fee_per = master_node.claim_fee_percentage
                claim_fee = amount * master_claim_fee_per/100
                partner_fees = claim_fee * 0.08
                try:
                    node_partners = NodePartner.objects.filter(node = node)
                except:
                    return Response({"Message": "No node partners found...."})
                for partner in node_partners:
                    client , created = ClientUser.objects.get_or_create(wallet_address = partner.partner_wallet_address)
                    Transaction.objects.create(sender=partner.partner_wallet_address, amount=partner_fees*partner.share/100, transaction_type='Reward Claim')
                Transaction.objects.create(sender=sender, amount=stake_swim_quantity * node.booster_node_1_cost, transaction_type='Stake & Swim Boost')
                Transaction.objects.create(sender=sender, amount=node_quantity * node.cost_per_node, transaction_type='ETH 2.0 Node')
                Transaction.objects.create(sender=sender, amount=supernode_quantity * node.booster_node_2_cost, transaction_type='SuperNode Boost')
                Transaction.objects.create(sender=partner.partner_wallet_address, amount=amount, transaction_type='Generated SubNode')
                master_wallet = AdminUser.objects.create(wallet_address = master_node.wallet_address, user_type = 'MasterNode')
                Transaction.objects.create(sender=master_node.wallet_address, amount=claim_fee*0.02, transaction_type='Reward Claim')

            elif sender.referral_code == master_node.master_node_id and master_node.parent_node is not None :
                print('single master node')
                print("Booolll",sender.referral_code == master_node.parent_node.node_id)
                print("Booooolllll",sender.referral_code == master_node.node_id and master_node.parent_node is not None)

                # print("parent nodeeeeee")
                master_node = MasterNode.objects.filter(node = node).order_by('-pk')[0]
                master_claim_fee_per = master_node.claim_fee_percentage
                claim_fee = amount * master_claim_fee_per/100
                partner_fees = claim_fee * 0.06
                try:
                    node_partners = NodePartner.objects.filter(node = node)
                except:
                    return Response({"Message": "No node partners found...."})
                for partner in node_partners:
                    client , created = ClientUser.objects.get_or_create(wallet_address = partner.partner_wallet_address)
                    Transaction.objects.create(sender=partner.partner_wallet_address, amount=partner_fees*partner.share/100, transaction_type='Reward Claim')
                Transaction.objects.create(sender=sender, amount=stake_swim_quantity * node.booster_node_1_cost, transaction_type='Stake & Swim Boost')
                Transaction.objects.create(sender=sender, amount=node_quantity * node.cost_per_node, transaction_type='ETH 2.0 Node')
                Transaction.objects.create(sender=sender, amount=supernode_quantity * node.booster_node_2_cost, transaction_type='SuperNode Boost')
                Transaction.objects.create(sender=partner.partner_wallet_address, amount=amount, transaction_type='Generated SubNode')
                master_wallet = AdminUser.objects.create(wallet_address = master_node.wallet_address, user_type = 'MasterNode')
                master_wallet2 = AdminUser.objects.create(wallet_address = master_node.wallet_address, user_type = 'MasterNode')
                
                Transaction.objects.create(sender=master_node.wallet_address, amount=claim_fee*0.02, transaction_type='Reward Claim')
                Transaction.objects.create(sender=master_node.wallet_address, amount=claim_fee*0.02, transaction_type='Reward Claim')

            # elif refered_user.user
            return Response({"Admin type is excuted and partners is to credited"})
            



            # elif refered_user.user

            

        return Response({"reward distributed"})

            # if sender.referred_by ==  

    @action(methods=['get'], detail=False)
    def all_trx(self, request, pk=None):
        try:
            wallet_address_from_cookie = request.query_params.get('address')
            instance = ClientUser.objects.get(
                wallet_address=wallet_address_from_cookie)
        except (ObjectDoesNotExist, ValueError):
            return Response({"detail": "User not found or invalid address"}, status=status.HTTP_404_NOT_FOUND)
        transactions = Transaction.objects.filter(sender=instance).exclude(transaction_type = 'Referral')
        serializer = self.get_serializer(transactions, many=True)

        total_deposit = transactions.filter(transaction_type='Deposit').aggregate(
            total_deposit=models.Sum('amount'))['total_deposit'] or 0
        total_withdrawal = transactions.filter(transaction_type='Withdrawal').aggregate(
            total_withdrawal=models.Sum('amount'))['total_withdrawal'] or 0
        referrals = Referral.objects.filter(user=instance)
        total_commission_earned = referrals.aggregate(total_commission=models.Sum('commission_earned'))['total_commission'] or 0
        

        response_data = {
            'total_deposit': total_deposit,
            'total_withdrawal': total_withdrawal+total_commission_earned,
            'transactions': serializer.data
        }
        return Response(response_data)
    

class CommissionViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data['sender']
        user_walletaddress = sender.wallet_address
        user_referral = sender.referred_by
        user_referral_tpye = user_referral.user.user_type
        print("wallllllet",user_referral_tpye)
        node = serializer.validated_data['node']
        amount = serializer.validated_data['node_quantity']
        transaction_type = serializer.validated_data['transaction_type']
        commission_percentage = node.node_commission_percentage

        # if user_referral_tpye == 'MasterNode':
            # referral_commission = amount * commission_percentage/100
            # Transaction.objects.create(sender=user_referral, amount=commission_amount, transaction_type='Commission Earned')
            
        node_id = serializer.validated_data.get('node_id')
        node = serializer.validated_data.get('node')
        referral_commission = amount * node.node_commission_percentage/100
        master_node = MasterNode.objects.filter(node = node).order_by('-pk')[0]

        try:
            if not master_node.parent_node:
                master_node1id = master_node.master_node_id
            elif master_node.parent_node:
                master_node1id = master_node.parent_node.master_node_id
                master_node2id = master_node.master_node_id
        except:
            return Response({"Message": "No master node found...."})

        if transaction_type == 'ETH 2.0 Node':
            # if sender.referred_by.user.referral_code == node_id or :
            # commission_amount = amount * commission_percentage/100
            # elif sender.referred_by.user.referral_code == master_node
            print("1")
            if sender.referred_by and sender.referred_by.commission_received == False:
                referral = sender.referred_by
                referred_by_user = sender.referred_by.user
                referred_by_maturity = referred_by_user.maturity
                user_ref_commision = referral.commission_earned
                print("1")

                if referred_by_maturity - referred_by_user.claimed_reward >= referral_commission:
                    referred_by_user.claimed_reward += referral_commission
                    referred_by_user.save()
                    referral.increase_commission_earned(referral_commission)
                    commission_transaction = Transaction.objects.create(
                        sender=sender,
                        amount=referral_commission,
                        transaction_type='Commission'
                    )
                    referral.commission_transactions = commission_transaction
                    referral.user.claimed_reward += referral_commission
                    referral.save()
                    serializer.save(amount = amount)
                    sender.maturity += amount*2
                    sender.referred_by.mark_commission_received()
                    sender.total_deposit += amount
                    sender.save()
                    print("3")

                elif referred_by_maturity - referred_by_user.claimed_reward < referral_commission and referred_by_maturity- referred_by_user.claimed_reward != 0:
                    commision_added = referred_by_maturity - referred_by_user.claimed_reward
                    referred_by_user.claimed_reward += commision_added
                    referred_by_user.save()
                    referral.increase_commission_earned(commision_added)
                    commission_transaction = Transaction.objects.create(
                        # sender=referral.user,
                        sender=sender,
                        amount=commision_added,
                        transaction_type='Commission'
                    )
                    referral.commission_transactions = commission_transaction

                    referral.save()
                    serializer.save(amount = amount)
                    sender.maturity += amount*2
                    sender.total_deposit += amount
                    sender.referred_by.mark_commission_received()
                    sender.save()
                    print("4")
                
                else:
                    
                    sender.maturity += amount*2
                    sender.total_deposit += amount
                    sender.save()
                    serializer.save(amount = amount)

            else:
                sender.maturity += amount*2
                sender.total_deposit += amount
                sender.save()
                serializer.save(amount = amount)


        return super().create(request, *args, **kwargs)



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


# class NodePerformanceViewset(viewsets.GenericViewSet, ListModelMixin):

#     def list(self, request, *args, **kwargs):
#         generated_reward = 
#         return super().list(request, *args, **kwargs)

