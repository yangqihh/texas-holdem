# -*- coding: utf-8 -*-
"""
Texas Hold'em Poker - Single Player vs AI
Player vs 2 AI opponents
"""

import random
from itertools import combinations
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.relativelayout import RelativeLayout
from kivy.animation import Animation
from kivy.uix.image import Image

# ──────────────────────────────────────────────
# COLORS
# ──────────────────────────────────────────────
C_BG         = get_color_from_hex('#0d6b3a')   # felt green
C_BG_DARK    = get_color_from_hex('#084d29')
C_GOLD       = get_color_from_hex('#f0c040')
C_WHITE      = get_color_from_hex('#ffffff')
C_BLACK      = get_color_from_hex('#111111')
C_RED        = get_color_from_hex('#e83030')
C_BLUE       = get_color_from_hex('#3060e8')
C_GRAY       = get_color_from_hex('#888888')
C_LIGHT_GRAY = get_color_from_hex('#cccccc')
C_CARD_BG    = get_color_from_hex('#fffdf0')
C_CARD_BACK  = get_color_from_hex('#1a3a7a')
C_BTN_GREEN  = get_color_from_hex('#27ae60')
C_BTN_RED    = get_color_from_hex('#c0392b')
C_BTN_BLUE   = get_color_from_hex('#2980b9')
C_BTN_ORANGE = get_color_from_hex('#e67e22')
C_BTN_GRAY   = get_color_from_hex('#555555')
C_HIGHLIGHT  = get_color_from_hex('#f1c40f')

# ──────────────────────────────────────────────
# CARD ENGINE
# ──────────────────────────────────────────────
SUITS   = ['♠', '♥', '♦', '♣']
RANKS   = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
SUIT_COLORS = {'♠': C_BLACK, '♥': C_RED, '♦': C_RED, '♣': C_BLACK}

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.rank_value = RANKS.index(rank)

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit


class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for s in SUITS for r in RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, n=1):
        result = self.cards[:n]
        self.cards = self.cards[n:]
        return result


# ──────────────────────────────────────────────
# HAND EVALUATOR
# ──────────────────────────────────────────────
HAND_NAMES = [
    'High Card', 'One Pair', 'Two Pair', 'Three of a Kind',
    'Straight', 'Flush', 'Full House', 'Four of a Kind',
    'Straight Flush', 'Royal Flush'
]

def evaluate_hand(cards):
    """Evaluate best 5-card hand from 5-7 cards. Returns (rank, tiebreakers)."""
    best = (-1, [])
    for combo in combinations(cards, 5):
        score = score_5(list(combo))
        if score > best:
            best = score
    return best

