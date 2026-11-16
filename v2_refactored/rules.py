"""대여 규칙 담당 (Strategy 패턴).

품목 분류마다 '반납 기한 계산', '연체료 계산', '안내 문구'가 다르다.
각 방법을 클래스 하나로 만들고, RULES 표에서 분류 이름으로 골라 쓴다.
새 규칙이 필요하면 이 파일에 클래스와 RULES 한 줄만 추가하면 된다.
"""
from datetime import timedelta


class RentalRule:
    """모든 대여 규칙이 지켜야 하는 공통 모양."""

    def due_date(self, rent_date):
        raise NotImplementedError

    def late_fee(self, late_days):
        raise NotImplementedError

    def describe(self):
        raise NotImplementedError


class StandardRule(RentalRule):
    """일반 물품: 3일 대여, 하루 500원, 연체료는 최대 3000원."""

    def due_date(self, rent_date):
        return rent_date + timedelta(days=3)

    def late_fee(self, late_days):
        return min(late_days * 500, 3000)

    def describe(self):
        return "3일 대여, 연체료 하루 500원(최대 3000원)"


class ElectronicsRule(RentalRule):
    """전자기기: 1일 대여, 하루 1000원, 상한 없음."""

    def due_date(self, rent_date):
        return rent_date + timedelta(days=1)

    def late_fee(self, late_days):
        return late_days * 1000

    def describe(self):
        return "1일 대여, 연체료 하루 1000원"


RULES = {
    "일반": StandardRule(),
    "전자기기": ElectronicsRule(),
}


def get_rule(category):
    """분류 이름에 맞는 규칙 객체를 돌려준다. 없는 분류면 ValueError."""
    if category not in RULES:
        raise ValueError("알 수 없는 분류입니다: " + category)
    return RULES[category]
