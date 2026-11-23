#include "presonus/MeterScaleControl.hpp"
#include <iostream>
#include <string>

int main() {
  using Ranges = Presonus::MeterScaleControl::Ranges;
  Ranges independent(Ranges::SourcePortTag{});
  std::cout << independent.count() << '\n';

  const Ranges *firstRegistry = nullptr;
  for (int invocation = 0; invocation < 2; ++invocation) {
    __initMeterScaleControl();
    const auto &ranges = presonus::meter::sourcePortMeterScaleRanges();
    if (!firstRegistry)
      firstRegistry = &ranges;
    if (firstRegistry != &ranges)
      return 1;
    std::cout << ranges.count() << '\n';
    for (int i = 0; i < ranges.count(); ++i) {
      const auto *range = ranges.at(i);
      std::cout << range->name.str() << ' ' << range->count << ' '
                << (range->values == ranges.at(i % 3)->values);
      for (int j = 0; j < range->count; ++j)
        std::cout << ' ' << range->values[j];
      std::cout << '\n';
      auto &mutableRanges = const_cast<Ranges &>(ranges);
      if (mutableRanges.getRange(range->name.str()) != ranges.at(i % 3))
        return 2;
    }
  }
}
