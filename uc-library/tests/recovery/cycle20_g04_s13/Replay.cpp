#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include <iostream>

int main() {
  using Core::Portable::Component;
  using Presonus::MixerClientComponentBase;
  using Presonus::SLChannelBase;
  Component groups("groups"), foreignGroup("line"), unrecognizedGroup("other");
  MixerClientComponentBase receiver(groups);
  auto *ownGroup = new Component("talkback");
  groups.addChild(ownGroup);
  Component wrongType("not-a-channel");
  SLChannelBase loose("loose");
  auto *rootChild = new SLChannelBase("root-child");
  groups.addChild(rootChild);
  auto *own = new SLChannelBase("own");
  ownGroup->addChild(own);
  auto *foreign = new SLChannelBase("foreign");
  foreignGroup.addChild(foreign);
  auto *unknown = new SLChannelBase("unknown");
  unrecognizedGroup.addChild(unknown);

  Component *const cases[]{nullptr, &wrongType, &loose, rootChild,
                           own,     foreign,    unknown};
  unsigned mode = 0;
  while (std::cin >> mode) {
    if (mode >= std::size(cases))
      return 1;
    std::cout << receiver.isChannelComponent(cases[mode]) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
