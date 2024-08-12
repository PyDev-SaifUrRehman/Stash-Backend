from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import NodeSetup, MasterNode, NodeManager, NodePartner, AdminReferral, NodePayout, NodeSuperNode
from StashClient.models import ClientUser, Referral
from StashClient.utils import generate_referral_code

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientUser
        fields = '__all__'
        read_only_fields = ['referral_code', 'referred_by']


    def validate_wallet_address(self, value):
        if ClientUser.objects.filter(wallet_address=value).exists():
            raise serializers.ValidationError("Address already registered!!")
        return value


class ParentMasterNodeSerializer(serializers.ModelSerializer):
    node = serializers.CharField()

    class Meta:
        model = MasterNode
        fields = '__all__'

    def validate(self, attrs):
        qp_wallet_address = self.context['request'].query_params.get(
            'address')
        if qp_wallet_address:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=qp_wallet_address)
                print("asd", admin_user.user_type)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            wallet_address = attrs['wallet_address'] 
            referral_code = attrs['master_node_id'] 
            referred_by_user = NodeSetup.objects.first().user
            referred_by = Referral.objects.create(user = referred_by_user)
            master_node, created = ClientUser.objects.get_or_create(wallet_address=wallet_address, referred_by = referred_by, referral_code = referral_code, user_type = 'MasterNode')
            return attrs
        else:
            raise serializers.ValidationError(
                "No admin wallet address added")
        
    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        

class MasterNodeSerializer(serializers.ModelSerializer):
    node = serializers.CharField()
    master_node = serializers.CharField()

    class Meta:
        model = MasterNode
        fields = ['node', 'master_node']

    def validate_node(self, value):
        try:
            supernode = NodeSuperNode.objects.get(super_node__referral_code=value)
            if supernode:
                return supernode
        except NodeSuperNode.DoesNotExist:
            raise serializers.ValidationError("No Supernode node with this Nodepass")
    
    def validate(self, attrs):
        qp_wallet_address = self.context['request'].query_params.get('address')
        if qp_wallet_address:
            try:
                admin_user = ClientUser.objects.get(wallet_address=qp_wallet_address)
            except ClientUser.DoesNotExist:
                raise ValidationError("You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError("You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError("No admin wallet address added")

    def create(self, validated_data):
        super_node = validated_data.get('node')
        master_node_address = validated_data.get('master_node')
        try:
            referral_code = generate_referral_code()
            super_node_ref = super_node.super_node.referral_code

            user_with_referral_code = ClientUser.objects.get(referral_code=super_node_ref)
            referral, _ = Referral.objects.get_or_create(user=user_with_referral_code)

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

            master_node, created = ClientUser.objects.get_or_create(
                wallet_address=master_node_address, 
                user_type='MasterNode', 
                node_type='MasterNode', 
                referral_code=referral_code, 
                referred_by=referral, 
                is_purchased=True
            )

            master_node_instance = MasterNode.objects.create(
                node=super_node,
                master_node=master_node
            )

            return master_node_instance
        except Exception as e:
            raise serializers.ValidationError(f"Not valid Super Node {e}")



class NodeManagerSerializer(serializers.ModelSerializer):
    node = serializers.CharField()
    node_id = serializers.SerializerMethodField(read_only = True)
    manager = serializers.CharField()


    class Meta:
        model = NodeManager
        fields = '__all__'

    def get_node_id(self, obj):
        return obj.node.node_id if obj.node else None
    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        

    def validate(self, attrs):
        qp_wallet_address = self.context['request'].query_params.get(
            'address')
        if qp_wallet_address:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=qp_wallet_address)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No admin wallet address added")
        

    def validate_manager(self, value):
        try:
            node_manager, created = ClientUser.objects.get_or_create(wallet_address=value, user_type = 'Manager')
            manager = ClientUser.objects.get(wallet_address = value)
            if manager:
                return manager
        except:
            raise serializers.ValidationError("Not valid manager")
        


class NodePartnerSerializer(serializers.ModelSerializer):
    node = serializers.CharField()
    
    class Meta:
        model = NodePartner
        fields = '__all__'

    
    def validate(self, attrs):
        qp_wallet_address = self.context['request'].query_params.get(
            'address')
        node = attrs.get('node')
        share = attrs.get('share')
        instance = self.instance
        existing_partners_count = NodePartner.objects.filter(node=node).exclude(pk=instance.pk if instance else None).count()
        if existing_partners_count >= 2:
            raise serializers.ValidationError('A node cannot have more than 2 partners.')

        total_share = NodePartner.objects.filter(node=node).exclude(pk=instance.pk if instance else None).aggregate(total=Sum('share'))['total'] or 0
        total_share += share
        if total_share > 100:
            raise serializers.ValidationError('The total share for a node must not exceed 100%.')
        # return data
        if qp_wallet_address:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=qp_wallet_address)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':

                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No admin wallet address added")       
        
        
    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        


