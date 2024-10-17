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
from .serializers import (
    ClientUserSerializer,
    ReferralSerializer,
    TransactionSerializer,
    ClientWalletDetialSerailizer,
    ClaimSerializer,
    NodePassAuthorizedSerializer,
    FirstTimeBuyingSerializer,
)
from .utils import (
    generate_referral_code,
    get_chain_node_type,
    distribute_to_partners,
    handle_commission_transfer,
)
from StashAdmin.models import BaseUser, NodePartner, NodeSetup, MasterNode
from StashAdmin.serializers import NodeSetupSerializer
import requests
from StashBackend.settings import api_key


class ClientUserViewSet(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = ClientUserSerializer
    lookup_field = "wallet_address"

    def create(self, request):

        new_user_referral_code = generate_referral_code()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(referral_code=new_user_referral_code)
        serializer_data = serializer.data

        return Response(serializer_data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):

        try:
            wallet_address_from_cookie = request.query_params.get("address")
            instance = (
                ClientUser.objects.select_related("referred_by")
                .prefetch_related("transactions")
                .get(wallet_address=wallet_address_from_cookie)
            )

        except (ObjectDoesNotExist, ValueError):
            return Response(
                {"detail": "User not found or invalid address"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        try:
            referrals = Referral.objects.filter(user=instance)
            total_referred_users = (
                referrals.aggregate(total_users=models.Sum("no_of_referred_users"))[
                    "total_users"
                ]
                or 0
            )
            total_commission_earned = (
                referrals.aggregate(total_commission=models.Sum("commission_earned"))[
                    "total_commission"
                ]
                or 0
            )
            if instance.referred_by:
                referred_by_code = instance.referred_by.user.referral_code
            else:
                referred_by_code = None

        except:
            referrals = 0
        serializer_data = serializer.data
        # nodes = Transaction.objects.filter(sender = instance, transaction_type = 'ETH 2.0 Node').aggregate(nodes = Sum('node_quantity'))['nodes'] or 0
        # total_eth2_nodes_count = Transaction.objects.filter(sender = instance, transaction_type = 'ETH 2.0 Node').aggregate(total_eth2_nodes_count = Sum('node_quantity'))['total_eth2_nodes_count'] or 0
        stake_swim_boostcount = (
            Transaction.objects.filter(
                sender=instance, transaction_type="Stake & Swim Boost"
            ).aggregate(stake_swim_quantity=Sum("stake_swim_quantity"))[
                "stake_swim_quantity"
            ]
            or 0
        )
        # total_super_nodes_count = Transaction.objects.filter(transaction_type = 'Generated SuperNode').aggregate(super_node_eth2 = Sum('super_node_eth2'))['super_node_eth2'] or 0
        total_nodes_operators_count = (
            Transaction.objects.filter(
                sender=instance, transaction_type="Nodes Operators"
            ).aggregate(supernode_quantity=Sum("supernode_quantity"))[
                "supernode_quantity"
            ]
            or 0
        )
        # generated_subnodes = Transaction.objects.filter(sender = instance, transaction_type = 'Generated SubNode' )
        # generated_subnodes_count = generated_subnodes.count()
        # total_commission_earned = generated_subnodes.aggregate(revenue = Sum('amount'))['revenue'] or 0
        total_eth2_nodes_count = (
            Transaction.objects.filter(sender=instance).aggregate(
                node_quantity=Sum("node_quantity")
            )["node_quantity"]
            or 0
        )
        total_master_nodes_count = (
            Transaction.objects.filter(sender=instance).aggregate(
                master_node_eth2=Sum("master_node_eth2")
            )["master_node_eth2"]
            or 0
        )
        total_super_nodes_count = (
            Transaction.objects.filter(sender=instance).aggregate(
                super_node_eth2=Sum("super_node_eth2")
            )["super_node_eth2"]
            or 0
        )

        # serializer_data['referral'] = total_referred_users
        serializer_data["total_eth2_nodes_count"] = total_eth2_nodes_count
        serializer_data["stake_swim_boostcount"] = stake_swim_boostcount
        serializer_data["total_nodes_operators_count"] = total_nodes_operators_count
        serializer_data["total_super_nodes_count"] = total_super_nodes_count
        serializer_data["total_master_nodes_count"] = total_master_nodes_count
        serializer_data["referred_by_code"] = referred_by_code

        return Response(serializer_data, status=status.HTTP_200_OK)


class UserLoginViewset(viewsets.ViewSet):
    def create(self, request):
        wallet_address = request.query_params.get("address")

        try:
            user = BaseUser.objects.get(wallet_address=wallet_address)
            response = Response({"message": "Login successful"})
            max_age_30_days = timedelta(days=30)
            response.set_cookie(
                "wallet_address", wallet_address, max_age=max_age_30_days
            )
            return response
        except ClientUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class GetRefAdressViewset(viewsets.GenericViewSet, ListModelMixin):

    def list(self, request, *args, **kwargs):

        ref_code = request.query_params.get("ref")
        if not ref_code:
            return Response(
                {"error": "Referral code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_with_referral_code = ClientUser.objects.get(
                referral_code=ref_code)
        except ClientUser.DoesNotExist:
            return Response(
                {"error": "Invalid referral code"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            admin_node = NodeSetup.objects.first().user.wallet_address
        except:
            return Response(
                {"error": "Invalid node setup"}, status=status.HTTP_400_BAD_REQUEST
            )

        referral = user_with_referral_code.referred_by
        super_node_ref = getattr(referral.super_node_ref, "wallet_address", "")
        master_node_ref = getattr(
            referral.master_node_ref, "wallet_address", "")
        sub_node_ref = getattr(referral.sub_node_ref, "wallet_address", "")
        admin_node_ref = admin_node

        response_data = {
            "super_node_ref": super_node_ref,
            "master_node_ref": master_node_ref,
            "sub_node_ref": sub_node_ref,
            "admin_node_ref": admin_node_ref,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class ClientWalletDetialViewset(viewsets.GenericViewSet, ListModelMixin):

    serializer_class = ClientUserSerializer

    def list(self, request, *args, **kwargs):

        try:
            wallet_address_from_cookie = request.query_params.get("address")
            instance = (
                ClientUser.objects.select_related("referred_by")
                .prefetch_related("transactions")
                .get(wallet_address=wallet_address_from_cookie)
            )

        except (ObjectDoesNotExist, ValueError):
            return Response(
                {"detail": "User not found or invalid address"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            referrals = Referral.objects.filter(user=instance)
            total_referred_users = (
                referrals.aggregate(total_users=models.Sum("no_of_referred_users"))[
                    "total_users"
                ]
                or 0
            )

        except:
            referrals = 0
        instance.save()
        serializer = self.get_serializer(instance)
        serializer_data = serializer.data
        serializer_data["referral"] = total_referred_users
        return Response(serializer_data, status=status.HTTP_200_OK)


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer

    def list(self, request, pk=None):

        try:
            wallet_address_from_cookie = request.query_params.get("address")
            instance = ClientUser.objects.get(
                wallet_address=wallet_address_from_cookie)
        except (ObjectDoesNotExist, ValueError):
            return Response(
                {"detail": "User not found or invalid address"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            referrals = Referral.objects.filter(user=instance)
        except Referral.DoesNotExist:
            return Response(
                {"error": "Referral not found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(referrals, many=True)
        total_referred_users = (
            referrals.aggregate(total_users=models.Sum("no_of_referred_users"))[
                "total_users"
            ]
            or 0
        )
        total_commission_earned = (
            referrals.aggregate(total_commission=models.Sum("commission_earned"))[
                "total_commission"
            ]
            or 0
        )

        return Response(
            {
                "no_of_referred_users": total_referred_users,
                "commission_earned": total_commission_earned,
            }
        )


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = ClaimSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = [
        "sender__wallet_address",
        "sender__referred_by__user__wallet_address",
        "transaction_type",
    ]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data["sender"]
        user_referral = sender.referred_by
        node = serializer.validated_data["node"]
        total_amount = serializer.validated_data["amount"]
        transaction_type = serializer.validated_data["transaction_type"]
        block_id = serializer.validated_data.get("block_id")
        trx_hash = serializer.validated_data.get("trx_hash")
        node_id = serializer.validated_data.get("node_id")
        node = serializer.validated_data.get("node")
        referral_commission = total_amount * node.reward_claim_percentage / 100
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
                return Response(
                    {"message": "User dont have referral"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        referral_commission_master_node = 0
        referral_commission_super_node = 0
        referral_commission_admin_user = 0

        if referred_super_node:
            if referred_master_node:
                referral_commission_super_node = (
                    referral_commission
                    * node.extra_super_node_reward_claim_percentage
                    / 100
                )
                referral_commission_master_node = (
                    referral_commission
                    * node.extra_master_node_reward_claim_percentage
                    / 100
                )
                referral_commission_admin_user = (
                    referral_commission
                    - referral_commission_super_node
                    - referral_commission_master_node
                )
            else:
                referral_commission_super_node = (
                    referral_commission
                    * node.extra_super_node_reward_claim_percentage
                    / 100
                )
                referral_commission_admin_user = (
                    referral_commission - referral_commission_super_node
                )

        elif referred_master_node:
            referral_commission_master_node = (
                referral_commission
                * node.extra_master_node_reward_claim_percentage
                / 100
            )
            referral_commission_admin_user = (
                referral_commission - referral_commission_master_node
            )

        else:
            referral_commission_admin_user = referral_commission

        if referral_commission_super_node:
            Transaction.objects.create(
                sender=referred_super_node,
                amount=referral_commission_super_node,
                transaction_type="Generated SubNode",
                generated_subnode_type="GeneratedSuperSubNode",
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                block_id=block_id,
                referred_wallet_address=sender,
            )
            referred_super_node.claimed_reward += referral_commission_super_node
            referred_super_node.save()

        if referral_commission_master_node:

            Transaction.objects.create(
                sender=referred_master_node,
                amount=referral_commission_master_node,
                transaction_type="Generated SubNode",
                generated_subnode_type="GeneratedMasterSubNode",
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                block_id=block_id,
                referred_wallet_address=sender,
            )
            referred_master_node.claimed_reward += referral_commission_master_node
            referred_master_node.save()

        if referral_commission_admin_user:

            Transaction.objects.create(
                sender=admin_user,
                amount=referral_commission_admin_user,
                transaction_type="Generated SubNode",
                generated_subnode_type="GeneratedAdminSubNode",
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                block_id=block_id,
                referred_wallet_address=sender,
            )
            admin_user.claimed_reward += referral_commission_admin_user
            admin_user.save()

        Transaction.objects.create(
            sender=sender,
            amount=total_amount,
            transaction_type="Reward Claim",
            trx_hash=trx_hash,
            node_id=node_id,
            node=node,
            block_id=block_id,
        )
        sender.claimed_reward -= total_amount
        sender.save()

        return Response({"message": "Transaction created successfully"})

    def list(self, request, *args, **kwargs):
        wallet_address = request.query_params.get("walletadd")
        try:
            sender = ClientUser.objects.get(wallet_address=wallet_address)
        except:
            return Response({"Message": "Invalid wallet address...."})
        total_revenue = (
            Transaction.objects.filter(
                sender=sender, transaction_type="Generated SubNode"
            ).aggregate(total_generated_trxs=Sum("amount"))["total_generated_trxs"]
            or 0
        )

        return Response({"total_revenue": total_revenue}, status=status.HTTP_200_OK)


class TransactionViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = [
        "sender__wallet_address",
        "sender__referred_by__user__wallet_address",
        "transaction_type",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(
                transaction_type__in=[
                    "Nodes Operators",
                    "Generated SubNode",
                    "Stake & Swim Boost",
                    "ETH 2.0 Node",
                    "Generated SuperNode",
                    "Generated SuperNode",
                ]
            )
            .annotate(
                nodepass=F("sender__referral_code"),
                referred_nodepass=F(
                    "referred_wallet_address__referral_code") or None,
                # referred_wallet_address = F('sender__referred_by__user__wallet_address')
            )
            .order_by("-timestamp")
        )
        wallet_address = self.request.query_params.get("address")
        all = self.request.query_params.get("all")
        if all:
            queryset = (
                Transaction.objects.all()
                .annotate(
                    nodepass=F("sender__referral_code"),
                    referred_nodepass=F(
                        "referred_wallet_address__referral_code"),
                    # referred_wallet_address = F('sender__referred_by__user__wallet_address')
                )
                .order_by("-timestamp")
            )
        if wallet_address:
            queryset = (
                queryset.filter(sender__wallet_address=wallet_address)
                .annotate(
                    nodepass=F("sender__referral_code"),
                    referred_nodepass=F(
                        "referred_wallet_address__referral_code"),
                    # referred_wallet_address = F('sender__referred_by__user__wallet_address')
                )
                .order_by("-timestamp")
            )
        return queryset

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data["sender"]
        user_referral = sender.referred_by
        node = serializer.validated_data["node"]
        amount = serializer.validated_data.get("node_quantity", 0)
        transaction_type = serializer.validated_data["transaction_type"]
        node_quantity = serializer.validated_data.get("node_quantity", 0)
        block_id = serializer.validated_data.get("block_id")
        setup_charges = serializer.validated_data.pop("setup_charges")
        if not setup_charges:
            setup_charges = 100

        server_type = serializer.validated_data.get("server_type")
        trx_hash = serializer.validated_data.get("trx_hash")
        stake_swim_quantity = serializer.validated_data.get(
            "stake_swim_quantity", 0)
        supernode_quantity = serializer.validated_data.get(
            "supernode_quantity", 0)
        master_node_eth2_quantity = serializer.validated_data.get(
            "master_node_eth2", 0)
        super_node_eth2_quantity = serializer.validated_data.get(
            "super_node_eth2", 0)
        if master_node_eth2_quantity:
            if sender.user_type != "MasterNode":
                return Response({"message": "User is not masternode"})

        if super_node_eth2_quantity:
            if sender.user_type != "SuperNode":
                return Response({"message": "User is not Supernode"})

        total_amount_node = node_quantity * node.cost_per_node if node_quantity else 0
        total_amount_stake = (
            stake_swim_quantity * node.booster_node_1_cost if stake_swim_quantity else 0
        )
        total_amount_super = (
            supernode_quantity * node.booster_node_2_cost if supernode_quantity else 0
        )
        master_node_eth2 = (
            master_node_eth2_quantity * node.master_node_cost
            if master_node_eth2_quantity
            else 0
        )
        super_node_eth2 = (
            super_node_eth2_quantity * node.super_node_cost
            if super_node_eth2_quantity
            else 0
        )
        total_amount = (
            total_amount_node
            + total_amount_stake
            + total_amount_super
            + master_node_eth2
            + super_node_eth2
        )

        node_id = serializer.validated_data.get("node_id")
        node = serializer.validated_data.get("node")
        referral_commission_node = total_amount * node.node_commission_percentage / 100
        referral_commission_super = (
            total_amount * node.extra_super_node_commission / 100
        )
        referral_commission_master = (
            total_amount * node.extra_master_node_commission / 100
        )
        referral_commission_super_node = 0
        referral_commission_master_node = 0
        referral_commission_subnode_node = 0

        try:
            referred_by_user = sender.referred_by
            referral = referred_by_user

            referred_super_node = referral.super_node_ref
            referred_master_node = referral.master_node_ref
            referred_sub_node = referral.sub_node_ref
        except AttributeError:
            referred_by_user = None
            referred_super_node = None
            referred_master_node = None
            referred_sub_node = None

            if not referred_by_user:
                return Response(
                    {"message": "User dont have referral"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

        if referred_master_node:
            if referred_sub_node:

                referral_commission_master_node = referral_commission_master
                referral_commission_subnode_node = referral_commission_node

            else:
                referral_commission_master_node = referral_commission_master

        if referred_sub_node:
            referral_commission_subnode_node = referral_commission_node

        else:
            # admin is the referral!!!
            referral_commission = 0

        if referral_commission_super_node:
            if sender.is_purchased:

                # handle_commission_transfer(sender, referred_by_user, referred_super_node, referral_commission_super_node, block_id, node_id, node, server_type, trx_hash,  node_quantity, master_node_eth2_quantity, super_node_eth2_quantity, generated_subnode_type = 'GeneratedSuperSubNode',)
                Transaction.objects.create(
                    sender=referred_super_node,
                    amount=referral_commission_super_node,
                    transaction_type="Generated SubNode",
                    block_id=block_id,
                    node_id=node_id,
                    node=node,
                    server_type=server_type,
                    trx_hash=trx_hash,
                    stake_swim_quantity=0,
                    supernode_quantity=0,
                    node_quantity=0,
                    generated_subnode_type="GeneratedSuperSubNode",
                    referred_wallet_address=sender,
                )
                referred_super_node.total_subnode_generated += node_quantity
                referred_super_node.save()

        if referral_commission_master_node:
            # handle_commission_transfer(sender, referred_by_user, referred_master_node, referral_commission_master_node, block_id, node_id, node, server_type, trx_hash, node_quantity, master_node_eth2_quantity, super_node_eth2_quantity, generated_subnode_type = 'GeneratedMasterSubNode')
            if sender.is_purchased:

                Transaction.objects.create(
                    sender=referred_master_node,
                    amount=referral_commission_master_node,
                    transaction_type="Generated SubNode",
                    block_id=block_id,
                    node_id=node_id,
                    node=node,
                    server_type=server_type,
                    trx_hash=trx_hash,
                    stake_swim_quantity=0,
                    supernode_quantity=0,
                    node_quantity=0,
                    generated_subnode_type="GeneratedMasterSubNode",
                )
                referred_master_node.total_subnode_generated += node_quantity
                referred_master_node.save()

        if referral_commission_subnode_node:
            if referred_by_user.commission_received == False:
                handle_commission_transfer(
                    sender,
                    referred_by_user,
                    referred_sub_node,
                    referral_commission_subnode_node,
                    block_id,
                    node_id,
                    node,
                    server_type,
                    trx_hash,
                    node_quantity,
                    master_node_eth2_quantity,
                    super_node_eth2_quantity,
                    generated_subnode_type="GeneratedClientSubNode",
                )

        if super_node_eth2_quantity:
            Transaction.objects.create(
                sender=sender,
                amount=super_node_eth2,
                transaction_type="Generated SuperNode",
                block_id=block_id,
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                server_type=server_type,
                super_node_eth2=super_node_eth2_quantity,
                setup_charges=setup_charges,
            )
            sender.is_supernode_masternode_purchased = True
            sender.total_deposit += super_node_eth2
            sender.maturity += super_node_eth2 * 2
            sender.save()

        elif master_node_eth2_quantity:
            Transaction.objects.create(
                sender=sender,
                amount=master_node_eth2,
                transaction_type="Generated MasterNode",
                block_id=block_id,
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                server_type=server_type,
                master_node_eth2=master_node_eth2_quantity,
                setup_charges=setup_charges,
            )
            sender.is_supernode_masternode_purchased = True
            sender.total_deposit += master_node_eth2
            sender.maturity += master_node_eth2 * 2
            sender.save()

        else:
            Transaction.objects.create(
                sender=sender,
                amount=total_amount_node,
                node_quantity=node_quantity,
                transaction_type="ETH 2.0 Node",
                block_id=block_id,
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                server_type=server_type,
                setup_charges=setup_charges,
            )
            sender.is_purchased = True
            sender.total_deposit += total_amount_node
            sender.maturity += total_amount_node * 2
            sender.save()

        if stake_swim_quantity:
            Transaction.objects.create(
                sender=sender,
                amount=total_amount_stake,
                transaction_type="Stake & Swim Boost",
                block_id=block_id,
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                server_type=server_type,
                stake_swim_quantity=stake_swim_quantity,
            )
            sender.total_deposit += total_amount_stake
            sender.maturity += total_amount_stake * 2
            sender.save()
        if supernode_quantity:
            Transaction.objects.create(
                sender=sender,
                amount=total_amount_super,
                transaction_type="Nodes Operators",
                block_id=block_id,
                trx_hash=trx_hash,
                node_id=node_id,
                node=node,
                server_type=server_type,
                supernode_quantity=supernode_quantity,
            )
            sender.total_deposit += total_amount_super
            sender.maturity += total_amount_super * 2
            sender.save()

        distribute_to_partners(sender, node, setup_charges, block_id, trx_hash)
        sender.is_purchased = True
        sender.save()
        return Response(
            {"message": "Transaction successfully created"},
            status=status.HTTP_201_CREATED,
        )


class ServerInformationViewset(viewsets.GenericViewSet, ListModelMixin):

    def list(self, request, *args, **kwargs):
        try:
            node = NodeSetup.objects.all()[-1]
            node_id = node.node_id
            transactions = Transaction.objects.all()

            generated_subnodes = (
                transactions.filter(
                    transaction_type="Generated SubNode").count() or 0
            )
            return Response(
                {"node_id": node_id, "generated_subnodes": generated_subnodes},
                status=status.HTTP_200_OK,
            )
        except:
            return Response(
                {"detail": "No node found"}, status=status.HTTP_404_NOT_FOUND
            )


class AuthorizedNodeViewset(viewsets.ModelViewSet):
    # queryset = ClientUser.objects.all()
    serializer_class = NodePassAuthorizedSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ref_code = serializer.validated_data.get("referral_code")
        user_wallet_address = serializer.validated_data.get(
            "user_wallet_address")
        if not ref_code:
            return Response(
                {"error": "Licensed node pass is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_with_referral_code = ClientUser.objects.get(
                referral_code=ref_code)
            try:
                referral = Referral.objects.create(
                    user=user_with_referral_code)
            except Referral.DoesNotExist:
                return Response(
                    {"error": "Error to create ref."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ClientUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            user = ClientUser.objects.get(wallet_address=user_wallet_address)
        except ClientUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if user.user_type == "SuperNode" or user.user_type == "MasterNode":
            if user_with_referral_code.user_type == "Client":
                return Response(
                    {"error": "Node can't authorize this type of node."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        user.referred_by = referral

        try:
            if referral.user.user_type == "SuperNode":
                referral.super_node_ref = referral.user
            elif referral.user.user_type == "MasterNode":
                referral.super_node_ref = referral.user.referred_by.user
                referral.master_node_ref = referral.user
            elif referral.user.user_type == "Client":
                referral.super_node_ref = referral.user.referred_by.super_node_ref
                referral.master_node_ref = referral.user.referred_by.master_node_ref
                referral.sub_node_ref = referral.user
            referral.save()
        except AttributeError as e:
            return Response(
                {"error": "MasterNode or SuperNode reference not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.save()
        referral.increase_referred_users()

        return Response("Liscenced Node is authorized", status=status.HTTP_200_OK)


class ExhaustedNodeViewset(viewsets.ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = ClientUserSerializer

    def list(self, request, *args, **kwargs):
        try:
            exhausted_users = ClientUser.objects.filter(
                maturity=F("claimed_reward"))
            transactions_list = Transaction.objects.filter(
                sender__in=exhausted_users, transaction_type="ETH 2.0 Node"
            )
            eth_node_sum = (
                transactions_list.aggregate(node_quantity=Sum("node_quantity"))[
                    "node_quantity"
                ]
                or 0
            )
            stake_boost_sum = (
                Transaction.objects.filter(
                    sender__in=exhausted_users, transaction_type="Stake & Swim Boost"
                ).aggregate(stake_swim_quantity=Sum("stake_swim_quantity"))[
                    "stake_swim_quantity"
                ]
                or 0
            )
            super_boost_sum = (
                Transaction.objects.filter(
                    sender__in=exhausted_users, transaction_type="Nodes Operators"
                ).aggregate(supernode_quantity=Sum("supernode_quantity"))[
                    "supernode_quantity"
                ]
                or 0
            )
            revenue_generated = (
                Transaction.objects.filter(
                    sender__in=exhausted_users, transaction_type="ETH 2.0 Node"
                ).aggregate(amount=Sum("amount"))["amount"]
                or 0
            )
            timestamp = transactions_list.first().timestamp
            return Response(
                {
                    "eth_node_sum": eth_node_sum,
                    "stake_boost_sum": stake_boost_sum,
                    "super_boost_sum": super_boost_sum,
                    "revenue_generated": revenue_generated,
                    "timestamp": timestamp,
                }
            )
        except:
            return Response(
                {"detail": "No exhausted nodes found"}, status=status.HTTP_404_NOT_FOUND
            )


class GeneratedSubNodesViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.filter(transaction_type="Generated SubNode")
    serializer_class = TransactionSerializer

    def list(self, request, *args, **kwargs):
        address = request.query_params.get("address", None)

        if address:
            try:
                user = ClientUser.objects.get(wallet_address=address)
            except ClientUser.DoesNotExist:
                return Response(
                    {"detail": "User with this address does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            generated_trxs = Transaction.objects.filter(
                sender=user,
                transaction_type__in=[
                    "Generated SubNode", "Generated MasterNode"],
            )
            total_subnodes = (
                generated_trxs.filter(
                    transaction_type="Generated SubNode").count() or 0
            )
            total_masternodes = (
                generated_trxs.filter(
                    generated_subnode_type="GeneratedMasterSubNode"
                ).count()
                or 0
            )
            total_revenue = (
                generated_trxs.aggregate(total_generated_trxs=Sum("amount"))[
                    "total_generated_trxs"
                ]
                or 0
            )
        else:
            return Response(
                {"message": "User address not entered"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(generated_trxs, many=True)

        return Response(
            {
                "generated_trxs": serializer.data,
                "total_subnodes": total_subnodes,
                "total_revenue": total_revenue,
                "total_masternodes": total_masternodes,
            }
        )


class EthereumDataVewiset(viewsets.GenericViewSet, ListModelMixin):
    def list(self, request, *args, **kwargs):
        api = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH"
        headers = {
            "X-CMC_PRO_API_KEY": api_key,
        }
        try:
            response = requests.get(url=api, headers=headers)
        except Exception as e:
            return Response(
                {"detail": str(e) + "Unable to fetch Ethereum data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return HttpResponse(response._content, status=status.HTTP_200_OK)


class FirstTimeBuyingViewset(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = FirstTimeBuyingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_wallet_address = serializer.validated_data.get("sender")
        trx_hash = serializer.validated_data.get("trx_hash")
        block_id = serializer.validated_data.get("block_id")
        setup_charges = serializer.validated_data.get("setup_charges", None)
        server_type = serializer.validated_data.get("server_type", None)

        try:
            user = ClientUser.objects.get(wallet_address=user_wallet_address)
            if user.is_purchased:
                return Response(
                    {"error": "User has already made a first-time buying"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            node = NodeSetup.objects.first()
            super_node_amount = node.super_node_cost
            master_node_amount = node.master_node_cost
            if user.user_type == "MasterNode":
                amount = master_node_amount
                # transaction_type = "MasterNode Nodepass"
            elif user.user_type == "SuperNode":
                amount = super_node_amount
                # transaction_type = "SuperNode Nodepass"
            else:
                return Response(
                    {"error": "User type is not masternode or supernode"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Transaction.objects.create(
            #     sender=user,
            #     amount=amount,
            #     server_type=server_type,
            #     trx_hash=trx_hash,
            #     transaction_type=transaction_type,
            # )
            distribute_to_partners(
                user, node, amount + setup_charges, block_id, trx_hash
            )
            user.is_purchased = True
            user.save()
            if user.user_type == 'MasterNode':
                user.referred_by.user.total_masternode_generated += 1
            # user.total_deposit += amount
            # user.maturity += amount * 2
                user.referred_by.user.save()
                user.referred_by.save()
            return Response({"message": "First-time buying successful"}, status=status.HTTP_200_OK)
        except:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        # return super().create(request, *args, **kwargs)
