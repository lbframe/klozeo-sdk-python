"""Filter builder for the Klozeo SDK.

Filters follow the format: ``logic.operator.field.value``

Usage::

    from klozeo import city, rating, tags, location, attr, or_

    city().eq("Berlin")                                 # and.eq.city.Berlin
    rating().gte(4.0)                                   # and.gte.rating.4.0
    tags().contains("vip")                              # and.array_contains.tags.vip
    location().within_radius(52.52, 13.405, 50)         # and.within_radius.location.52.52,13.405,50
    attr("industry").eq("Software")                     # and.eq.attr:industry.Software
    or_().city().eq("Paris")                            # or.eq.city.Paris
"""

from __future__ import annotations


class Filter:
    """A resolved filter expression ready to be serialised to a query parameter.

    Call :meth:`to_param` to get the ``logic.operator.field.value`` string that
    is passed as a ``filter=`` query parameter.
    """

    def __init__(self, logic: str, operator: str, field: str, value: str = "") -> None:
        self._logic = logic
        self._operator = operator
        self._field = field
        self._value = value

    def to_param(self) -> str:
        """Serialise to a ``filter=`` query-parameter value.

        Returns:
            A string in the format ``logic.operator.field[.value]``.
        """
        if self._value:
            return f"{self._logic}.{self._operator}.{self._field}.{self._value}"
        return f"{self._logic}.{self._operator}.{self._field}"

    def __repr__(self) -> str:
        return f"Filter({self.to_param()!r})"


# ---------------------------------------------------------------------------
# Field builders — returned by the public factory functions
# ---------------------------------------------------------------------------


class _TextField:
    """Filter builder for text-type lead fields."""

    def __init__(self, field: str, logic: str) -> None:
        self._field = field
        self._logic = logic

    def eq(self, value: str) -> Filter:
        """Equals (case-insensitive).

        Args:
            value: The value to match.
        """
        return Filter(self._logic, "eq", self._field, value)

    def neq(self, value: str) -> Filter:
        """Not equals.

        Args:
            value: The value to exclude.
        """
        return Filter(self._logic, "neq", self._field, value)

    def contains(self, value: str) -> Filter:
        """Contains substring.

        Args:
            value: The substring to search for.
        """
        return Filter(self._logic, "contains", self._field, value)

    def not_contains(self, value: str) -> Filter:
        """Does not contain substring.

        Args:
            value: The substring to exclude.
        """
        return Filter(self._logic, "not_contains", self._field, value)

    def is_empty(self) -> Filter:
        """Is null or empty string."""
        return Filter(self._logic, "is_empty", self._field)

    def is_not_empty(self) -> Filter:
        """Has a non-empty value."""
        return Filter(self._logic, "is_not_empty", self._field)


class _NumberField:
    """Filter builder for numeric lead fields."""

    def __init__(self, field: str, logic: str) -> None:
        self._field = field
        self._logic = logic

    def eq(self, value: float | int) -> Filter:
        """Equals.

        Args:
            value: The numeric value to match.
        """
        return Filter(self._logic, "eq", self._field, str(value))

    def neq(self, value: float | int) -> Filter:
        """Not equals.

        Args:
            value: The numeric value to exclude.
        """
        return Filter(self._logic, "neq", self._field, str(value))

    def gt(self, value: float | int) -> Filter:
        """Greater than.

        Args:
            value: Lower bound (exclusive).
        """
        return Filter(self._logic, "gt", self._field, str(value))

    def gte(self, value: float | int) -> Filter:
        """Greater than or equal.

        Args:
            value: Lower bound (inclusive).
        """
        return Filter(self._logic, "gte", self._field, str(value))

    def lt(self, value: float | int) -> Filter:
        """Less than.

        Args:
            value: Upper bound (exclusive).
        """
        return Filter(self._logic, "lt", self._field, str(value))

    def lte(self, value: float | int) -> Filter:
        """Less than or equal.

        Args:
            value: Upper bound (inclusive).
        """
        return Filter(self._logic, "lte", self._field, str(value))


