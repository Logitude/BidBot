from django import forms
from django.core import validators

class BidForm(forms.Form):
    def __init__(self, match, possible_usernames, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(possible_usernames) > 1:
            self.fields['player'] = forms.ChoiceField(label='Bid as', choices=zip(possible_usernames, possible_usernames))
        for nation in match.nation_set.all():
            self.fields[f'bid_for_{nation.name}'] = forms.CharField(label=nation.name, max_length=5, validators=[validators.RegexValidator(r'^(\d+)((?:\.[05])?)$')])

ordinals = ('zeroth', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth')

class RankForm(forms.Form):
    def __init__(self, bids, *args, **kwargs):
        super().__init__(*args, **kwargs)
        player_bid_values = sorted(set(bids.values()), reverse=True)
        self.nation_sets = []
        for bid_value in player_bid_values:
            nations_with_bid_value = [nation for (nation, bid_for_nation) in bids.items() if bid_for_nation == bid_value]
            if len(nations_with_bid_value) == 1:
                continue
            self.nation_sets.append(nations_with_bid_value)
            ranks = ordinals[1:len(nations_with_bid_value)+1]
            choice_list = [('', '')] + [(rank, rank.capitalize()) for rank in ranks]
            for nation in nations_with_bid_value:
                self.fields[nation] = forms.ChoiceField(label=nation, choices=choice_list)

    def clean(self):
        cleaned_data = super().clean()
        for nation_set in self.nation_sets:
            nation_ranks = []
            for nation in nation_set:
                nation_ranks.append(cleaned_data.get(nation))
            if len(nation_ranks) != len(set(nation_ranks)):
                raise forms.ValidationError('Non-unique rankings', code='not_unique')
        return cleaned_data

class MatchForm(forms.Form):
    match_id = forms.CharField(label='MaBiWeb match ID', validators=[validators.RegexValidator(r'^\d+$')])

class MaBiWebUsernameForm(forms.Form):
    help_text = 'Must exactly match your MaBiWeb username. Case sensitive.'
    username = forms.CharField(label='MaBiWeb username', help_text=help_text)
    mabiweb_uid = forms.CharField(label='MaBiWeb user ID', validators=[validators.RegexValidator(r'^\d+$')])