def score_5(cards):
    ranks = sorted([c.rank_value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    is_flush  = len(set(suits)) == 1
    sorted_r  = sorted(ranks, reverse=True)
    is_straight = (sorted_r[0] - sorted_r[4] == 4 and len(set(sorted_r)) == 5)
    # Wheel straight A-2-3-4-5
    if set(sorted_r) == {12, 0, 1, 2, 3}:
        is_straight = True
        sorted_r = [3, 2, 1, 0, -1]  # 5-high straight

    from collections import Counter
    cnt = Counter(ranks)
    counts = sorted(cnt.values(), reverse=True)
    rank_by_count = sorted(cnt.keys(), key=lambda r: (cnt[r], r), reverse=True)

    if is_straight and is_flush:
        if sorted_r[0] == 12:
            return (9, sorted_r)   # Royal Flush
        return (8, sorted_r)       # Straight Flush
    if counts[0] == 4:
        return (7, rank_by_count)  # Four of a Kind
    if counts[:2] == [3, 2]:
        return (6, rank_by_count)  # Full House
    if is_flush:
        return (5, sorted_r)       # Flush
    if is_straight:
        return (4, sorted_r)       # Straight
    if counts[0] == 3:
        return (3, rank_by_count)  # Three of a Kind
    if counts[:2] == [2, 2]:
        return (2, rank_by_count)  # Two Pair
    if counts[0] == 2:
        return (1, rank_by_count)  # One Pair
    return (0, sorted_r)           # High Card

def hand_name(score):
    return HAND_NAMES[score[0]]


# ──────────────────────────────────────────────
# AI STRATEGY
# ──────────────────────────────────────────────
class AIPlayer:
    """AI with basic poker strategy based on hand strength and position."""

    AGGRESSION = {'tight': 0.3, 'normal': 0.55, 'loose': 0.75}

    def __init__(self, name, style='normal'):
        self.name   = name
        self.style  = style
        self.aggr   = self.AGGRESSION.get(style, 0.55)
        self.bluff_rate = {'tight': 0.05, 'normal': 0.12, 'loose': 0.22}[style]

    def hand_strength(self, hole, community):
        """0.0-1.0 hand strength estimate."""
        if not community:
            # Pre-flop: use hole card ranks
            r1, r2 = sorted([c.rank_value for c in hole], reverse=True)
            suited = hole[0].suit == hole[1].suit
            paired = r1 == r2
            score = (r1 + r2) / 24.0
            if paired: score += 0.15
            if suited: score += 0.05
            if r1 >= 10: score += 0.05
            return min(score, 1.0)
        else:
            score, _ = evaluate_hand(hole + community)
            return score / 9.0

    def decide(self, hole, community, pot, to_call, my_chips, stage):
        """Return (action, amount). action: 'fold','check','call','raise','allin'"""
        strength = self.hand_strength(hole, community)
        is_bluff  = random.random() < self.bluff_rate

        effective_strength = strength + (0.3 if is_bluff else 0)
        effective_strength = min(effective_strength, 1.0)

        # Can't afford to call
        if to_call >= my_chips:
            if effective_strength > 0.35:
                return ('allin', my_chips)
            return ('fold', 0)

        # No cost to continue
        if to_call == 0:
            if effective_strength > self.aggr:
                bet = max(pot // 3, 1)
                bet = min(bet, my_chips)
                return ('raise', bet)
            return ('check', 0)

        # Must call or fold/raise
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0

        if effective_strength < pot_odds - 0.05:
            return ('fold', 0)
        elif effective_strength > self.aggr + 0.1:
            raise_amt = min(to_call * 2 + pot // 4, my_chips)
            if raise_amt <= to_call:
                return ('call', to_call)
            return ('raise', raise_amt)
        else:
            return ('call', to_call)


# ──────────────────────────────────────────────
# GAME LOGIC
# ──────────────────────────────────────────────
STAGES = ['preflop', 'flop', 'turn', 'river', 'showdown']

class PokerGame:
    SMALL_BLIND = 10
    BIG_BLIND   = 20
    START_CHIPS = 1000

    def __init__(self):
        self.players = [
            {'name': 'You',    'chips': self.START_CHIPS, 'is_human': True,  'ai': None},
            {'name': 'Alice',  'chips': self.START_CHIPS, 'is_human': False, 'ai': AIPlayer('Alice', 'normal')},
            {'name': 'Bob',    'chips': self.START_CHIPS, 'is_human': False, 'ai': AIPlayer('Bob',   'loose')},
        ]
        self.dealer_idx = 0
        self.hand_num   = 0
        self.reset_round()

    def reset_round(self):
        self.deck        = Deck()
        self.community   = []
        self.pot         = 0
        self.stage       = 'preflop'
        self.bets        = [0, 0, 0]
        self.folded      = [False, False, False]
        self.all_in      = [False, False, False]
        self.hole_cards  = [[], [], []]
        self.current_bet = 0
        self.action_log  = []
        self.round_over  = False
        self.winner_info = None
        self.acting_idx  = -1

    def active_players(self):
        return [i for i in range(3) if not self.folded[i] and self.players[i]['chips'] > 0 or not self.folded[i] and self.all_in[i]]

    def players_who_can_act(self):
        return [i for i in range(3) if not self.folded[i] and not self.all_in[i] and self.players[i]['chips'] > 0]

    def deal_hole_cards(self):
        for i in range(3):
            self.hole_cards[i] = self.deck.deal(2)

    def post_blinds(self):
        n = len(self.players)
        sb_idx = (self.dealer_idx + 1) % n
        bb_idx = (self.dealer_idx + 2) % n

        def post(idx, amount):
            amount = min(amount, self.players[idx]['chips'])
            self.players[idx]['chips'] -= amount
            self.bets[idx] += amount
            self.pot += amount
            if self.players[idx]['chips'] == 0:
                self.all_in[idx] = True

        post(sb_idx, self.SMALL_BLIND)
        post(bb_idx, self.BIG_BLIND)
        self.current_bet = self.BIG_BLIND
        self.action_log.append(f"{self.players[sb_idx]['name']} posts SB ${self.SMALL_BLIND}")
        self.action_log.append(f"{self.players[bb_idx]['name']} posts BB ${self.BIG_BLIND}")
        return (self.dealer_idx + 3) % n  # UTG acts first preflop

    def deal_community(self):
        if self.stage == 'flop':
            self.community += self.deck.deal(3)
        elif self.stage in ('turn', 'river'):
            self.community += self.deck.deal(1)

    def apply_action(self, player_idx, action, amount):
        p = self.players[player_idx]
        name = p['name']

        if action == 'fold':
            self.folded[player_idx] = True
            self.action_log.append(f"{name} folds")

        elif action == 'check':
            self.action_log.append(f"{name} checks")

        elif action == 'call':
            to_call = min(self.current_bet - self.bets[player_idx], p['chips'])
            p['chips'] -= to_call
            self.bets[player_idx] += to_call
            self.pot += to_call
            if p['chips'] == 0:
                self.all_in[player_idx] = True
                self.action_log.append(f"{name} calls ${to_call} (all-in)")
            else:
                self.action_log.append(f"{name} calls ${to_call}")

        elif action in ('raise', 'allin'):
            if action == 'allin':
                amount = p['chips']
            actual = min(amount, p['chips'])
            total_bet = self.bets[player_idx] + actual
            p['chips'] -= actual
            self.bets[player_idx] += actual
            self.pot += actual
            if total_bet > self.current_bet:
                self.current_bet = total_bet
            if p['chips'] == 0:
                self.all_in[player_idx] = True
                self.action_log.append(f"{name} raises to ${self.bets[player_idx]} (all-in)")
            else:
                self.action_log.append(f"{name} raises to ${self.bets[player_idx]}")

    def to_call_for(self, idx):
        return max(0, self.current_bet - self.bets[idx])

    def determine_winners(self):
        active = [i for i in range(3) if not self.folded[i]]
        if len(active) == 1:
            return [(active[0], self.pot, 'Last player standing')]

        scores = {}
        for i in active:
            score = evaluate_hand(self.hole_cards[i] + self.community)
            scores[i] = score

        best_score = max(scores.values())
        winners = [i for i, s in scores.items() if s == best_score]

        hand_desc = hand_name(best_score)
        per_winner = self.pot // len(winners)
        result = []
        for w in winners:
            result.append((w, per_winner, hand_desc))
        return result

    def payout(self, winners):
        for (idx, amount, desc) in winners:
            self.players[idx]['chips'] += amount

    def next_dealer(self):
        self.dealer_idx = (self.dealer_idx + 1) % 3
        self.hand_num  += 1

    def is_betting_complete(self, order):
        """Check if all active non-allin players have matched the current bet."""
        can_act = self.players_who_can_act()
        if not can_act:
            return True
        for i in can_act:
            if self.bets[i] < self.current_bet:
                return False
        return True

    def start_new_hand(self):
        # Remove broke players (replace with fresh AI for simplicity)
        for i, p in enumerate(self.players):
            if p['chips'] <= 0:
                p['chips'] = self.START_CHIPS
                self.action_log.append(f"{p['name']} rebuys for ${self.START_CHIPS}")
        self.reset_round()
        self.hand_num += 1
        self.deal_hole_cards()
        first_actor = self.post_blinds()
        return first_actor


# ──────────────────────────────────────────────
# CARD WIDGET
# ──────────────────────────────────────────────
class CardWidget(Widget):
    def __init__(self, card=None, face_down=False, **kwargs):
        super().__init__(**kwargs)
        self.card      = card
        self.face_down = face_down
        self.size_hint = (None, None)
        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_once(lambda dt: self._draw(), 0)

    def _draw(self, *args):
        self.canvas.clear()
        w, h = self.size
        x, y = self.pos
        r = max(6, w * 0.12)

        with self.canvas:
            # Shadow
            Color(0, 0, 0, 0.25)
            RoundedRectangle(pos=(x+3, y-3), size=(w, h), radius=[r])

            if self.face_down:
                Color(*C_CARD_BACK)
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
                Color(1, 1, 1, 0.15)
                margin = w * 0.12
                RoundedRectangle(pos=(x+margin, y+margin),
                                 size=(w-2*margin, h-2*margin), radius=[r*0.5])
            else:
                Color(*C_CARD_BG)
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
                Color(*C_LIGHT_GRAY, 0.6)
                Line(rounded_rectangle=(x+1, y+1, w-2, h-2, r), width=1)

                if self.card:
                    suit_c = SUIT_COLORS.get(self.card.suit, C_BLACK)
                    Color(*suit_c)

                    # Top-left rank+suit
                    from kivy.graphics import Color as KC
                    self.canvas.add(KC(*suit_c))

        # Draw text labels
        if not self.face_down and self.card:
            # Clear old labels
            self.clear_widgets()
            suit_c = SUIT_COLORS.get(self.card.suit, C_BLACK)
            hex_color = '#cc0000' if suit_c == C_RED else '#111111'
            fs_rank = max(10, int(w * 0.32))
            fs_suit = max(12, int(w * 0.38))
            fs_center = max(14, int(w * 0.45))

            # Top-left
            tl = Label(
                text=f"[color={hex_color}]{self.card.rank}[/color]",
                markup=True, font_size=fs_rank,
                size_hint=(None, None), size=(w*0.5, h*0.25),
                pos=(x + 2, y + h - h*0.28),
                halign='left', valign='top'
            )
            # Suit top
            ts = Label(
                text=f"[color={hex_color}]{self.card.suit}[/color]",
                markup=True, font_size=fs_suit,
                size_hint=(None, None), size=(w*0.5, h*0.25),
                pos=(x + 2, y + h - h*0.52),
                halign='left', valign='top'
            )
            # Center big suit
            cs = Label(
                text=f"[color={hex_color}]{self.card.suit}[/color]",
                markup=True, font_size=fs_center,
                size_hint=(None, None), size=(w, h*0.5),
                pos=(x, y + h*0.25),
                halign='center', valign='middle'
            )
            self.add_widget(tl)
            self.add_widget(ts)
            self.add_widget(cs)

    def set_card(self, card, face_down=False):
        self.card      = card
        self.face_down = face_down
        self._draw()


# ──────────────────────────────────────────────
# CHIP DISPLAY
# ──────────────────────────────────────────────
class ChipStack(Label):
    def __init__(self, amount=0, **kwargs):
        super().__init__(**kwargs)
        self.amount = amount
        self._update()
        self.bind(size=self._draw_bg, pos=self._draw_bg)

    def set_amount(self, v):
        self.amount = v
        self._update()

    def _update(self):
        self.text = f"[b]${self.amount}[/b]"
        self.markup = True

    def _draw_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*C_BTN_GRAY, 0.85)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8])


# ──────────────────────────────────────────────
# PLAYER PANEL
# ──────────────────────────────────────────────
class PlayerPanel(RelativeLayout):
    def __init__(self, player_data, is_human=False, **kwargs):
        super().__init__(**kwargs)
        self.player_data = player_data
        self.is_human    = is_human
        self.card_widgets = []
        self._build()

    def _build(self):
        self.clear_widgets()
        w, h = self.size

        # Background panel
        with self.canvas.before:
            Color(*C_BG_DARK, 0.8)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])

        self.bind(pos=self._update_bg, size=self._update_bg)

        # Name label
        self.name_lbl = Label(
            text=f"[b]{self.player_data['name']}[/b]",
            markup=True, font_size=14, color=C_GOLD,
            size_hint=(1, None), height=22,
            pos_hint={'x': 0, 'top': 1},
            halign='center'
        )
        self.add_widget(self.name_lbl)

        # Chips label
        self.chips_lbl = Label(
            text=f"[b]${self.player_data['chips']}[/b]",
            markup=True, font_size=13, color=C_WHITE,
            size_hint=(1, None), height=20,
            pos_hint={'x': 0, 'y': 0},
            halign='center'
        )
        self.add_widget(self.chips_lbl)

        # Cards area
        self.cards_box = BoxLayout(
            orientation='horizontal', spacing=4,
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.cards_box)

        # Status label (Dealer/SB/BB, action)
        self.status_lbl = Label(
            text='', font_size=11, color=C_HIGHLIGHT,
            size_hint=(1, None), height=18,
            pos_hint={'x': 0, 'y': 0.12},
            halign='center', markup=True
        )
        self.add_widget(self.status_lbl)

    def _update_bg(self, *args):
        self.bg_rect.pos  = self.pos
        self.bg_rect.size = self.size

    def refresh(self, show_cards=False, status_text=''):
        self.chips_lbl.text  = f"[b]${self.player_data['chips']}[/b]"
        self.status_lbl.text = status_text

        # Update cards
        self.cards_box.clear_widgets()
        self.card_widgets = []
        pw = self.size[0]
        card_w = min(max(pw * 0.4, 38), 55)
        card_h = card_w * 1.45
        self.cards_box.size = (card_w*2 + 8, card_h)

        cards = self.player_data.get('_hole', [])
        for i, c in enumerate(cards):
            cw = CardWidget(
                card=c,
                face_down=(not show_cards and not self.is_human),
                size=(card_w, card_h)
            )
            self.cards_box.add_widget(cw)
            self.card_widgets.append(cw)

    def highlight(self, on=True):
        """Highlight when it's this player's turn."""
        self.canvas.before.clear()
        with self.canvas.before:
            if on:
                Color(*C_GOLD, 0.35)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
            Color(*C_BG_DARK, 0.8)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])


