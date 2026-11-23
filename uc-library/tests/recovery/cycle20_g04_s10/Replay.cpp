#include "presonus/MixerClientComponentBase.hpp"
#include <iostream>

int main() {
  using Presonus::MixerClientComponentBase;
  MixerClientComponentBase receiver, peerA, peerB;
  MixerClientComponentBase *const identities[] = {nullptr, &peerA, &peerB,
                                                  &receiver};
  unsigned input = 0;
  while (std::cin >> input) {
    if (input >= std::size(identities))
      return 1;
    auto &state = receiver.portableState();
    const auto cascade = input % 3;
    state.masterWord = cascade == 2 ? 0x1357U : 0;
    state.slaveWord = cascade == 1 ? 0x2468U : 0;
    auto *selected = identities[input];
    auto *other = identities[(input + 1) % std::size(identities)];
    state.masterMixer = other;
    state.slaveMixer = other;
    receiver.setMasterMixer(selected);
    if (state.slaveMixer != other)
      return 3;
    auto *result = receiver.getMasterMixer();
    if (receiver.getCascadeState() != cascade)
      return 2;
    unsigned index = 0;
    while (index < std::size(identities) && identities[index] != result)
      ++index;
    std::cout << index << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
