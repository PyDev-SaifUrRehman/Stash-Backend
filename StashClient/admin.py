from django.contrib import admin
from .models import ClientUser, Referral, Transaction

admin.site.register(ClientUser)
admin.site.register(Referral)
admin.site.register(Transaction)