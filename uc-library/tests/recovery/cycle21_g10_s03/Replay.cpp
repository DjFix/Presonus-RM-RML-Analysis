#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Mixer;
namespace {
struct Child : Component {
  explicit Child(AutoFilterGroupManager &owner) : owner(owner) {}
  void onIdle() override {
    std::cout << "base " << owner.portableUpdateChannels().count() << '\n';
  }
  AutoFilterGroupManager &owner;
};
struct Member : NumericParam {
  Member(const ParamInfo &info, AutoFilterGroupManager &owner)
      : NumericParam(info), owner(owner) {}
  void setValue(ParamValue value, bool edit) override {
    if (value == 1.f)
      std::cout << "update " << getTag() - 646 << ' '
                << owner.portableUpdateChannels().count() << '\n';
    NumericParam::setValue(value, edit);
  }
  AutoFilterGroupManager &owner;
};
struct Group : Component {
  Group() : Component("Group0") {}
  void attach(Parameter *value) { paramList.add(value); }
};
} // namespace

int main(int argc, char **argv) {
  static const ParamInfo iconInfo = PARAM_STRING(25, "icon", 0);
  static const ParamInfo memberInfo[] = {PARAM_TOGGLE(647, "member1", 0, 0, 0),
                                         PARAM_TOGGLE(648, "member2", 0, 0, 0),
                                         PARAM_TOGGLE(649, "member3", 0, 0, 0)};
  std::array<std::unique_ptr<ChannelComponent>, 3> channels;
  AutoFilterGroupManager::AutoGroupingState state;
  AutoFilterGroupManager target(
      AutoFilterGroupManager::SourcePortConstruction{});
  Group group;
  state.groups[0] = &group;
  for (int i = 0; i < static_cast<int>(channels.size()); ++i) {
    channels[i] = std::make_unique<ChannelComponent>(
        ChannelComponent::SourcePortConstruction{});
    channels[i]->addParameters(&iconInfo, 1);
    channels[i]->getParameterByTag(25)->fromString("drum/tom");
    state.channelOrdinals.emplace_back(channels[i].get(), i + 1);
    group.attach(new Member(memberInfo[i], target));
  }
  target.bindAutoGrouping(state);
  target.addChild(new Child(target));
  for (int i = 1; i < argc; ++i) {
    const int nr = std::stoi(argv[i]);
    target.addUpdateChannel(nr ? channels.at(nr - 1).get() : nullptr);
  }
  target.onIdle();
  std::cout << "remaining";
  const auto &remaining = target.portableUpdateChannels();
  for (int i = 0; i < remaining.count(); ++i) {
    int id = 0;
    for (int j = 0; j < static_cast<int>(channels.size()); ++j)
      if (channels[j].get() == remaining[i])
        id = j + 1;
    std::cout << ' ' << id;
  }
  std::cout << '\n';
}
