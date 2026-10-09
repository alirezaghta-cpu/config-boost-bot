from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from bot import quota

TEHRAN = ZoneInfo("Asia/Tehran")


@pytest.mark.parametrize(
    ("qualified", "expected"),
    [(0, 1), (1, 1), (2, 2), (3, 2), (4, 3)],
)
def test_formula_table(qualified, expected):
    assert quota.balance(qualified, 0) == expected


def test_saturday_boundary_resets_usage_but_keeps_qualification():
    friday = datetime(2025, 1, 3, 23, 59, tzinfo=TEHRAN)
    saturday = datetime(2025, 1, 4, 0, 0, tzinfo=TEHRAN)
    assert quota.week_key(friday) != quota.week_key(saturday)

    user = {
        "tg_id": 20,
        "used_week_key": quota.week_key(friday),
        "used_this_week": 2,
        "used_total": 7,
        "qualified_at": "2024-12-01T12:00:00+03:30",
        "delivered_config_ids": ["a"],
        "delivered_this_week_ids": ["a"],
    }
    reset = quota.reset_week_if_needed(user, saturday)
    assert reset["used_this_week"] == 0
    assert reset["used_total"] == 7
    assert reset["qualified_at"] == user["qualified_at"]
    assert reset["delivered_this_week_ids"] == []


def test_qualification_happens_only_on_first_consumption():
    user = {
        "tg_id": 2,
        "inviter": 1,
        "qualified_at": None,
        "used_total": 0,
        "used_week_key": quota.week_key(),
        "used_this_week": 0,
        "delivered_config_ids": [],
        "delivered_this_week_ids": [],
    }
    assert not quota.is_qualified_invitee(user)
    result = quota.consume_one(user, qualified_referrals=0, config_id="cfg")
    assert result.allowed
    assert result.became_qualified
    assert result.user["used_total"] == 1
    assert quota.is_qualified_invitee(result.user)

    next_result = quota.consume_one(result.user, qualified_referrals=2, config_id="cfg2")
    assert next_result.allowed
    assert not next_result.became_qualified


def test_self_invite_rejected():
    decision = quota.assign_referral({}, invitee_id=7, inviter_id=7, daily_new_count=0)
    assert not decision.accepted
    assert decision.reason == "self_invite"
    assert decision.user.get("inviter") is None


def test_first_inviter_wins_forever():
    first = quota.assign_referral({}, invitee_id=9, inviter_id=1, daily_new_count=0)
    assert first.accepted
    second = quota.assign_referral(first.user, invitee_id=9, inviter_id=2, daily_new_count=0)
    assert not second.accepted
    assert second.user["inviter"] == 1


def test_second_person_qualification_opens_one_more_same_week():
    first = {
        "tg_id": 11,
        "inviter": 1,
        "qualified_at": "2025-01-01T00:00:00+03:30",
        "used_total": 1,
    }
    second = {
        "tg_id": 12,
        "inviter": 1,
        "qualified_at": None,
        "used_total": 0,
        "used_week_key": quota.week_key(),
        "used_this_week": 0,
        "delivered_config_ids": [],
        "delivered_this_week_ids": [],
    }
    qualified_before = sum(map(quota.is_qualified_invitee, [first, second]))
    assert qualified_before == 1
    assert quota.balance(qualified_before, used_this_week=1) == 0

    consumed = quota.consume_one(second, qualified_referrals=0, config_id="own")
    qualified_after = sum(map(quota.is_qualified_invitee, [first, consumed.user]))
    assert qualified_after == 2
    assert quota.balance(qualified_after, used_this_week=1) == 1



def test_two_new_qualified_after_one_use_opens_one_more():
    assert quota.balance(qualified=0, used_this_week=1) == 0
    assert quota.balance(qualified=2, used_this_week=1) == 1


def test_next_saturday_restores_full_entitlement():
    friday = datetime(2025, 1, 3, 20, 0, tzinfo=TEHRAN)
    saturday = datetime(2025, 1, 4, 0, 0, tzinfo=TEHRAN)
    user = {
        "used_week_key": quota.week_key(friday),
        "used_this_week": 2,
        "used_total": 2,
        "delivered_config_ids": ["a", "b"],
        "delivered_this_week_ids": ["a", "b"],
    }
    reset = quota.reset_week_if_needed(user, saturday)
    assert quota.balance(qualified=4, used_this_week=reset["used_this_week"]) == 3


def test_invite_cap_ten_per_tehran_day():
    count = 0
    accepted = 0
    for invitee_id in range(100, 111):
        decision = quota.assign_referral(
            {}, invitee_id=invitee_id, inviter_id=1, daily_new_count=count
        )
        count = decision.new_daily_count
        accepted += int(decision.accepted)
    assert accepted == 10
    assert count == 10


def test_shortage_message_uses_persian_digits():
    text = quota.shortage_message(4, 3)
    assert "زیرمجموعهٔ معتبر: ۴" in text
    assert "مصرف‌شده: ۳" in text
