#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Mixer;
namespace {
bool recording = false;

struct Member : NumericParam {
  Member(const ParamInfo &info, int group) : NumericParam(info), group(group) {}
  void setValue(ParamValue value, bool edit) override {
    if (recording)
      std::cout << "set " << group << ' ' << static_cast<int>(value) << ' '
                << edit << '\n';
    NumericParam::setValue(value, edit);
  }
  int group;
};
struct Label : StringParam {
  Label(const ParamInfo &info, int group) : StringParam(info), group(group) {}
  void fromString(Core::CStringPtr value, bool edit) override {
    if (recording)
      std::cout << "label " << group << ' ' << value << ' ' << edit << '\n';
    StringParam::fromString(value, edit);
  }
  int group;
};
struct Group : Component {
  Group(const char *name, int index) : Component(name), index(index) {}
  void attach(Parameter *param) { paramList.add(param); }
  int index;
};
} // namespace

extern "C" void
__real__ZN4Core8Portable9Component15resetToDefaultsEbbPKNS0_14IStorageFilterE(
    Component *, bool, bool, const IStorageFilter *);
extern "C" void
__wrap__ZN4Core8Portable9Component15resetToDefaultsEbbPKNS0_14IStorageFilterE(
    Component *receiver, bool storableOnly, bool edit,
    const IStorageFilter *filter) {
  const bool previous = recording;
  if (recording)
    std::cout << "reset " << static_cast<Group *>(receiver)->index << ' '
              << storableOnly << ' ' << edit << '\n';
  recording = false;
  __real__ZN4Core8Portable9Component15resetToDefaultsEbbPKNS0_14IStorageFilterE(
      receiver, storableOnly, edit, filter);
  recording = previous;
}

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const char *icon = argv[1];
  const int current = std::stoi(argv[2]);
  const bool hasOther = std::stoi(argv[3]) != 0;
  const bool iconString = std::stoi(argv[4]) != 0;
  const bool labelString = std::stoi(argv[5]) != 0;
  static const ParamInfo memberInfo = PARAM_TOGGLE(648, "member", 0, 0, 0);
  static const ParamInfo otherInfo = PARAM_TOGGLE(649, "other", 0, 0, 0);
  static const ParamInfo labelInfo = PARAM_STRING(600, "label", 0);
  static const ParamInfo wrongLabel = PARAM_TOGGLE(600, "label", 0, 0, 0);
  static const ParamInfo iconInfo = PARAM_STRING(25, "icon", 0);
  static const ParamInfo wrongIcon = PARAM_TOGGLE(25, "icon", 0, 0, 0);

  std::array<std::unique_ptr<Group>, 9> groups;
  AutoFilterGroupManager::AutoGroupingState state;
  ChannelComponent channel(ChannelComponent::SourcePortConstruction{});
  channel.addParameters(iconString ? &iconInfo : &wrongIcon, 1);
  if (iconString)
    channel.getParameterByTag(25)->fromString(icon);
  state.channelOrdinals.emplace_back(&channel, 2);

  for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
    groups[i] =
        std::make_unique<Group>(("Group" + std::to_string(i)).c_str(), i);
    state.groups[i] = groups[i].get();
    auto *member = new Member(memberInfo, i);
    auto *other = new NumericParam(otherInfo);
    member->setValue(i == current, false);
    other->setValue(i == current && hasOther);
    groups[i]->attach(member);
    groups[i]->attach(other);
    if (labelString) {
      auto *label = new Label(labelInfo, i);
      label->setDefaultText("default");
      label->fromString("old", false);
      groups[i]->attach(label);
    } else {
      groups[i]->addParameters(&wrongLabel, 1);
    }
  }
  AutoFilterGroupManager target(
      AutoFilterGroupManager::SourcePortConstruction{});
  target.bindAutoGrouping(state);
  recording = true;
  target.updateAutoGroup(&channel);
  recording = false;

  for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
    const auto &group = *groups[i];
    const auto *label = StringParam::cast(group.getParameterByTag(600));
    std::cout << "group " << i << ' '
              << static_cast<int>(group.getParameterByTag(648)->getValue())
              << ' '
              << static_cast<int>(group.getParameterByTag(649)->getValue())
              << ' ' << (label ? label->getText().str() : "old") << '\n';
  }
}
