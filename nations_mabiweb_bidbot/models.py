from django.db import models
from django.contrib.auth.models import User

class MaBiWebUsername(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=200)
    def __str__(self):
        return f'{self.username}'

class Match(models.Model):
    match_id = models.IntegerField(default=0, primary_key=True)
    def __str__(self):
        return f'MaBiWeb match {self.match_id}'

class Player(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    def __str__(self):
        return f'{self.name} (in {self.match})'

class Nation(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    def __str__(self):
        return f'{self.name} (in {self.match})'

class Bid(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    nation = models.ForeignKey(Nation, on_delete=models.CASCADE)
    twice_bid_value = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    def __str__(self):
        return f'{self.twice_bid_value/2.0:.1f} (for {self.nation.name} by {self.player.name} in {self.match})'