# ──────────────────────────────────────────────
# BET SLIDER / INPUT
# ──────────────────────────────────────────────
class RaiseSlider(BoxLayout):
    def __init__(self, min_val, max_val, **kwargs):
        super().__init__(orientation='horizontal', spacing=6, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.value   = min_val

        from kivy.uix.slider import Slider
        self.slider = Slider(
            min=min_val, max=max_val, value=min_val,
            size_hint=(1, 1)
        )
        self.slider.bind(value=self._on_slide)

        self.val_lbl = Label(
            text=f"${min_val}",
            size_hint=(None, 1), width=70,
            font_size=14, color=C_GOLD,
            bold=True, markup=True
        )

        self.add_widget(self.slider)
        self.add_widget(self.val_lbl)

    def _on_slide(self, inst, val):
        self.value = int(val)
        self.val_lbl.text = f"[b]${self.value}[/b]"

    def get_value(self):
        return int(self.slider.value)


# ──────────────────────────────────────────────
# ACTION LOG
# ──────────────────────────────────────────────
class ActionLog(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(1, 1),
            do_scroll_x=False,
            **kwargs
        )
        self.log_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=1,
            padding=[4, 2]
        )
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        self.add_widget(self.log_layout)
        self.entries = []

    def add_entry(self, text, color=C_WHITE):
        lbl = Label(
            text=text,
            font_size=11,
            color=color,
            size_hint_y=None,
            height=18,
            halign='left',
            valign='middle',
            text_size=(self.width - 8, None)
        )
        self.log_layout.add_widget(lbl)
        self.entries.append(lbl)
        # Keep only last 30
        if len(self.entries) > 30:
            self.log_layout.remove_widget(self.entries.pop(0))
        Clock.schedule_once(lambda dt: self._scroll_bottom(), 0.05)

    def _scroll_bottom(self):
        self.scroll_y = 0

    def clear_log(self):
        self.log_layout.clear_widgets()
        self.entries = []


