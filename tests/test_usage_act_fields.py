"""Cost and discount fields of ``UsageActShortSerializer`` the SDK used to drop.

Server-side source: ``UsageActShortSerializer`` in
``website/user_panel/serializers.py``. Six fields: ``next_charge_rub_cents``
(``mround(get_held_up_money())``), ``full_period_cost_rub_cents``
(``get_debt_info(include_prepay=True)[2]``), ``full_planned_cost_rub_cents``
(unit price x ``periods_planned``), ``discount_percent`` (model field,
default 0), ``promocode_code`` (str or null) and ``promocode_discount_value``
(int or null, only for percentage promocodes).

The same serializer feeds ``usage_act``, ``last_usage_act``,
``last_finished_usage_act`` and ``resume_usage_act`` of a ``CloudServer``.
All four cost fields are ``int`` kopecks; the OpenAPI schema calls five of the
six ``string`` (``SerializerMethodField``).
"""

from intelion_cloud.models import CloudServer, UsageAct

from .conftest import SAMPLE_CLOUD_SERVER, SAMPLE_TERM_USAGE_ACT, SAMPLE_USAGE_ACT

COST_FIELDS = (
    "next_charge_rub_cents",
    "full_period_cost_rub_cents",
    "full_planned_cost_rub_cents",
    "discount_percent",
    "promocode_code",
    "promocode_discount_value",
)


class TestUsageActCostFields:
    def test_all_six_fields_are_read(self):
        act = UsageAct.from_dict(SAMPLE_TERM_USAGE_ACT)
        for name in COST_FIELDS:
            assert getattr(act, name) == SAMPLE_TERM_USAGE_ACT[name], name

    def test_hourly_act_without_discount_or_promocode(self):
        act = UsageAct.from_dict(SAMPLE_USAGE_ACT)
        assert act.next_charge_rub_cents == 16071
        assert act.full_period_cost_rub_cents == 16071
        assert act.full_planned_cost_rub_cents == 16071
        assert act.discount_percent == 0
        assert act.promocode_code is None
        assert act.promocode_discount_value is None

    def test_term_act_with_discount_and_percentage_promocode(self):
        act = UsageAct.from_dict(SAMPLE_TERM_USAGE_ACT)
        # One month frozen at a time for a company: planned cost is the monthly price
        assert act.periods_planned == 1
        assert act.full_planned_cost_rub_cents == 6318000
        assert act.discount_percent == 35
        assert act.promocode_code == "WELCOME10"
        assert act.promocode_discount_value == 10

    def test_individual_pays_whole_term_in_planned_cost(self):
        """Individuals freeze the whole term: ``periods_planned`` is the term, cost is already multiplied."""
        act = UsageAct.from_dict(
            {**SAMPLE_TERM_USAGE_ACT, "periods_planned": 12, "full_planned_cost_rub_cents": 75816000}
        )
        assert act.periods_planned == 12
        assert act.full_planned_cost_rub_cents == 75816000

    def test_fixed_amount_promocode_has_code_but_no_percent(self):
        """A fixed-rouble promocode: the server sends the code and ``null`` for the percent."""
        act = UsageAct.from_dict(
            {**SAMPLE_USAGE_ACT, "promocode_code": "MINUS500", "promocode_discount_value": None}
        )
        assert act.promocode_code == "MINUS500"
        assert act.promocode_discount_value is None

    def test_next_charge_can_differ_from_planned_cost(self):
        """Partially prepaid period: the next charge is what is still held up, not the full price."""
        act = UsageAct.from_dict(
            {**SAMPLE_TERM_USAGE_ACT, "next_charge_rub_cents": 1000000, "full_period_cost_rub_cents": 6318000}
        )
        assert act.next_charge_rub_cents == 1000000
        assert act.full_period_cost_rub_cents == 6318000
        assert act.full_planned_cost_rub_cents == 6318000


class TestUsageActCostFieldsAbsentOrNull:
    def test_absent_fields_do_not_break_old_payloads(self):
        act = UsageAct.from_dict({"id": 1})
        assert act.next_charge_rub_cents == 0
        assert act.full_period_cost_rub_cents == 0
        assert act.full_planned_cost_rub_cents == 0
        assert act.discount_percent == 0
        assert act.promocode_code is None
        assert act.promocode_discount_value is None

    def test_null_numbers_fall_back_to_zero(self):
        act = UsageAct.from_dict(
            {
                "id": 1,
                "next_charge_rub_cents": None,
                "full_period_cost_rub_cents": None,
                "full_planned_cost_rub_cents": None,
                "discount_percent": None,
            }
        )
        assert act.next_charge_rub_cents == 0
        assert act.full_period_cost_rub_cents == 0
        assert act.full_planned_cost_rub_cents == 0
        assert act.discount_percent == 0

    def test_empty_promocode_code_is_none(self):
        assert UsageAct.from_dict({"id": 1, "promocode_code": ""}).promocode_code is None

    def test_zero_discount_is_zero_not_missing(self):
        assert UsageAct.from_dict({"id": 1, "discount_percent": 0}).discount_percent == 0


class TestUsageActFieldsOnCloudServer:
    def test_all_act_slots_carry_the_new_fields(self):
        """The same short serializer feeds four slots on a server; none may drop the fields."""
        server = CloudServer.from_dict(
            {
                **SAMPLE_CLOUD_SERVER,
                "usage_act": SAMPLE_TERM_USAGE_ACT,
                "last_usage_act": SAMPLE_TERM_USAGE_ACT,
                "last_finished_usage_act": SAMPLE_USAGE_ACT,
                "resume_usage_act": SAMPLE_TERM_USAGE_ACT,
            }
        )
        assert server.usage_act.discount_percent == 35
        assert server.last_usage_act.promocode_code == "WELCOME10"
        assert server.last_finished_usage_act.full_planned_cost_rub_cents == 16071
        assert server.resume_usage_act.full_planned_cost_rub_cents == 6318000
