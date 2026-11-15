#include "presonus/mixer/MixerComponentBase.hpp"
#include <iostream>
int main() {
  Presonus::Mixer::MixerComponentBase owner;
  owner.selectedChannel = 0xdeadbeef;
  int value;
  while (std::cin >> value) {
    std::cout << owner.shouldCollectFaderChanges(value) << '\n';
    if (owner.selectedChannel != 0xdeadbeef)
      return 1;
  }
}