# ──────────────────────────────────────────────
# MAIN GAME SCREEN
# ──────────────────────────────────────────────
class GameScreen(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game         = PokerGame()
        self.raise_slider = None
        self.action_queue = []
        self.waiting_ai   = False
        self._build_ui()
        Clock.schedule_once(lambda dt: self._start_hand(), 0.3)

    # ── BUILD UI ──────────────────────────────
    def _build_ui(self):
        # Background
        with self.canvas.before:
            Color(*C_BG)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # ── Top info bar ──
        top_bar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None), height=36,
            pos_hint={'x': 0, 'top': 1},
            padding=[8, 4], spacing=8
        )
        with top_bar.canvas.before:
            Color(*C_BG_DARK, 0.9)
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda i,v: setattr(top_bar.canvas.before.children[1], 'pos', v),
                     size=lambda i,v: setattr(top_bar.canvas.before.children[1], 'size', v))

        self.hand_lbl = Label(
            text='[b]Hand #1[/b]', markup=True,
            font_size=13, color=C_GOLD, size_hint=(None, 1), width=80
        )
        self.stage_lbl = Label(
            text='[b]Pre-Flop[/b]', markup=True,
            font_size=13, color=C_WHITE, size_hint=(1, 1)
        )
        self.pot_lbl = Label(
            text='[b]Pot: $0[/b]', markup=True,
            font_size=14, color=C_HIGHLIGHT, size_hint=(None, 1), width=110
        )
        top_bar.add_widget(self.hand_lbl)
        top_bar.add_widget(self.stage_lbl)
        top_bar.add_widget(self.pot_lbl)
        self.add_widget(top_bar)

        # ── AI Player panels (top area) ──
        ai_row = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None), height=110,
            pos_hint={'x': 0, 'top': 0.88},
            spacing=10, padding=[8, 4]
        )
        self.panels = []

        for i in range(3):
            p = self.game.players[i]
            panel = PlayerPanel(
                p,
                is_human=p['is_human'],
                size_hint=(1, 1)
            )
            self.panels.append(panel)
            ai_row.add_widget(panel)

        self.add_widget(ai_row)

        # ── Community cards ──
        community_area = BoxLayout(
            orientation='vertical',
            size_hint=(0.85, None), height=110,
            pos_hint={'center_x': 0.5, 'top': 0.62},
            spacing=4
        )

        # Dealer button indicator
        self.dealer_lbl = Label(
            text='', font_size=11, color=C_HIGHLIGHT,
            size_hint=(1, None), height=18,
            halign='center', markup=True
        )
        community_area.add_widget(self.dealer_lbl)

        # Community card row
        comm_card_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 1),
            spacing=6
        )
        self.comm_card_box = comm_card_box
        community_area.add_widget(comm_card_box)
        self.add_widget(community_area)

        # ── Action Log (right side) ──
        self.action_log = ActionLog(
            size_hint=(0.3, None), height=160,
            pos_hint={'right': 0.99, 'y': 0.34}
        )
        with self.action_log.canvas.before:
            Color(*C_BG_DARK, 0.75)
            RoundedRectangle(pos=self.action_log.pos, size=self.action_log.size, radius=[8])
        self.add_widget(self.action_log)

        # ── Raise slider area ──
        self.slider_area = BoxLayout(
            orientation='vertical',
            size_hint=(0.65, None), height=48,
            pos_hint={'x': 0.01, 'y': 0.27},
            spacing=4, padding=[4, 2]
        )
        self.slider_area.opacity = 0
        self.add_widget(self.slider_area)

        # ── Action buttons ──
        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None), height=56,
            pos_hint={'x': 0, 'y': 0.01},
            spacing=8, padding=[8, 4]
        )
        self.btn_fold  = self._make_btn('Fold',       C_BTN_RED,    self._on_fold)
        self.btn_check = self._make_btn('Check/Call', C_BTN_BLUE,   self._on_check_call)
        self.btn_raise = self._make_btn('Raise',      C_BTN_ORANGE, self._on_raise_toggle)
        self.btn_allin = self._make_btn('All-In',     C_BTN_GRAY,   self._on_allin)
        btn_row.add_widget(self.btn_fold)
        btn_row.add_widget(self.btn_check)
        btn_row.add_widget(self.btn_raise)
        btn_row.add_widget(self.btn_allin)
        self.add_widget(btn_row)

        # Confirm raise button (hidden initially)
        self.btn_confirm_raise = Button(
            text='[b]Confirm Raise[/b]', markup=True,
            size_hint=(0.4, None), height=40,
            pos_hint={'center_x': 0.3, 'y': 0.16},
            background_normal='',
            background_color=C_BTN_ORANGE,
            font_size=13, color=C_WHITE,
            opacity=0, disabled=True
        )
        self.btn_confirm_raise.bind(on_press=self._on_confirm_raise)
        self.add_widget(self.btn_confirm_raise)

        # ── Winner popup overlay ──
        self.winner_overlay = Label(
            text='', markup=True,
            size_hint=(0.7, None), height=60,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            font_size=18, color=C_GOLD,
            halign='center', opacity=0
        )
        with self.winner_overlay.canvas.before:
            Color(*C_BG_DARK, 0.92)
            self.wo_bg = RoundedRectangle(pos=self.winner_overlay.pos,
                                          size=self.winner_overlay.size, radius=[12])
        self.winner_overlay.bind(
            pos=lambda i,v: setattr(self.wo_bg, 'pos', v),
            size=lambda i,v: setattr(self.wo_bg, 'size', v)
        )
        self.add_widget(self.winner_overlay)

        # New hand button
        self.btn_new_hand = Button(
            text='[b]Next Hand ▶[/b]', markup=True,
            size_hint=(0.45, None), height=46,
            pos_hint={'center_x': 0.5, 'y': 0.48},
            background_normal='',
            background_color=C_BTN_GREEN,
            font_size=15, color=C_WHITE,
            opacity=0, disabled=True
        )
        self.btn_new_hand.bind(on_press=lambda _: self._start_hand())
        self.add_widget(self.btn_new_hand)

        self._set_buttons_enabled(False)

    def _make_btn(self, text, color, callback):
        btn = Button(
            text=f'[b]{text}[/b]', markup=True,
            size_hint=(1, 1),
            background_normal='',
            background_color=color,
            font_size=14, color=C_WHITE,
            disabled=True
        )
        btn.bind(on_press=callback)
        return btn

    def _update_bg(self, *args):
        self.bg.pos  = self.pos
        self.bg.size = self.size

    # ── GAME FLOW ─────────────────────────────
    def _start_hand(self):
        self.winner_overlay.opacity = 0
        self.btn_new_hand.opacity   = 0
        self.btn_new_hand.disabled  = True
        self._hide_raise_slider()

        self.action_log.clear_log()
        first_actor = self.game.start_new_hand()
        self._flush_log()
        self._refresh_ui()

        self.hand_lbl.text  = f'[b]Hand #{self.game.hand_num}[/b]'
        self.stage_lbl.text = '[b]Pre-Flop[/b]'

        # Flush to log immediately
        self._flush_log()

        # Start betting round
        self._run_betting_round(first_actor)

    def _run_betting_round(self, first_actor_idx):
        """Build ordered action queue and process."""
        g = self.game
        n = 3
        order = [(first_actor_idx + i) % n for i in range(n)]
        order = [i for i in order if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0]

        self.action_queue   = order[:]
        self.bet_order      = order[:]   # full order for re-raise tracking
        self.acted_this_round = set()
        self.last_raiser    = -1
        self._process_next_action()

    def _process_next_action(self):
        """Pop next player from queue and handle."""
        g = self.game

        # If only one player left (all others folded), end hand
        active = [i for i in range(3) if not g.folded[i]]
        if len(active) == 1:
            self._end_hand()
            return

        # Betting complete?
        can_act = [i for i in range(3) if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0]
        if not can_act:
            self._advance_stage()
            return

        if not self.action_queue:
            # Check if betting is actually done
            all_matched = all(
                g.bets[i] == g.current_bet
                for i in can_act
            )
            if all_matched or len(can_act) <= 1:
                self._advance_stage()
            else:
                # Re-open action (someone raised)
                remaining = [i for i in self.bet_order if i in can_act and i != self.last_raiser]
                if remaining:
                    self.action_queue = remaining
                    self._process_next_action()
                else:
                    self._advance_stage()
            return

        idx = self.action_queue.pop(0)

        if g.folded[idx] or g.all_in[idx] or g.players[idx]['chips'] == 0:
            self._process_next_action()
            return

        self._refresh_ui(acting_idx=idx)

        if g.players[idx]['is_human']:
            self._set_buttons_enabled(True)
            self.current_acting = idx
        else:
            self._set_buttons_enabled(False)
            Clock.schedule_once(lambda dt: self._ai_act(idx), 1.2)

    def _ai_act(self, idx):
        g = self.game
        p = g.players[idx]
        to_call = g.to_call_for(idx)
        action, amount = p['ai'].decide(
            g.hole_cards[idx], g.community,
            g.pot, to_call, p['chips'], g.stage
        )

        was_raiser = (action in ('raise', 'allin'))
        g.apply_action(idx, action, amount)

        if was_raiser:
            self.last_raiser = idx
            # Re-add other players who haven't acted since raise
            can_act = [i for i in range(3) if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0 and i != idx]
            self.action_queue = can_act

        self._flush_log()
        self._refresh_ui()
        Clock.schedule_once(lambda dt: self._process_next_action(), 0.3)

    def _advance_stage(self):
        g = self.game
        stages = ['preflop', 'flop', 'turn', 'river']
        idx = stages.index(g.stage) if g.stage in stages else -1

        if idx == len(stages) - 1 or idx == -1:
            self._end_hand()
            return

        g.stage = stages[idx + 1]
        g.bets  = [0, 0, 0]
        g.current_bet = 0
        g.deal_community()

        self.stage_lbl.text = f'[b]{g.stage.capitalize()}[/b]'
        self.action_log.add_entry(f'── {g.stage.upper()} ──', C_GOLD)
        self._refresh_ui()

        # Post-flop: first active left of dealer
        n = 3
        order_start = (g.dealer_idx + 1) % n
        order = [(order_start + i) % n for i in range(n)]
        order = [i for i in order if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0]

        if not order:
            self._end_hand()
            return

        self.bet_order   = order[:]
        self.action_queue = order[:]
        self.last_raiser  = -1
        Clock.schedule_once(lambda dt: self._process_next_action(), 0.4)

    def _end_hand(self):
        g = self.game
        winners = g.determine_winners()
        g.payout(winners)
        g.round_over = True

        # Show all cards
        for i, p in enumerate(g.players):
            p['_hole'] = g.hole_cards[i]

        self._refresh_ui(show_all=True)
        self._set_buttons_enabled(False)

        # Winner message
        msgs = []
        for (widx, amount, desc) in winners:
            name = g.players[widx]['name']
            msgs.append(f"{name} wins ${amount} ({desc})")
            self.action_log.add_entry(f"🏆 {name} wins ${amount} [{desc}]", C_GOLD)

        self.winner_overlay.text    = '[b]' + '\n'.join(msgs) + '[/b]'
        self.winner_overlay.opacity = 1

        self.btn_new_hand.opacity  = 1
        self.btn_new_hand.disabled = False

        g.next_dealer()
        self._refresh_ui(show_all=True)

    # ── PLAYER ACTIONS ────────────────────────
    def _on_fold(self, *args):
        self._player_act('fold', 0)

    def _on_check_call(self, *args):
        g = self.game
        to_call = g.to_call_for(0)
        if to_call == 0:
            self._player_act('check', 0)
        else:
            self._player_act('call', to_call)

    def _on_raise_toggle(self, *args):
        if self.slider_area.opacity == 0:
            self._show_raise_slider()
        else:
            self._hide_raise_slider()

    def _show_raise_slider(self):
        g = self.game
        p = g.players[0]
        to_call = g.to_call_for(0)
        min_raise = max(g.current_bet + g.BIG_BLIND, to_call + g.BIG_BLIND)
        min_raise = min(min_raise, p['chips'])
        max_raise = p['chips']

        if min_raise >= max_raise:
            self._player_act('allin', p['chips'])
            return

        self.slider_area.clear_widgets()
        slider = RaiseSlider(min_raise, max_raise, size_hint=(1, None), height=44)
        self.current_raise_slider = slider
        self.slider_area.add_widget(slider)
        self.slider_area.opacity = 1

        self.btn_confirm_raise.opacity  = 1
        self.btn_confirm_raise.disabled = False

    def _hide_raise_slider(self):
        self.slider_area.opacity        = 0
        self.btn_confirm_raise.opacity  = 0
        self.btn_confirm_raise.disabled = True

    def _on_confirm_raise(self, *args):
        if hasattr(self, 'current_raise_slider'):
            amount = self.current_raise_slider.get_value()
            self._player_act('raise', amount)
        self._hide_raise_slider()

    def _on_allin(self, *args):
        chips = self.game.players[0]['chips']
        self._player_act('allin', chips)

    def _player_act(self, action, amount):
        self._set_buttons_enabled(False)
        self._hide_raise_slider()
        g = self.game
        was_raiser = (action in ('raise', 'allin'))
        g.apply_action(0, action, amount)
        if was_raiser:
            self.last_raiser = 0
            can_act = [i for i in range(3) if not g.folded[i] and not g.all_in[i] and g.players[i]['chips'] > 0 and i != 0]
            self.action_queue = can_act
        self._flush_log()
        self._refresh_ui()
        Clock.schedule_once(lambda dt: self._process_next_action(), 0.2)

    # ── UI HELPERS ────────────────────────────
    def _set_buttons_enabled(self, enabled):
        g = self.game
        for btn in [self.btn_fold, self.btn_check, self.btn_raise, self.btn_allin]:
            btn.disabled = not enabled

        if enabled:
            to_call = g.to_call_for(0)
            if to_call == 0:
                self.btn_check.text = '[b]Check[/b]'
                self.btn_check.background_color = C_BTN_GREEN
            else:
                self.btn_check.text = f'[b]Call ${to_call}[/b]'
                self.btn_check.background_color = C_BTN_BLUE

    def _flush_log(self):
        g = self.game
        while g.action_log:
            entry = g.action_log.pop(0)
            color = C_HIGHLIGHT if 'raises' in entry else C_WHITE
            if 'folds' in entry:
                color = C_GRAY
            elif 'wins' in entry:
                color = C_GOLD
            self.action_log.add_entry(entry, color)

    def _refresh_ui(self, acting_idx=-1, show_all=False):
        g = self.game
        self.pot_lbl.text = f'[b]Pot: ${g.pot}[/b]'

        # Dealer label
        d_name = g.players[g.dealer_idx]['name']
        sb_idx = (g.dealer_idx + 1) % 3
        bb_idx = (g.dealer_idx + 2) % 3
        self.dealer_lbl.text = (
            f'[b][color=#f1c40f]🃏 Dealer: {d_name}  '
            f'SB: {g.players[sb_idx]["name"]}  '
            f'BB: {g.players[bb_idx]["name"]}[/color][/b]'
        )

        # Player panels
        for i, panel in enumerate(self.panels):
            p = g.players[i]
            p['_hole'] = g.hole_cards[i]

            status_parts = []
            if g.folded[i]:
                status_parts.append('[color=#888888]FOLDED[/color]')
            elif g.all_in[i]:
                status_parts.append('[color=#f39c12]ALL-IN[/color]')

            bet = g.bets[i]
            if bet > 0:
                status_parts.append(f'Bet: ${bet}')

            if i == acting_idx:
                status_parts.append('[color=#f1c40f]◀ Acting[/color]')

            show = show_all or p['is_human']
            panel.refresh(show_cards=show, status_text=' '.join(status_parts))
            panel.highlight(on=(i == acting_idx))

        # Community cards
        self.comm_card_box.clear_widgets()
        card_size = (52, 75)
        for c in g.community:
            cw = CardWidget(card=c, face_down=False, size=card_size, size_hint=(None, None))
            self.comm_card_box.add_widget(cw)
        # Empty placeholders
        for _ in range(5 - len(g.community)):
            ph = Widget(size=card_size, size_hint=(None, None))
            with ph.canvas:
                Color(*C_BG_DARK, 0.5)
                RoundedRectangle(pos=ph.pos, size=ph.size, radius=[6])
            ph.bind(pos=lambda i, v: None)
            self.comm_card_box.add_widget(ph)


# ──────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────
class TexasHoldemApp(App):
    def build(self):
        Window.clearcolor = C_BG
        self.title = "Texas Hold'em Poker"
        self.icon  = ''
        root = GameScreen()
        return root


if __name__ == '__main__':
    TexasHoldemApp().run()
