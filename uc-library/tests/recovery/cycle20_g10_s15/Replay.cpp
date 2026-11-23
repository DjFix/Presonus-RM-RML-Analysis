#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"

#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const bool bound = std::atoi(argv[1]) != 0;
  const bool attached = std::atoi(argv[2]) != 0;
  Core::Portable::Component parent(argv[3]);
  Presonus::MixerClientComponentBase mixer;
  Presonus::SLChannelBase channel("channel");
  if (bound)
    channel.bindSourcePortMixer(&mixer);
  if (attached)
    parent.addChild(&channel);
  const auto result = static_cast<int>(channel.getChannelType());
  if (attached) {
    if (parent.countChildren() != 1 || parent.getChild(0) != &channel)
      return 1;
    parent.removeChild(&channel);
  }
  std::cout << result << '\n';
}
