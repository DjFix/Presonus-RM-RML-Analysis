#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/DAWDeviceSlot.hpp"
#include "presonus/surface/DawFxPageComponent.hpp"

#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {
using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::DAWDeviceFolder;
using Presonus::DAWDeviceSlot;
using Presonus::Surface::DawFxPageComponent;

constexpr int absent = -999;

Parameter *addParameter(Component &component, const char *name, int tag,
                        float value) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = tag;
  std::strcpy(info.name, name);
  info.minValue = -32;
  info.maxValue = 32;
  info.defaultValue = value;
  component.addParameters(&info, 1, true);
  return component.getParameterByTag(tag);
}
} // namespace

int main() {
  bool scroll, useFolder;
  int used, slot, send, insertOffset, sendOffset, size;
  std::string name;
  while (std::cin >> scroll >> useFolder >> name >> used >> slot >> send >>
         insertOffset >> sendOffset >> size) {
    Component modeOwner;
    auto *mode =
        send == absent ? nullptr : addParameter(modeOwner, "mode", 0, send);
    DAWDeviceFolder folder;
    folder.setName(name.c_str());
    std::vector<DAWDeviceSlot *> children;
    std::vector<int> values;
    for (int i = 0; i < size; ++i) {
      int value;
      if (!(std::cin >> value))
        return 1;
      values.push_back(value);
      auto *child = new DAWDeviceSlot;
      folder.addChild(child);
      children.push_back(child);
      if (value != absent)
        addParameter(*child, "tag-only", 1, value / 2.f);
    }
    if (used != absent) {
      addParameter(folder, "used", 0, used);
      folder.init();
    }
    DAWDeviceSlot foreign;
    auto *selected = slot >= 0    ? children.at(slot)
                     : slot == -1 ? &foreign
                                  : nullptr;
    auto *inputFolder = useFolder ? &folder : nullptr;
    DawFxPageComponent page(mode, {}, insertOffset, sendOffset);
    const int offsetBefore = page.getListOffset();
    const int usedBefore = folder.getUsedCount();
    const int result = scroll ? page.calcAutoScroll(inputFolder, selected)
                              : page.getEditSlotIndex(inputFolder);
    if (page.getListOffset() != offsetBefore ||
        folder.getUsedCount() != usedBefore || folder.countChildren() != size)
      return 1;
    for (int i = 0; i < size; ++i) {
      auto *parameter = children[i]->getParameterByTag(1);
      if (folder.getChild(i) != children[i] ||
          (values[i] == absent
               ? parameter != nullptr
               : !parameter || parameter->getValue() != values[i] / 2.f))
        return 1;
    }
    std::cout << result << '\n';
  }
  return !std::cin.eof();
}