class NodeSetupSerializer(serializers.ModelSerializer):

    node_id = serializers.CharField(read_only = True)
    user = serializers.CharField()
    
    class Meta:
        model = NodeSetup
        fields = '__all__'

    def validate_user(self, value):
        try:
            value = ClientUser.objects.get(wallet_address=value)
            return value
        except ClientUser.DoesNotExist:
            raise serializers.ValidationError("Invalid User")
        
    def validate(self, attrs):
        wallet_address_from_cookie = self.context['request'].query_params.get(
            'address')
        if wallet_address_from_cookie:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=wallet_address_from_cookie)
                print("user", admin_user.user_type)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No wallet address")

class AdminReferralSerializer(serializers.ModelSerializer):
    commission_earned = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    no_of_referred_users = serializers.IntegerField(read_only=True)
    user = serializers.CharField()


    class Meta:
        model = AdminReferral
        fields = ['id', 'user', 'commission_earned',
                  'no_of_referred_users']

    def validate_user(self, value):
        try:
            user = ClientUser.objects.get(wallet_address=value)
            return user
        except ClientUser.DoesNotExist:
            raise serializers.ValidationError("User with this wallet address does not exist")
        
    def validate(self, attrs):
        wallet_address_from_cookie = self.context['request'].query_params.get(
            'address')
        if wallet_address_from_cookie:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=wallet_address_from_cookie)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No wallet address")


class NodePayoutSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = NodePayout
        fields = '__all__'
        

    def validate(self, attrs):
        wallet_address_from_cookie = self.context['request'].query_params.get(
            'address')
        if wallet_address_from_cookie:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=wallet_address_from_cookie)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No wallet address")


class AddNodeToAdminSerializer(serializers.Serializer):
    node_pass = serializers.CharField()
    wallet_address = serializers.CharField()

    admin_added_claimed_reward = serializers.DecimalField(
        max_digits=10, decimal_places=2)

    node_quantity = serializers.IntegerField(default = 0, write_only = True)
    stake_swim_quantity = serializers.IntegerField(default = 0, write_only = True)
    supernode_quantity = serializers.IntegerField(default = 0, write_only = True)
    admin_maturity = serializers.IntegerField(default = 0, write_only = True)
    exhaustion = serializers.IntegerField(default = 0)

    # class Meta:
    #     model = ClientUser
    #     fields = '__all__'
    #     read_only_fields = ['node_pass','user_type', 'maturity', 'total_deposit', 'generated_reward', 'claimed_reward', 'total_revenue', 'admin_added_claimed_reward', 'node_type', 'admin_maturity', 'referred_by', 'referral_code']
    #     extra_kwargs = {
    #         'node_pass': {'write_only': True},
    #         'node_quantity': {'write_only': True},
    #         'supernode_quantity': {'write_only': True},
    #         'stake_swim_quantity': {'write_only': True},
    #         'admin_maturity': {'write_only': True},
        # }
    def validate_wallet_address(self, value):

        if ClientUser.objects.filter(wallet_address=value).exists():
            raise serializers.ValidationError(
                "Wallet address already registered!!")
        return value

    def validate(self, attrs):
        wallet_address_from_cookie = self.context['request'].query_params.get(
            'address')
        if wallet_address_from_cookie:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=wallet_address_from_cookie)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No wallet address")


class NodeSuperNodeSerializer(serializers.ModelSerializer):
    node = serializers.CharField()
    node_id = serializers.SerializerMethodField(read_only = True)
    super_node = serializers.CharField()

    class Meta:
        model = NodeSuperNode
        fields = '__all__'

    def get_node_id(self, obj):
        return obj.node.node_id if obj.node else None
    
    def validate_node(self, value):
        try:
            node = NodeSetup.objects.get(node_id = value)
            if node:
                return node
        except:
            raise serializers.ValidationError("No node with this Id")
        

    def validate(self, attrs):
        qp_wallet_address = self.context['request'].query_params.get(
            'address')
        if qp_wallet_address:
            try:
                admin_user = ClientUser.objects.get(
                    wallet_address=qp_wallet_address)
            except ClientUser.DoesNotExist:
                raise ValidationError(
                    "You don't have permission to perform this action.")

            if admin_user.user_type == 'Client':
                raise ValidationError(
                    "You don't have permission to perform this action.")
            return attrs
        else:
            raise serializers.ValidationError(
                "No admin wallet address added")
        

    def validate_super_node(self, value):
        try:
            referral_code = generate_referral_code()
            referred_by_code = NodeSetup.objects.first().node_id
            # referred_by_user = ClientUser.objects.get(referral_code = referred_by_code)
            try:
                user_with_referral_code = ClientUser.objects.get(
                referral_code=referred_by_code)
                
                try:
                    referral = Referral.objects.create(
                        user=user_with_referral_code)
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
                                
                except Referral.DoesNotExist:
                    raise serializers.ValidationError("Error to create ref.")
            except ClientUser.DoesNotExist:
                return serializers.ValidationError("User not found.")

            
            super_node, created = ClientUser.objects.get_or_create(wallet_address=value, user_type = 'SuperNode', node_type  = 'SuperNode', referral_code = referral_code, referred_by = referral, is_purchased = True)
            supernode = ClientUser.objects.get(wallet_address = value)
            if super_node:
                return super_node
        except Exception as e:
            raise serializers.ValidationError(f"Not valid Super Node {e}")
        
    