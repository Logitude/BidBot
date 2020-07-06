from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

import re
import secrets
import base64
import urllib.request

from .models import MaBiWebUsername, Match, Player, Nation, Bid
from .forms import BidForm, RankForm, MatchForm, MaBiWebUsernameForm, ordinals

def home(request):
    return render(request, 'nations_mabiweb_bidbot/home.html')

@login_required
def add_mabiweb_username(request):
    if request.method == 'POST':
        form = MaBiWebUsernameForm(request.POST)
        if form.is_valid():
            request.session['username'] = form.cleaned_data.get('username')
            request.session['mabiweb_uid'] = form.cleaned_data.get('mabiweb_uid')
            return redirect('nations_mabiweb_bidbot:verify_mabiweb_username')
    else:
        form = MaBiWebUsernameForm()
    return render(request, 'nations_mabiweb_bidbot/add_mabiweb_username.html', {'form': form})

@login_required
def verify_mabiweb_username(request):
    if request.method == 'POST':
        username = request.session.pop('username', None)
        mabiweb_uid = request.session.pop('mabiweb_uid', None)
        verification_code = request.session.pop('verification_code', None)
        if username is None or mabiweb_uid is None or verification_code is None:
            return redirect('nations_mabiweb_bidbot:home')
        mabiweb_profile_url = f'http://www.mabiweb.com/modules.php?name=Forums&file=profile&mode=viewprofile&u={mabiweb_uid}'
        try:
            mabiweb_profile_page = urllib.request.urlopen(mabiweb_profile_url).read().decode('iso-8859-1')
        except:
            mabiweb_profile_page = ''
        if f'>Viewing profile :: {username}</th>' in mabiweb_profile_page:
            m = re.search(f'{verification_code}', mabiweb_profile_page)
        else:
            m = None
        if m is None:
            request.session['username'] = username
            request.session['mabiweb_uid'] = mabiweb_uid
            return redirect('nations_mabiweb_bidbot:verify_mabiweb_username_failure')
        MaBiWebUsername(user=request.user, username=username).save()
        return redirect('profile')
    else:
        username = request.session.pop('username', None)
        mabiweb_uid = request.session.pop('mabiweb_uid', None)
        if username is None or mabiweb_uid is None:
            return redirect('nations_mabiweb_bidbot:home')
        verification_code = secrets.token_hex(8)
        request.session['username'] = username
        request.session['mabiweb_uid'] = mabiweb_uid
        request.session['verification_code'] = verification_code
        return render(request, 'nations_mabiweb_bidbot/verify_mabiweb_username.html', {'username': username, 'verification_code': verification_code})

@login_required
def verify_mabiweb_username_failure(request):
    username = request.session.pop('username', None)
    mabiweb_uid = request.session.pop('mabiweb_uid', None)
    if username is None or mabiweb_uid is None:
        return redirect('nations_mabiweb_bidbot:home')
    return render(request, 'nations_mabiweb_bidbot/verify_mabiweb_username_failure.html', {'username': username, 'mabiweb_uid': mabiweb_uid})

@login_required
def remove_mabiweb_username(request):
    if request.method == 'GET':
        username = request.GET.get('username')
        username = request.user.mabiwebusername_set.get(username=username)
        return render(request, 'nations_mabiweb_bidbot/remove_mabiweb_username.html', {'username': username})
    elif request.method == 'POST':
        username = request.POST.get('username')
        username = request.user.mabiwebusername_set.get(username=username)
        username.delete()
        return redirect('profile')
    return redirect('home')

