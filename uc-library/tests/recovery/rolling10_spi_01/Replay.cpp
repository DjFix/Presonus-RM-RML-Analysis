#include "presonus/panel/SPIControlGroup.hpp"
#include <iostream>
int main() {
  unsigned initial;
  unsigned long long pointer;
  while (std::cin >> initial >> pointer) {
    Presonus::Panel::SPIControlGroup group(7, 9, 0);
    group.markDirty(initial != 0);
    auto *control = reinterpret_cast<Presonus::Panel::Control *>(
        static_cast<std::uintptr_t>(pointer));
    int result = group.broadcast(control);
    std::cout << result << ' ' << group.isDirty() << ' '
              << group.transportDescriptor() << ' ' << group.payloadByteCount()
              << '\n';
  }
}
