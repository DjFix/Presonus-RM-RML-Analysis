#include "presonus/MixerClientComponentBase.hpp"
#include <iostream>

int main() {
  using Core::ConstVector;
  using Core::Portable::Component;
  Presonus::MixerClientComponentBase receiver;
  Component first("first"), second("second"), third("third"), fourth("fourth"),
      fifth("fifth"), error("error");
  Component *const identities[] = {nullptr, &first, &second, &third,
                                   &fourth, &fifth, &error};
  auto &fallback = ConstVector<Component *>::getError();
  auto *const previousFallback = fallback;
  fallback = &error;

  int count = 0, argument = 0;
  while (std::cin >> count >> argument) {
    if (count < -1 || count > 5)
      return 1;
    const ConstVector<Component *> roster(identities + 1,
                                          count < 0 ? 0 : count);
    receiver.bindGeqs(count < 0 ? nullptr : &roster);
    if (receiver.getNumGeqs() != (count < 0 ? 0 : count))
      return 2;
    auto *result = receiver.getMainGeq(argument != 0);
    unsigned index = 0;
    while (index < std::size(identities) && identities[index] != result)
      ++index;
    std::cout << index << '\n';
    receiver.bindGeqs(nullptr);
  }
  fallback = previousFallback;
  return std::cin.eof() ? 0 : 1;
}
