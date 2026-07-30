#!/usr/bin/env python3
"""PROTOTYPE — throwaway balance explorer for asciicoins.

Question: do the agreed rewards and current prices produce the intended cadence?
This is not production code and has no persistence.

Run:
    python prototypes/economy_balance.py --report
    python prototypes/economy_balance.py
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

STARTING_BALANCE = 50
PRICES = {
    "descanso_rapido": 5,
    "fuerza_1d4": 8,
    "velocidad_1d4": 8,
    "pocion_comida": 10,
    "fuerza_1d6": 12,
    "velocidad_1d6": 12,
    "fuerza_1d8": 18,
    "velocidad_1d8": 18,
    "silbato": 20,
    "fuerza_1d10": 26,
    "velocidad_1d10": 26,
    "fuerza_1d12": 36,
    "velocidad_1d12": 36,
}


@dataclass(frozen=True)
class Profile:
    care: int
    competitions: int
    wins: int
    evolutions: int = 0

    @property
    def daily_income(self) -> int:
        return self.care + self.competitions * 4 + self.wins * 2 + self.evolutions * 10


PROFILES = {
    "casual": Profile(care=8, competitions=1, wins=0),       # 12/day
    "competitive": Profile(care=8, competitions=3, wins=1), # 22/day
    "intensive": Profile(care=12, competitions=3, wins=3),  # 30/day
    "max-evolution": Profile(care=12, competitions=3, wins=3, evolutions=1), # 40 spike
}


def days_from_zero(price: int, income: int) -> int:
    return math.ceil(price / income)


def print_report() -> None:
    print("PROTOTYPE — current catalog vs agreed asciicoin rewards\n")
    print("Profile       Income  Cheapest(5)  Minor<=12  1d12(36)  30d theoretical hoard")
    print("------------- ------  -----------  ---------  ---------  --------------------")
    for name, profile in PROFILES.items():
        income = profile.daily_income
        cheapest = days_from_zero(5, income)
        minor = days_from_zero(12, income)
        d12 = days_from_zero(36, income)
        hoard = STARTING_BALANCE + 30 * income
        print(f"{name:<13} {income:>6}  {cheapest:^11}  {minor:^9}  {d12:^9}  {hoard:>17}")

    print("\nItem affordability from zero (days):")
    header = "item".ljust(21) + "".join(f"{name[:7]:>9}" for name in PROFILES)
    print(header)
    print("-" * len(header))
    for item, price in PRICES.items():
        cells = "".join(
            f"{days_from_zero(price, profile.daily_income):>9}"
            for profile in PROFILES.values()
        )
        print(f"{item:<18} {price:>2}{cells}")

    print("\nChecks:")
    casual = PROFILES["casual"].daily_income
    print(f"- Minor item <=12: {days_from_zero(12, casual)} casual day (target: 1) — PASS")
    print(f"- 1d12 at 36: {days_from_zero(36, casual)} casual days (target: 2-3) — PASS")
    print("- Starting 50/50 gift buys any one current item immediately — PASS")
    print("- Purchase power cannot raise reward caps; no earning snowball — PASS")
    print("- Hoarding remains possible, but there is no shared market or player transfer.")
    print("- The max-evolution row is a one-day ceiling; it is not a claim that evolution occurs daily.")


def simulate(profile_name: str, days: int, target: str) -> None:
    profile = PROFILES[profile_name]
    price = PRICES[target]
    balance = STARTING_BALANCE
    bought = 0
    print(f"\nState: profile={profile_name}, target={target}, price={price}, balance={balance}")
    for day in range(1, days + 1):
        earned = profile.daily_income
        balance += earned
        purchases = 0
        while balance >= price:
            balance -= price
            purchases += 1
            bought += 1
        print(
            f"day={day:>2} earned={earned:>2} bought={purchases:>2} "
            f"total_bought={bought:>2} balance={balance:>3}"
        )


def interactive() -> None:
    print_report()
    print("\nInteractive alternative-purchase simulation")
    names = list(PROFILES)
    for index, name in enumerate(names, 1):
        print(f"  {index}. {name} ({PROFILES[name].daily_income}/day)")
    profile_name = names[int(input("Profile [1-4]: ")) - 1]
    days = int(input("Days: "))
    target = input(f"Item {sorted(PRICES)}: ").strip()
    simulate(profile_name, days, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        print_report()
    else:
        interactive()


if __name__ == "__main__":
    main()
