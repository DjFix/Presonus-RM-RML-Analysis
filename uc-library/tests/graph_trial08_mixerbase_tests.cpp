#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  int method = std::atoi(argv[1]);
  auto value = static_cast<std::uint32_t>(std::strtoull(argv[2], nullptr, 10));
  Presonus::Mixer::MixerComponentBase m;
  m.selectedChannel = value;
  m.clientCount = value ^ 0x55aa55aaU;
  m.hardwareMicLineInputs = value ^ 0xffffffffU;
  m.tryingToQuit = std::atoi(argv[3]) != 0;
  switch (method) {
  case 1:
    std::cout << m.getSelectedChannel();
    break;
  case 2:
    std::cout << m.numClients();
    break;
  case 3:
    std::cout << m.numHWMicLineIn();
    break;
  case 4:
    std::cout << m.getCompanyName();
    break;
  case 5:
    std::cout << m.getSpectrumSendSlot();
    break;
  case 6:
    m.setTryingToQuit();
    std::cout << m.tryingToQuit;
    break;
  default:
    return 2;
  }
  std::cout << '\n'
            << m.getSelectedChannel() << ' ' << m.numClients() << ' '
            << m.numHWMicLineIn() << ' ' << m.tryingToQuit << '\n';
}
