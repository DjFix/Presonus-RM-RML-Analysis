#include "presonus/panel/RoguePanelRegistrar.hpp"

#include <array>
#include <cstring>
#include <iostream>

int main() {
  for (unsigned index = 0; index < 3; ++index) {
    Presonus::Panel::RoguePanelRegistrar receiver{};
    std::array<unsigned char, sizeof(receiver)> before{};
    std::memcpy(before.data(), &receiver, before.size());
    int count = 0;
    const auto *tags = receiver.getTags(20, count);
    if (tags == nullptr || count != 16)
      return 1;
    receiver.muteCS1TrafficForNOAAArmUpdate();
    const bool unchanged =
        std::memcmp(before.data(), &receiver, before.size()) == 0;
    const auto *after = receiver.getTags(20, count);
    if (tags != after || count != 16 || after[0] != 8 || after[15] != 7)
      return 1;
    std::cout << "case " << index << ' ' << unchanged << '\n';
  }
}
