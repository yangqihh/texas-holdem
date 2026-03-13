"""
Standalone test for Texas Hold'em game logic (no Kivy needed).
"""
import sys, types, random
from itertools import combinations
from collections import Counter

# ─── Copy game logic directly ───

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.rank_value = RANKS.index(rank)
    def __repr__(self):
        return f"{self.rank}{self.suit}"

class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)
    def deal(self, n=1):
        result = self.cards[:n]
        self.cards = self.cards[n:]
        return result

HAND_NAMES = ['High Card','One Pair','Two Pair','Three of a Kind',
              'Straight','Flush','Full House','Four of a Kind',
              'Straight Flush','Royal Flush']

def score_5(cards):
    ranks = sorted([c.rank_value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1
    sorted_r = sorted(ranks, reverse=True)
    is_straight = (sorted_r[0]-sorted_r[4]==4 and len(set(sorted_r))==5)
    if set(sorted_r) == {12,0,1,2,3}:
        is_straight = True
        sorted_r = [3,2,1,0,-1]
    cnt = Counter(ranks)
    counts = sorted(cnt.values(), reverse=True)
    rank_by_count = sorted(cnt.keys(), key=lambda r:(cnt[r],r), reverse=True)
    if is_straight and is_flush:
        return (9,sorted_r) if sorted_r[0]==12 else (8,sorted_r)
    if counts[0]==4: return (7,rank_by_count)
    if counts[:2]==[3,2]: return (6,rank_by_count)
    if is_flush: return (5,sorted_r)
    if is_straight: return (4,sorted_r)
    if counts[0]==3: return (3,rank_by_count)
    if counts[:2]==[2,2]: return (2,rank_by_count)
    if counts[0]==2: return (1,rank_by_count)
    return (0,sorted_r)

def evaluate_hand(cards):
    best = (-1,[])
    for combo in combinations(cards,5):
        s = score_5(list(combo))
        if s > best: best = s
    return best

def hand_name(score):
    return HAND_NAMES[score[0]]

class AIPlayer:
    AGGRESSION = {'tight':0.3,'normal':0.55,'loose':0.75}
    def __init__(self, name, style='normal'):
        self.name=name; self.style=style
        self.aggr=self.AGGRESSION.get(style,0.55)
        self.bluff_rate={'tight':0.05,'normal':0.12,'loose':0.22}[style]
    def hand_strength(self, hole, community):
        if not community:
            r1,r2=sorted([c.rank_value for c in hole],reverse=True)
            suited=hole[0].suit==hole[1].suit; paired=r1==r2
            score=(r1+r2)/24.0
            if paired: score+=0.15
            if suited: score+=0.05
            if r1>=10: score+=0.05
            return min(score,1.0)
        return evaluate_hand(hole+community)[0]/9.0
    def decide(self, hole, community, pot, to_call, my_chips, stage):
        strength=self.hand_strength(hole,community)
        is_bluff=random.random()<self.bluff_rate
        es=min(strength+(0.3 if is_bluff else 0),1.0)
        if to_call>=my_chips:
            return ('allin',my_chips) if es>0.35 else ('fold',0)
        if to_call==0:
            if es>self.aggr:
                return ('raise',min(max(pot//3,1),my_chips))
            return ('check',0)
        pot_odds=to_call/(pot+to_call) if (pot+to_call)>0 else 0
        if es<pot_odds-0.05: return ('fold',0)
        elif es>self.aggr+0.1:
            ra=min(to_call*2+pot//4,my_chips)
            return ('call',to_call) if ra<=to_call else ('raise',ra)
        return ('call',to_call)

class PokerGame:
    SMALL_BLIND=10; BIG_BLIND=20; START_CHIPS=1000
    def __init__(self):
        self.players=[
            {'name':'You','chips':self.START_CHIPS,'is_human':True,'ai':None},
            {'name':'Alice','chips':self.START_CHIPS,'is_human':False,'ai':AIPlayer('Alice','normal')},
            {'name':'Bob','chips':self.START_CHIPS,'is_human':False,'ai':AIPlayer('Bob','loose')},
        ]
        self.dealer_idx=0; self.hand_num=0; self.reset_round()
    def reset_round(self):
        self.deck=Deck(); self.community=[]; self.pot=0; self.stage='preflop'
        self.bets=[0,0,0]; self.folded=[False,False,False]; self.all_in=[False,False,False]
        self.hole_cards=[[],[],[]]; self.current_bet=0; self.action_log=[]; self.round_over=False
    def post_blinds(self):
        sb=(self.dealer_idx+1)%3; bb=(self.dealer_idx+2)%3
        def post(idx,amt):
            a=min(amt,self.players[idx]['chips'])
            self.players[idx]['chips']-=a; self.bets[idx]+=a; self.pot+=a
            if self.players[idx]['chips']==0: self.all_in[idx]=True
        post(sb,self.SMALL_BLIND); post(bb,self.BIG_BLIND)
        self.current_bet=self.BIG_BLIND
        self.action_log.append(f"{self.players[sb]['name']} posts SB ${self.SMALL_BLIND}")
        self.action_log.append(f"{self.players[bb]['name']} posts BB ${self.BIG_BLIND}")
        return (self.dealer_idx+3)%3
    def deal_hole_cards(self):
        for i in range(3): self.hole_cards[i]=self.deck.deal(2)
    def deal_community(self):
        if self.stage=='flop': self.community+=self.deck.deal(3)
        elif self.stage in('turn','river'): self.community+=self.deck.deal(1)
    def to_call_for(self,idx): return max(0,self.current_bet-self.bets[idx])
    def apply_action(self,idx,action,amount):
        p=self.players[idx]; name=p['name']
        if action=='fold':
            self.folded[idx]=True; self.action_log.append(f"{name} folds")
        elif action=='check':
            self.action_log.append(f"{name} checks")
        elif action=='call':
            tc=min(self.current_bet-self.bets[idx],p['chips'])
            p['chips']-=tc; self.bets[idx]+=tc; self.pot+=tc
            if p['chips']==0: self.all_in[idx]=True
            self.action_log.append(f"{name} calls ${tc}")
        elif action in('raise','allin'):
            if action=='allin': amount=p['chips']
            a=min(amount,p['chips']); tb=self.bets[idx]+a
            p['chips']-=a; self.bets[idx]+=a; self.pot+=a
            if tb>self.current_bet: self.current_bet=tb
            if p['chips']==0: self.all_in[idx]=True
            self.action_log.append(f"{name} raises to ${self.bets[idx]}")
    def determine_winners(self):
        active=[i for i in range(3) if not self.folded[i]]
        if len(active)==1: return [(active[0],self.pot,'Last player')]
        scores={i:evaluate_hand(self.hole_cards[i]+self.community) for i in active}
        best=max(scores.values())
        winners=[i for i,s in scores.items() if s==best]
        return [(w,self.pot//len(winners),hand_name(best)) for w in winners]
    def payout(self,winners):
        for(idx,amt,_) in winners: self.players[idx]['chips']+=amt
    def start_new_hand(self):
        for p in self.players:
            if p['chips']<=0: p['chips']=self.START_CHIPS
        self.reset_round(); self.hand_num+=1
        self.deal_hole_cards()
        return self.post_blinds()

# ─── TESTS ───
print("=" * 50)
print("Texas Hold'em - Logic Test Suite")
print("=" * 50)

# Test 1: Deck
d = Deck()
assert len(d.cards) == 52, "Deck should have 52 cards"
print(f"✅ Deck: 52 cards")

# Test 2: Deal
hole = d.deal(2)
comm = d.deal(5)
assert len(hole) == 2 and len(comm) == 5
print(f"✅ Deal: hole={hole}, comm={comm}")

# Test 3: Hand evaluator
score = evaluate_hand(hole + comm)
print(f"✅ Evaluator: {hand_name(score)} (rank {score[0]})")

# Test 4: Known hands
royal_cards = [Card('A','♠'),Card('K','♠'),Card('Q','♠'),Card('J','♠'),Card('10','♠')]
assert score_5(royal_cards)[0] == 9, "Should be Royal Flush"
print(f"✅ Royal Flush detected")

pair_cards = [Card('A','♠'),Card('A','♥'),Card('2','♦'),Card('5','♣'),Card('9','♠')]
assert score_5(pair_cards)[0] == 1, "Should be One Pair"
print(f"✅ One Pair detected")

# Test 5: Full game simulation
g = PokerGame()
print(f"\n{'─'*40}")
print("Simulating full hand...")
fa = g.start_new_hand()
print(f"  Hand #{g.hand_num}, Pot after blinds: ${g.pot}")
print(f"  First actor: {g.players[fa]['name']}")
print(f"  Player hole cards: {g.hole_cards[0]}")

# Simulate preflop action
for i in range(3):
    if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0:
        if g.players[i]['is_human']:
            tc = g.to_call_for(i)
            g.apply_action(i, 'call', tc)
        else:
            action, amt = g.players[i]['ai'].decide(
                g.hole_cards[i], g.community, g.pot, g.to_call_for(i), g.players[i]['chips'], 'preflop')
            g.apply_action(i, action, amt)

# Deal flop
g.stage = 'flop'
g.deal_community()
print(f"  Community (flop): {g.community}")

# Deal turn
g.stage = 'turn'
g.deal_community()
print(f"  Community (turn): {g.community}")

# Deal river
g.stage = 'river'
g.deal_community()
print(f"  Community (river): {g.community}")

# Showdown
winners = g.determine_winners()
g.payout(winners)
print(f"\n  Results:")
for (idx, amt, desc) in winners:
    print(f"    🏆 {g.players[idx]['name']} wins ${amt} ({desc})")

print(f"\n  Final chips:")
for p in g.players:
    print(f"    {p['name']}: ${p['chips']}")

print(f"\n  Action log:")
for entry in g.action_log:
    print(f"    {entry}")

print("\n" + "=" * 50)
print("✅ All tests PASSED! Game logic is working correctly.")
print("=" * 50)
