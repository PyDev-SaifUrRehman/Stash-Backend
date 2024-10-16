from decimal import Decimal
import random
import string

from StashAdmin.models import NodeSetup, MasterNode, NodePartner
from StashClient.models import ClientUser, Transaction, Referral
from rest_framework.response import Response


def generate_referral_code():
    part1 = "".join(random.choices(string.digits, k=2)) + "".join(
        random.choices(string.ascii_uppercase, k=2)
    )
    part2 = random.choice(string.ascii_uppercase) + "".join(
        random.choices(string.digits, k=2)
    )
    random_string = f"{part1}-{part2}"
    return random_string


def get_chain_node_type(user_with_referral_code):
    try:
        admin_node = NodeSetup.objects.first().node_id
    except:
        return {"error": "Invalid node setup"}

    master_node_ref = MasterNode.objects.get(parent_node__isnull=False)
    master_node_ref_child_node = master_node_ref.master_node_id
    master_node_ref_parent_node = (
        master_node_ref.parent_node.master_node_id
        if master_node_ref.parent_node
        else None
    )

    while True:
        referral_code = user_with_referral_code.referred_by.user.referral_code

        if referral_code == master_node_ref_child_node:
            return {"type": "child", "value": master_node_ref_child_node}
        elif referral_code == master_node_ref_parent_node:
            return {"type": "parent", "value": master_node_ref_parent_node}
        elif referral_code == admin_node:
            return {"type": "admin", "value": admin_node}

        try:
            user_with_referral_code = user_with_referral_code.referred_by.user
        except AttributeError:
            return {"error": "Master node not found in referral chain"}


def distribute_to_partners(sender, node, claim_fee, block_id, trx_hash):
    print("sender parterrrrr", sender.referral_code)
    try:
        node_partners = NodePartner.objects.filter(node=node)
    except NodePartner.DoesNotExist:
        return Response({"Message": "No node partners found...."})

    for partner in node_partners:
        partner_user, _ = ClientUser.objects.get_or_create(
            wallet_address=partner.partner_wallet_address
        )
        Transaction.objects.create(
            sender=partner_user,
            amount=claim_fee * partner.share / 100,
            transaction_type="Generated SubNode",
            block_id=block_id,
            trx_hash=trx_hash,
            referred_wallet_address=sender,
        )
        partner_user.claimed_reward += claim_fee * partner.share / 100
        partner_user.save()

    return


def handle_commission_transfer(
    sender,
    referred_by_user,
    referred_user,
    referral_commission,
    block_id,
    node_id,
    node,
    server_type,
    trx_hash,
    node_quantity,
    master_node_eth2_quantity,
    super_node_eth2_quantity,
    generated_subnode_type,
):
    referred_by_maturity = referred_user.maturity
    # referral = referred_user.referred_by
    referral = referred_by_user
    print("referreddd", referred_by_maturity, referred_user.claimed_reward)

    if referred_by_maturity - referred_user.claimed_reward >= referral_commission:
        commission_amount = Decimal(referral_commission)
        referred_user.claimed_reward += commission_amount
        referred_user.save()
        referral.increase_commission_earned(commission_amount)
        commission_transaction = Transaction.objects.create(
            sender=referred_user,
            amount=commission_amount,
            transaction_type="Generated SubNode",
            block_id=block_id,
            node_id=node_id,
            node=node,
            server_type=server_type,
            trx_hash=trx_hash,
            stake_swim_quantity=0,
            supernode_quantity=0,
            node_quantity=0,
            generated_subnode_type=generated_subnode_type,
            referred_wallet_address=sender,
        )
        referral.commission_transactions = commission_transaction
        if referred_user.user_type == "Client":
            referral.mark_commission_received()
        referral.save()
        # referred_user.save()
        if node_quantity:
            referred_user.total_subnode_generated += node_quantity
        # if master_node_eth2_quantity:
        #     referred_user.total_masternode_generated += master_node_eth2_quantity
        # if super_node_eth2_quantity:
        #     referred_user.total_supernode_generated += super_node_eth2_quantity
        referred_user.save()
        return commission_transaction, commission_amount

    elif (
        referred_by_maturity - referred_user.claimed_reward < referral_commission
        and referred_by_maturity - referred_user.claimed_reward != 0
    ):
        commision_added = referred_by_maturity - referred_user.claimed_reward
        commision_added = Decimal(commision_added)
        referred_user.claimed_reward += commision_added
        referred_user.save()
        referral.increase_commission_earned(commision_added)
        commission_transaction = Transaction.objects.create(
            sender=referred_user,
            amount=commision_added,
            transaction_type="Generated SubNode",
            block_id=block_id,
            node_id=node_id,
            node=node,
            server_type=server_type,
            trx_hash=trx_hash,
            stake_swim_quantity=0,
            supernode_quantity=0,
            node_quantity=0,
            generated_subnode_type=generated_subnode_type,
            referred_wallet_address=sender,
        )
        referral.commission_transactions = commission_transaction
        if referred_user.user_type == "Client":
            referral.mark_commission_received()
        referral.save()
        if node_quantity:
            referred_user.total_subnode_generated += node_quantity
        # if master_node_eth2_quantity:
        #     referred_user.total_masternode_generated += master_node_eth2_quantity
        # if super_node_eth2_quantity:
        #     referred_user.total_supernode_generated += super_node_eth2_quantity
        referred_user.save()
        return commission_transaction, commision_added

    return None, 0