class _TagsField:
    """Filter builder for the ``tags`` array field."""

    def __init__(self, logic: str) -> None:
        self._logic = logic

    def contains(self, value: str) -> Filter:
        """Array contains the given tag.

        Args:
            value: Tag value to search for.
        """
        return Filter(self._logic, "array_contains", "tags", value)

    def not_contains(self, value: str) -> Filter:
        """Array does not contain the given tag.

        Args:
            value: Tag value to exclude.
        """
        return Filter(self._logic, "array_not_contains", "tags", value)

    def is_empty(self) -> Filter:
        """Tags array is empty."""
        return Filter(self._logic, "array_empty", "tags")

    def is_not_empty(self) -> Filter:
        """Tags array has at least one item."""
        return Filter(self._logic, "array_not_empty", "tags")


class _LocationField:
    """Filter builder for the ``location`` field (latitude + longitude pair)."""

    def __init__(self, logic: str) -> None:
        self._logic = logic

    def within_radius(self, lat: float, lng: float, km: float) -> Filter:
        """Within a given radius in kilometres.

        Args:
            lat: Latitude of the centre point.
            lng: Longitude of the centre point.
            km: Radius in kilometres.
        """
        return Filter(self._logic, "within_radius", "location", f"{lat},{lng},{km}")

    def is_set(self) -> Filter:
        """Has geographic coordinates (latitude + longitude)."""
        return Filter(self._logic, "is_set", "location")

    def is_not_set(self) -> Filter:
        """Missing geographic coordinates."""
        return Filter(self._logic, "is_not_set", "location")


class _AttrField:
    """Filter builder for custom (dynamic) attributes.

    The field name in the query is ``attr:<name>``.
    """

    def __init__(self, name: str, logic: str) -> None:
        self._field = f"attr:{name}"
        self._logic = logic

    def eq(self, value: str) -> Filter:
        """Text equals.

        Args:
            value: Value to match.
        """
        return Filter(self._logic, "eq", self._field, value)

    def neq(self, value: str) -> Filter:
        """Text not equals.

        Args:
            value: Value to exclude.
        """
        return Filter(self._logic, "neq", self._field, value)

    def contains(self, value: str) -> Filter:
        """Text contains.

        Args:
            value: Substring to search for.
        """
        return Filter(self._logic, "contains", self._field, value)

    def eq_number(self, value: float | int) -> Filter:
        """Number equals.

        Args:
            value: Numeric value to match.
        """
        return Filter(self._logic, "eq", self._field, str(value))

    def gt(self, value: float | int) -> Filter:
        """Number greater than.

        Args:
            value: Lower bound (exclusive).
        """
        return Filter(self._logic, "gt", self._field, str(value))

    def gte(self, value: float | int) -> Filter:
        """Number greater than or equal.

        Args:
            value: Lower bound (inclusive).
        """
        return Filter(self._logic, "gte", self._field, str(value))

    def lt(self, value: float | int) -> Filter:
        """Number less than.

        Args:
            value: Upper bound (exclusive).
        """
        return Filter(self._logic, "lt", self._field, str(value))

    def lte(self, value: float | int) -> Filter:
        """Number less than or equal.

        Args:
            value: Upper bound (inclusive).
        """
        return Filter(self._logic, "lte", self._field, str(value))


# ---------------------------------------------------------------------------
# OR logic proxy — delegates all field factories with logic="or"
# ---------------------------------------------------------------------------


class _OrProxy:
    """Entry point for OR-logic filters.

    Chain a field factory method immediately after ``or_()``:

    Example::

        or_().city().eq("Paris")    # → or.eq.city.Paris
        or_().rating().gte(4.0)     # → or.gte.rating.4.0
    """

    _logic = "or"

    def city(self) -> _TextField:
        """OR filter on the ``city`` field."""
        return _TextField("city", self._logic)

    def name(self) -> _TextField:
        """OR filter on the ``name`` field."""
        return _TextField("name", self._logic)

    def country(self) -> _TextField:
        """OR filter on the ``country`` field."""
        return _TextField("country", self._logic)

    def state(self) -> _TextField:
        """OR filter on the ``state`` field."""
        return _TextField("state", self._logic)

    def category(self) -> _TextField:
        """OR filter on the ``category`` field."""
        return _TextField("category", self._logic)

    def source(self) -> _TextField:
        """OR filter on the ``source`` field."""
        return _TextField("source", self._logic)

    def email(self) -> _TextField:
        """OR filter on the ``email`` field."""
        return _TextField("email", self._logic)

    def phone(self) -> _TextField:
        """OR filter on the ``phone`` field."""
        return _TextField("phone", self._logic)

    def website(self) -> _TextField:
        """OR filter on the ``website`` field."""
        return _TextField("website", self._logic)

    def rating(self) -> _NumberField:
        """OR filter on the ``rating`` field."""
        return _NumberField("rating", self._logic)

    def review_count(self) -> _NumberField:
        """OR filter on the ``review_count`` field."""
        return _NumberField("review_count", self._logic)

    def tags(self) -> _TagsField:
        """OR filter on the ``tags`` array field."""
        return _TagsField(self._logic)

    def location(self) -> _LocationField:
        """OR filter on the ``location`` field."""
        return _LocationField(self._logic)

    def attr(self, name: str) -> _AttrField:
        """OR filter on a custom attribute.

        Args:
            name: Attribute name (e.g. ``"industry"``).
        """
        return _AttrField(name, self._logic)