@login_required
def initiate(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match_id = form.cleaned_data.get('match_id')
            if not Match.objects.filter(match_id=match_id).exists():
                match_url = f'http://www.mabiweb.com/modules.php?name=GM_Nations&g_id={match_id}&op=view_game_reset'
                try:
                    match_page = urllib.request.urlopen(match_url).read().decode('iso-8859-1')
                    players = re.findall(r'<IMG src=modules/GM_Nations/images/Disc_\S*\.png\s+style=\'[^\']*\'>(?:<B>)?\b([^\s&<]+)\b', match_page)
                    players = sorted(set(players), key=players.index)
                    nations = re.search(r'Player Boards available:\s*([^<]+)', match_page).group(1).split()
                    (match, new_match) = Match.objects.get_or_create(match_id=match_id)
                    if new_match:
                        match.save()
                        for player_name in players:
                            Player(match=match, name=player_name).save()
                        for nation_name in nations:
                            Nation(match=match, name=nation_name).save()
                except:
                    request.session['match_id'] = match_id
                    return redirect('nations_mabiweb_bidbot:initiate_failure')
            return redirect('nations_mabiweb_bidbot:results', pk=match_id)
    else:
        form = MatchForm()
    return render(request, 'nations_mabiweb_bidbot/initiate.html', {'form': form})

@login_required
def initiate_failure(request):
    match_id = request.session.pop('match_id', None)
    if match_id is None:
        return redirect('nations_mabiweb_bidbot:home')
    return render(request, 'nations_mabiweb_bidbot/initiate_failure.html', {'match_id': match_id})

@login_required
def bid(request, pk):
    match = get_object_or_404(Match, match_id=pk)
    player_names = [player.name for player in match.player_set.all()]
    bid_players = {bid.player.name for bid in match.bid_set.all()}
    usernames = {username.username for username in request.user.mabiwebusername_set.all()}
    possible_usernames = (set(player_names) & usernames) - bid_players
    if not possible_usernames:
        return redirect('nations_mabiweb_bidbot:results', pk=pk)
    possible_usernames = sorted(possible_usernames, key=player_names.index)
    if request.method == 'POST':
        form = BidForm(match, possible_usernames, request.POST)
        if form.is_valid():
            if len(possible_usernames) > 1:
                player = form.cleaned_data.get('player')
            else:
                player = possible_usernames[0]
            bid_values = {nation.name: form.cleaned_data.get(f'bid_for_{nation.name}') for nation in match.nation_set.all()}
            twice_bid_values = {}
            for (nation, bid_value) in bid_values.items():
                m = re.match(r'^(\d+)((?:\.[05])?)$', bid_value)
                twice_bid_values[nation] = (int(m.group(1)) * 2) + (1 if m.group(2) == '.5' else 0)
            request.session['match_id'] = match.match_id
            request.session['player'] = player
            request.session['twice_bid_values'] = twice_bid_values
            if len(twice_bid_values) != len(set(twice_bid_values.values())):
                return redirect('nations_mabiweb_bidbot:rank', pk=pk)
            return redirect('nations_mabiweb_bidbot:confirm', pk=pk)
    else:
        form = BidForm(match, possible_usernames)
    if len(possible_usernames) == 1:
        player = possible_usernames[0]
    else:
        player = None
    return render(request, 'nations_mabiweb_bidbot/bid.html', {'match': match, 'player': player, 'form': form})

def twice_bid_value_to_bid_string(twice_bid_value):
    return f'{twice_bid_value//2}' + ('' if twice_bid_value % 2 == 0 else '.5')

@login_required
def rank(request, pk):
    match_id = request.session.get('match_id', None)
    player = request.session.get('player', None)
    twice_bid_values = request.session.get('twice_bid_values', None)
    if match_id is None or player is None or twice_bid_values is None or match_id != pk:
        return redirect('nations_mabiweb_bidbot:bid', pk=pk)
    match = get_object_or_404(Match, match_id=pk)
    descending_bid_values = sorted(set(twice_bid_values.values()), reverse=True)
    if request.method == 'POST':
        form = RankForm(twice_bid_values, request.POST)
        if form.is_valid():
            rankings = {}
            rank = 0
            for bid_value in descending_bid_values:
                nations_with_bid_value = [nation for (nation, bid_for_nation) in twice_bid_values.items() if bid_for_nation == bid_value]
                if len(nations_with_bid_value) == 1:
                    rankings[nations_with_bid_value[0]] = rank
                else:
                    for nation in nations_with_bid_value:
                        rankings[nation] = rank + ordinals.index(form.cleaned_data.get(nation)) - 1
                rank += len(nations_with_bid_value)
            request.session['rankings'] = rankings
            return redirect('nations_mabiweb_bidbot:confirm', pk=pk)
    else:
        form = RankForm(twice_bid_values)
    nation_sets = []
    for bid_value in descending_bid_values:
        nations_with_bid_value = [nation for (nation, bid_for_nation) in twice_bid_values.items() if bid_for_nation == bid_value]
        if len(nations_with_bid_value) != 1:
            nation_sets.append((nations_with_bid_value, twice_bid_value_to_bid_string(bid_value)))
    return render(request, 'nations_mabiweb_bidbot/rank.html', {'match': match, 'player': player, 'nation_sets': nation_sets, 'form': form})

@login_required
def confirm(request, pk):
    if request.method == 'POST':
        match_id = request.session.pop('match_id', None)
        player = request.session.pop('player', None)
        twice_bid_values = request.session.pop('twice_bid_values', None)
    else:
        match_id = request.session.get('match_id', None)
        player = request.session.get('player', None)
        twice_bid_values = request.session.get('twice_bid_values', None)
    if match_id is None or player is None or twice_bid_values is None or match_id != pk:
        return redirect('nations_mabiweb_bidbot:bid', pk=pk)
    match = get_object_or_404(Match, match_id=pk)
    player = match.player_set.get(name=player)
    rankings = request.session.pop('rankings', None)
    if rankings is None:
        def bid_sort_key(nation):
            return twice_bid_values[nation]
        sorted_nations = sorted(twice_bid_values.keys(), key=bid_sort_key, reverse=True)
        rankings = {nation: rank for (rank, nation) in enumerate(sorted_nations)}
    if request.method == 'POST':
        for (nation, twice_bid_value) in twice_bid_values.items():
            bid = Bid()
            bid.match = match
            bid.player = player
            bid.nation = match.nation_set.get(name=nation)
            bid.twice_bid_value = twice_bid_value
            bid.rank = rankings[nation]
            bid.save()
        return redirect('nations_mabiweb_bidbot:results', pk=pk)
    def nation_sort_key(nation_bid):
        (nation, bid) = nation_bid
        return rankings[nation]
    bid_values = {nation: twice_bid_value_to_bid_string(twice_bid_value) for (nation, twice_bid_value) in twice_bid_values.items()}
    bid_values = sorted(bid_values.items(), key=nation_sort_key)
    bid_values = [(nation, f'{ordinals[rankings[nation]+1].capitalize()} choice with a bid of {bid}') for (nation, bid) in bid_values]
    return render(request, 'nations_mabiweb_bidbot/confirm.html', {'match': match, 'player': player, 'bid_values': bid_values})

def make_bid_string(player, bids, preferences):
    bid_strings = []
    descending_bid_values = sorted(set(bids.values()), reverse=True)
    for bid_value in descending_bid_values:
        bid_string = twice_bid_value_to_bid_string(bid_value) + ' for '
        nations_with_bid_value = [nation for (nation, bid_for_nation) in bids.items() if bid_for_nation == bid_value]
        if len(nations_with_bid_value) == 1:
            bid_string += f'{nations_with_bid_value[0]}'
        else:
            nation_preferences = list(preferences[bid_value])
            if len(nations_with_bid_value) == 2:
                (nation1, nation2) = nation_preferences
                bid_string += f'{nation1} and {nation2}'
            else:
                bid_string += ', '.join(nation_preferences[:-1]) + f', and {nation_preferences[-1]}'
            bid_string += ' (preferring '
            bid_string += ' over '.join(nation_preferences)
            bid_string += ')'
        bid_strings.append(bid_string)
    return f'{player} bid ' + '; '.join(bid_strings)

# assign_nations
#
# players is the list of players in the match in initial player order.
# nations is the list of nations in the match.
# bids contains (twice) the values each player bid for each nation.
#     - The values are doubled to make them integers since players can bid half-points.
# preferences contains the order each player prefers each nation for which they bid the same value.
def assign_nations(players, nations, bids, preferences):
    remaining_players = list(players)
    remaining_nations = list(nations)
    nation_assignments = []
    # Assign nations until they have all been assigned to the players:
    while remaining_nations:
        # Find the highest bid by the remaining players for the remaining nations:
        highest_bid = max(bids[player][nation] for player in remaining_players for nation in remaining_nations)
        # List all of the players who made that highest bid:
        players_with_highest_bid = [player for player in remaining_players if highest_bid in [bids[player][nation] for nation in remaining_nations]]
        # Of those players, the one last in turn order wins ties:
        player = players_with_highest_bid[-1]
        # List all of the nations for which that player made that highest bid:
        player_highest_bid_nations = [nation for nation in remaining_nations if bids[player][nation] == highest_bid]
        # Of those nations, find the one most preferred that player:
        nation = sorted(player_highest_bid_nations, key=preferences[player][highest_bid].index)[0]
        # Construct the string announcing the assignment:
        s_if_plural_points = 's' if highest_bid != 2 else ''
        bid_string = twice_bid_value_to_bid_string(highest_bid)
        nation_assignments.append(f'{player} gets {nation} for {bid_string} point{s_if_plural_points}')
        # Remove that player and that nation from further consideration:
        remaining_players.remove(player)
        remaining_nations.remove(nation)
    return nation_assignments

def results(request, pk):
    match = get_object_or_404(Match, match_id=pk)
    player_order = [player.name for player in match.player_set.all()]
    nations = [nation.name for nation in match.nation_set.all()]
    player_names = set(player_order)
    bid_players = {bid.player.name for bid in match.bid_set.all()}
    may_bid = False
    bid_strings = None
    nation_assignments = None
    if bid_players == player_names:
        bid_strings = []
        twice_bid_values = {}
        preferences = {}
        for player_name in player_order:
            player = match.player_set.get(name=player_name)
            player_bids = {}
            rankings = {}
            for nation in match.nation_set.all():
                bid = match.bid_set.get(player=player, nation=nation)
                player_bids[nation.name] = bid.twice_bid_value
                rankings[nation.name] = bid.rank
            twice_bid_values[player_name] = player_bids
            player_preferences = {}
            def rank_sort_key(nation):
                return rankings[nation]
            for bid_value in set(player_bids.values()):
                nations_with_bid_value = [nation for (nation, bid_for_nation) in player_bids.items() if bid_for_nation == bid_value]
                player_preferences[bid_value] = sorted(nations_with_bid_value, key=rank_sort_key)
            preferences[player_name] = player_preferences
            bid_strings.append(make_bid_string(player_name, player_bids, player_preferences))
        nation_assignments = assign_nations(player_order, nations, twice_bid_values, preferences)
    elif request.user.is_authenticated:
        usernames = {username.username for username in request.user.mabiwebusername_set.all()}
        possible_usernames = (player_names & usernames) - bid_players
        may_bid = bool(possible_usernames)
    context = {
        'match': match,
        'player_bids': bid_strings,
        'nation_assignments': nation_assignments,
        'bid_players': bid_players,
        'may_bid': may_bid
    }
    return render(request, 'nations_mabiweb_bidbot/results.html', context)
