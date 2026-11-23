#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include <cstring>
#include <iostream>

int main() {
  using Core::Portable::Component;
  using Presonus::MixerClientComponentBase;
  using Presonus::SLChannelBase;
  Component emptyGroups;
  Component mixer("Mixer"), root("Group");
  auto *first = new SLChannelBase("Channel 1");
  mixer.addChild(first);
  auto *sub = new Component("Sub");
  auto *second = new SLChannelBase("Selected");
  root.addChild(sub);
  sub->addChild(second);
  SLChannelBase *const selected[] = {nullptr, first, second};

  const auto printBytes = [](Core::CStringBuffer<256> &buffer) {
    constexpr char hex[] = "0123456789abcdef";
    for (int i = 0; i < buffer.getSize(); ++i) {
      const auto byte = static_cast<unsigned char>(buffer.getBuffer()[i]);
      std::cout << hex[byte >> 4] << hex[byte & 15];
    }
  };
  int type = 0;
  unsigned path = 0;
  while (std::cin >> type >> path) {
    if (path >= std::size(selected))
      return 1;
    MixerClientComponentBase receiver(emptyGroups, selected[path]);
    Core::CStringBuffer<256> target;
    std::memset(target.getBuffer(), 0x7d, 256);
    receiver.getRemotePresetTarget(
        static_cast<Presonus::IPresetHandler::PresetType>(type), target);
    printBytes(target);
    if (type == Presonus::IPresetHandler::Channel && selected[path]) {
      Core::CStringBuffer<256> providerOutput;
      std::memset(providerOutput.getBuffer(), 0x7d, 256);
      selected[path]->getComponentPath(providerOutput);
      std::cout << ' ';
      printBytes(providerOutput);
    }
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
