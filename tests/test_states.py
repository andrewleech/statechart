# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Leigh McKenzie
# All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import pytest

from statechart import (Action, CompositeState, ConcurrentState, Event, FinalState,
                        InitialState, State, Statechart, Transition)


class ActionSpy(Action):
    def __init__(self):
        self.executed = False

    def execute(self, param):
        self.executed = True


class StateSpy(State):
    def __init__(self, name, context):
        State.__init__(self, name=name, context=context)
        self.dispatch_called = False
        self.metadata = None
        self.event = None

    def dispatch(self, metadata, event, param):
        self.dispatch_called = True
        self.metadata = metadata
        self.event = event
        return True


class TestStatechart:
    def test_create_statechart(self):
        Statechart(name='statechart', param=0)

    def test_start(self):
        statechart = Statechart(name='statechart', param=0)
        initial_state = InitialState(name='initial', context=statechart)
        statechart.start()
        assert statechart.initial_state is initial_state

    def test_dispatch(self):
        statechart = Statechart(name='statechart', param=0)
        initial_state = InitialState(name='initial', context=statechart)
        default_state = StateSpy(name='default', context=statechart)
        next_state = State(name='next', context=statechart)
        test_event = Event(name='test_event', param=123)
        Transition('default_transition', start=initial_state,
                   end=default_state)
        Transition(name='test_transition', start=default_state, end=next_state,
                   event=test_event)
        statechart.start()
        assert statechart.dispatch(event=test_event)
        assert default_state.dispatch_called
        assert default_state.event == test_event

    def test_add_transition(self):
        statechart = Statechart(name='statechart', param=0)
        initial_state = InitialState(name='initial', context=statechart)

        with pytest.raises(RuntimeError):
            Transition('initial_transition', start=statechart,
                       end=initial_state)


class TestState:
    def test_create_state(self):
        statechart = Statechart(name='statechart', param=0)
        State(name='anon', context=statechart)

    def test_create_state_without_parent(self):
        with pytest.raises(RuntimeError):
            State(name='anon', context=None)

    def test_add_transition(self):
        statechart = Statechart(name='statechart', param=0)
        initial_state = InitialState(name='initial', context=statechart)
        default_state = State(name='default', context=statechart)

        default_transition = Transition(name='default', start=initial_state,
                                        end=default_state)

        assert default_transition in initial_state._transitions

    def test_activate(self):
        statechart = Statechart(name='statechart', param=0)
        InitialState(name='initial', context=statechart)
        default_state = State(name='default', context=statechart)
        statechart.start()

        default_state.activate(statechart.metadata, 0)

        assert statechart.metadata.is_active(default_state)

    def test_deactivate(self):
        statechart = Statechart(name='statechart', param=0)
        InitialState(name='initial', context=statechart)
        default_state = State(name='default', context=statechart)
        statechart.start()

        default_state.activate(statechart.metadata, 0)
        assert statechart.metadata.is_active(default_state)

        default_state.deactivate(statechart.metadata, 0)
        assert not statechart.metadata.is_active(default_state)

    def test_dispatch(self):
        statechart = Statechart(name='statechart', param=0)
        initial_state = InitialState(name='initial', context=statechart)
        default_state = State(name='default', context=statechart)
        statechart.start()

        default_trigger = Event('default_trigger', 0)
        Transition(name='default', start=initial_state, end=default_state,
                   event=default_trigger)

        assert initial_state.dispatch(metadata=statechart.metadata,
                                      event=default_trigger, param=0)

        assert statechart.metadata.is_active(default_state)


class TestFinalState:
    def test_add_transition(self):
        statechart = Statechart(name='statechart', param=0)
        final_state = FinalState(name='final', context=statechart)

        with pytest.raises(RuntimeError):
            Transition(name='final', start=final_state, end=statechart)

    def test_dispatch(self):
        statechart = Statechart(name='statechart', param=0)
        final_state = FinalState(name='final', context=statechart)
        final_trigger = Event(name='final_trigger', param=0)
        with pytest.raises(RuntimeError):
            final_state.dispatch(metadata=statechart.metadata,
                                 event=final_trigger, param=0)


