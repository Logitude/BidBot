from django.contrib import admin

from .models import MaBiWebUsername, Match, Player, Nation, Bid

admin.site.register(MaBiWebUsername)
admin.site.register(Match)
admin.site.register(Player)
admin.site.register(Nation)
admin.site.register(Bid)
