from .models import NodeSetup, MasterNode, NodeManager, NodePartner, AdminUser, AdminReferral, NodePayout
from rest_framework import serializers
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from StashClient.utils import generate_referral_code
from StashClient.models import ClientUser, Referral

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientUser
        fields = '__all__'
        read_only_fields = ['referral_code', 'referred_by']


    def validate_wallet_address(self, value):
        if ClientUser.objects.filter(wallet_address=value).exists():
            raise serializers.ValidationError("Address already registered!!")
        return value



    # def validate(self, attrs):
    #     qp_wallet_address = self.context['request'].query_params.get(
    #         'address')
    #     if qp_wallet_address:
    #         try:
    #             admin_user = AdminUser.objects.get(
    #                 wallet_address=qp_wallet_address)
    #         except AdminUser.DoesNotExist:
    #             raise ValidationError(
    #                 "You don't have permission to perform this action.")
    #         return attrs
    #     else:
    #         raise serializers.ValidationError(
    #             "No admin wallet address added")


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
        


from StashClient.utils import generate_referral_code
class MasterNodeSerializer(serializers.ModelSerializer):
    node = serializers.CharField()
    master_node_id = serializers.CharField(required = False)

    # parent_node = ParentMasterNodeSerializer()
    class Meta:
        model = MasterNode
        fields = '__all__'
        read_only_fields = ['parent_node', 'node_id']

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
            # return attrs
            wallet_address = attrs['wallet_address'] 
            referral_code = attrs['master_node_id'] 
            referred_by = NodeSetup.objects.first().user
            referred_by = Referral.objects.create(user = referred_by)
            master_node, created = ClientUser.objects.get_or_create(wallet_address=wallet_address, referred_by = referred_by, referral_code = referral_code, user_type = 'MasterNode')
            return attrs
        else:
            raise serializers.ValidationError(
                "No admin wallet address added")
    # def get_master_node_id(self, obj):
    #     return obj.master_node_id
    
    def create(self, validated_data):
        master_node_id = validated_data.get('master_node_id', generate_referral_code())
        validated_data['master_node_id'] = master_node_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'master_node_id' not in validated_data:
            master_node_id = validated_data.get('master_node_id', generate_referral_code())

            validated_data['master_node_id'] = master_node_id
        return super().update(instance, validated_data)


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
    
    # master_node = MasterNodeSerializer()
    # node_manager = NodeManagerSerializer()
    # node_partner = NodePartnerSerializer()

    class Meta:
        model = NodeSetup
        fields = '__all__'
        # read_only_fields = []

    # def create(self, validated_data):
    #     validated_data['node_id'] = validated_data['user'].referral_code
    #     return super().create(validated_data)

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

    


    # def create(self, validated_data):
    #     # transaction_id = generate_trx_id()
    #     user = validated_data.pop('user')
    #     try:
    #         sender = AdminUser.objects.get(wallet_address=user)
    #     except AdminUser.DoesNotExist :
    #         raise serializers.ValidationError("Invalid sender address")

    #     master_node = validated_data.pop('master_node')
    #     node_manager = validated_data.pop('node_manager')
    #     node_partner = validated_data.pop('node_partner')
    #     billing_address_data = validated_data.pop('trx_billing_address')
        
    #     transaction = NodeSetup.objects.create(sender = sender,**validated_data)
        
    #     NodePartner.objects.create(transaction=transaction, **node_partner)
    #     MasterNodeSerializer.objects.create(transaction=transaction, **billing_address_data)
    #     return transaction
    

    # def update(self, instance, validated_data):
    #     sender_address = validated_data.pop('sender')
    #     try:
    #         sender = ClientUser.objects.get(wallet_address=sender_address)
    #     except ClientUser.DoesNotExist :
    #         raise serializers.ValidationError("Invalid sender address")

    #     card_data = validated_data.pop('trx_card')
    #     billing_address_data = validated_data.pop('trx_billing_address')
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
    #     card_detail, created = CardDetail.objects.update_or_create(
    #         transaction=instance, defaults=card_data
    #     )
    #     billing_address, created = TrxBillingAddress.objects.update_or_create(
    #         transaction=instance, defaults=billing_address_data
    #     )
    #     return instance
    
    # def get_trx_fee(self, validated_data):
    #     print("gettting trx feeee")
    #     purchase_fee, created = PurchaseFee.objects.get_or_create(pk = 1)
    #     print("validated dataa",validated_data)
    #     # amount = validated_data.get('amount')
    #     return validated_data.amount * (purchase_fee.fee_percentage /100)


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