# ---------------------------------------------------------------------------
# Public AND-logic factory functions
# ---------------------------------------------------------------------------


def city() -> _TextField:
    """AND filter on the ``city`` text field.

    Example::

        city().eq("Berlin")
        city().contains("York")
    """
    return _TextField("city", "and")


def name() -> _TextField:
    """AND filter on the ``name`` text field.

    Example::

        name().contains("Tech")
        name().eq("Acme Corporation")
    """
    return _TextField("name", "and")


def country() -> _TextField:
    """AND filter on the ``country`` text field.

    Example::

        country().eq("USA")
        country().neq("Spain")
    """
    return _TextField("country", "and")


def state() -> _TextField:
    """AND filter on the ``state`` text field.

    Example::

        state().eq("CA")
    """
    return _TextField("state", "and")


def category() -> _TextField:
    """AND filter on the ``category`` text field.

    Example::

        category().eq("Technology")
    """
    return _TextField("category", "and")


def source() -> _TextField:
    """AND filter on the ``source`` text field.

    Example::

        source().eq("website")
    """
    return _TextField("source", "and")


def email() -> _TextField:
    """AND filter on the ``email`` text field.

    Example::

        email().is_not_empty()
        email().contains("@gmail.com")
    """
    return _TextField("email", "and")


def phone() -> _TextField:
    """AND filter on the ``phone`` text field.

    Example::

        phone().is_not_empty()
    """
    return _TextField("phone", "and")


def website() -> _TextField:
    """AND filter on the ``website`` text field.

    Example::

        website().is_not_empty()
        website().contains("acme.com")
    """
    return _TextField("website", "and")


def rating() -> _NumberField:
    """AND filter on the ``rating`` numeric field.

    Example::

        rating().gte(4.0)
        rating().lt(3.0)
    """
    return _NumberField("rating", "and")


def review_count() -> _NumberField:
    """AND filter on the ``review_count`` numeric field.

    Example::

        review_count().gt(100)
    """
    return _NumberField("review_count", "and")


def tags() -> _TagsField:
    """AND filter on the ``tags`` array field.

    Example::

        tags().contains("enterprise")
        tags().is_not_empty()
    """
    return _TagsField("and")


def location() -> _LocationField:
    """AND filter on the ``location`` (lat/lng) field.

    Example::

        location().within_radius(52.52, 13.405, 50)
        location().is_set()
    """
    return _LocationField("and")


def attr(name: str) -> _AttrField:
    """AND filter on a custom dynamic attribute.

    Args:
        name: Attribute name (e.g. ``"industry"``).

    Example::

        attr("industry").eq("Software")
        attr("employees").gte(100)
    """
    return _AttrField(name, "and")


def or_() -> _OrProxy:
    """Switch to OR logic for the next filter.

    Chain a field factory immediately after::

        or_().city().eq("Paris")    # → or.eq.city.Paris
        or_().rating().gte(4.0)     # → or.gte.rating.4.0

    Returns:
        An :class:`_OrProxy` that exposes the same field factories with OR logic.
    """
    return _OrProxy()


def attr_sort_field(name: str) -> str:
    """Return a sort-field string for a custom attribute.

    Args:
        name: Attribute name (e.g. ``"employees"``).

    Returns:
        A string like ``"attr:employees"`` suitable for the ``sort_by`` parameter.

    Example::

        result = client.list(sort_by=attr_sort_field("employees"), sort_order=SortOrder.DESC)
    """
    return f"attr:{name}"
