#include "presonus/ChannelGroupFilter.hpp"

#include <iostream>

int main() {
  int length = 0;
  int index = 0;
  bool error = false;
  while (std::cin >> length >> index >> error) {
    Presonus::ChannelGroupFilter filter(length);
    for (int item = 0; item < length; ++item) {
      bool value = false;
      if (!(std::cin >> value))
        return 2;
      filter.setVisible(item, value);
    }
    auto &errorSlot = Core::ConstVector<bool>::getError();
    errorSlot = error;
    const auto &view = filter.sourcePortVisibility();
    const auto &readOnlyFilter = filter;
    const int result = readOnlyFilter.getChannelOffset(index);
    std::cout << result << ' ' << view.getCapacity() << '\n';
    if (errorSlot != error || view.count() != length)
      return 3;
  }
  return std::cin.eof() ? 0 : 4;
}
