#include "presonus/surface_panel/MeterControl.hpp"

#include <iostream>

int main() {
  Presonus::Panel::MeterControl first;
  Presonus::Panel::MeterControl second;
  int count = 7;
  using presonus::surface_panel_port::MeterControlAccess;
  MeterControlAccess::setState(second, &count, 1);

  int classId;
  while (std::cin >> classId) {
    for (auto *receiver : {&first, &second}) {
      const void *result = receiver->castTo(classId);
      if (result != nullptr && result != receiver)
        return 1;
      std::cout << (result == receiver) << ' ';
    }
    if (MeterControlAccess::direction(first) != 0 ||
        MeterControlAccess::direction(second) != 1 ||
        second.getNumMeterSteps(Presonus::Panel::MeterControl::BusDirection{},
                                false) != 7)
      return 1;
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