# TODO(lam) Add test with final states - state shouldn't dispatch default
# event until all regions have finished.
# TOOD(lam) Add test for transition directly into a concurrent, composite sub
# state.
class TestConcurrentState:
    def test_keyboard_example(self):
        """
        Test classic concurrent state keyboard example with concurrent states
        for caps, num and scroll lock.

        init - -
               |
               v
        -- keyboard --------------------------------------
        |                                                |
        |  init ---> --caps lock off --                  |
        |        --- |                | <--              |
        |        |   -----------------|   |              |
        |  caps lock pressed       caps lock pressed     |
        |        |   -- caps lock on --   |              |
        |        --> |                | ---              |
        |            ------------------                  |
        |                                                |
        --------------------------------------------------
        |                                                |
        |  init ---> --num lock off ---                  |
        |        --- |                | <--              |
        |        |   -----------------|   |              |
        |  num lock pressed      num lock pressed        |
        |        |   -- num lock on ---   |              |
        |        --> |                | ---              |
        |            ------------------                  |
        |                                                |
        --------------------------------------------------
        |                                                |
        |  init ---> -- scroll lock off --               |
        |        --- |                    | <--          |
        |        |   ---------------------|   |          |
        |  scroll lock pressed      scroll lock pressed  |
        |        |   -- scroll lock on ---|   |          |
        |        --> |                    | ---          |
        |            ----------------------              |
        |                                                |
        --------------------------------------------------
        """
        statechart = Statechart(name='statechart', param=0)

        start_state = InitialState(name='start_state', context=statechart)
        keyboard = ConcurrentState(name='keyboard', context=statechart)
        Transition(name='start', start=start_state, end=keyboard)

        caps_lock = CompositeState(name='caps_lock', context=keyboard)
        caps_lock_initial = InitialState(name='caps_lock_initial',
                                         context=caps_lock)
        caps_lock_on = State(name='caps_lock_on', context=caps_lock)
        caps_lock_off = State(name='caps_lock_off', context=caps_lock)
        caps_lock_pressed = Event(name='caps_lock_pressed', param=None)
        Transition(name='caps_lock_default_off', start=caps_lock_initial,
                   end=caps_lock_off)
        Transition(name='caps_lock_on', start=caps_lock_on, end=caps_lock_off,
                   event=caps_lock_pressed)
        Transition(name='caps_lock_off', start=caps_lock_off, end=caps_lock_on,
                   event=caps_lock_pressed)

        num_lock = CompositeState(name='num_lock', context=keyboard)
        num_lock_initial = InitialState(name='num_lock_initial',
                                        context=num_lock)
        num_lock_on = State(name='num_lock_on', context=num_lock)
        num_lock_off = State(name='num_lock_off', context=num_lock)
        num_lock_pressed = Event(name='num_lock_pressed', param=None)
        Transition(name='num_lock_default_off', start=num_lock_initial,
                   end=num_lock_off)
        Transition(name='num_lock_on', start=num_lock_on, end=num_lock_off,
                   event=num_lock_pressed)
        Transition(name='num_lock_off', start=num_lock_off, end=num_lock_on,
                   event=num_lock_pressed)

        scroll_lock = CompositeState(name='scroll_lock', context=keyboard)
        scroll_lock_initial = InitialState(name='scroll_lock_initial',
                                           context=scroll_lock)
        scroll_lock_on = State(name='scroll_lock_on', context=scroll_lock)
        scroll_lock_off = State(name='scroll_lock_off', context=scroll_lock)
        scroll_lock_pressed = Event(name='scroll_lock_pressed', param=None)
        Transition(name='scroll_lock_default_off', start=scroll_lock_initial,
                   end=scroll_lock_off)
        Transition(name='scroll_lock_on', start=scroll_lock_on,
                   end=scroll_lock_off, event=scroll_lock_pressed)
        Transition(name='scroll_lock_off', start=scroll_lock_off,
                   end=scroll_lock_on, event=scroll_lock_pressed)

        statechart.start()

        assert statechart.metadata.is_active(keyboard)
        assert statechart.metadata.is_active(caps_lock_off)
        assert statechart.metadata.is_active(num_lock_off)
        assert statechart.metadata.is_active(scroll_lock_off)

        statechart.dispatch(event=caps_lock_pressed)
        assert statechart.metadata.is_active(caps_lock_on)

        statechart.dispatch(event=num_lock_pressed)
        assert statechart.metadata.is_active(num_lock_on)

        statechart.dispatch(event=scroll_lock_pressed)
        assert statechart.metadata.is_active(scroll_lock_on)

        statechart.dispatch(event=caps_lock_pressed)
        assert statechart.metadata.is_active(caps_lock_off)

        statechart.dispatch(event=num_lock_pressed)
        assert statechart.metadata.is_active(num_lock_off)

        statechart.dispatch(event=scroll_lock_pressed)
        assert statechart.metadata.is_active(scroll_lock_off)


class TestCompositeState:
    class Submachine(CompositeState):
        def __init__(self, name, context):
            CompositeState.__init__(self, name=name, context=context)

            init = InitialState(name='init submachine', context=self)
            self.state_a = State(name='sub state a', context=self)
            self.state_b = State(name='sub state b', context=self)

            self.sub_a_to_b = Event('sub cd', None)
            Transition(name='init', start=init, end=self.state_a)
            Transition(name='sub_cd', start=self.state_a, end=self.state_b, event=self.sub_a_to_b)

    def test_submachines(self):
        statechart = Statechart(name='statechart', param=0)

        init = InitialState(name='init a', context=statechart)
        top_a = self.Submachine('top a', statechart)
        top_b = self.Submachine('top b', statechart)

        top_a_to_b = Event('top_ab', None)
        Transition(name='init', start=init, end=top_a)
        Transition(name='init', start=top_a, end=top_b, event=top_a_to_b)

        statechart.start()

        assert statechart.metadata.is_active(top_a)
        assert statechart.metadata.is_active(top_a.state_a)

        statechart.dispatch(top_a.sub_a_to_b)

        assert statechart.metadata.is_active(top_a)
        assert statechart.metadata.is_active(top_a.state_b)

        statechart.dispatch(top_a_to_b)

        assert statechart.metadata.is_active(top_b)
        assert statechart.metadata.is_active(top_b.state_a)

        statechart.dispatch(top_a.sub_a_to_b)

        assert statechart.metadata.is_active(top_b)
        assert statechart.metadata.is_active(top_b.state_b)
