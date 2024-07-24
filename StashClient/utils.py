import random
import string

from StashAdmin.models import NodeSetup, MasterNode

def generate_referral_code():
    part1 = ''.join(random.choices(string.digits, k=2)) + ''.join(random.choices(string.ascii_uppercase, k=2))    
    part2 = random.choice(string.ascii_uppercase) + ''.join(random.choices(string.digits, k=2))
    random_string = f"{part1}-{part2}"
    return random_string


def get_chain_node_type(user_with_referral_code):
    try:
        admin_node = NodeSetup.objects.first().node_id
    except:
        return {"error": "Invalid node setup"}
    
    master_node_ref = MasterNode.objects.get(parent_node__isnull=False)
    master_node_ref_child_node = master_node_ref.master_node_id
    master_node_ref_parent_node = master_node_ref.parent_node.master_node_id if master_node_ref.parent_node else None
    
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
