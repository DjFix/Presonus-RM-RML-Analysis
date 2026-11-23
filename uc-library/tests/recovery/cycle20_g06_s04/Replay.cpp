#include "core/portable/corecomponent.h"
#include "presonus/panel/TextEntryElement.hpp"

#include <iostream>

using Core::Portable::Component;
using Core::Portable::ParamInfo;
using Presonus::Panel::TextEntryElement;

int main() {
  constexpr ParamInfo infos[] = {
      PARAM_INT_(191, "first", 0, 12, 3, "", "", 0, 0, "", nullptr),
      PARAM_INT_(192, "second", 0, 12, 7, "", "", 0, 0, "", nullptr),
  };
  Component tree("TextEntryFixture");
  tree.addParameters(infos, 2);
  auto *first = tree.getParameterByTag(191);
  auto *second = tree.getParameterByTag(192);
  if (!first || !second || first == second)
    return 1;

  presonus::panel::portable::TextEntryState state;
  presonus::panel::portable::TextEntryState otherState;
  TextEntryElement element(state);
  TextEntryElement other(otherState);
  if (element.getParam() || other.getParam())
    return 2;

  unsigned index;
  Core::Portable::Parameter *parameters[] = {nullptr, first, second};
  while (std::cin >> index) {
    if (index > 2)
      return 3;
    TextEntryElement::setEncoderParam(parameters[index]);
    auto *observed = element.getParam();
    if (observed != other.getParam() ||
        (observed && observed != first && observed != second))
      return 4;
    std::cout << (observed == nullptr ? 0 : (observed == first ? 1 : 2))
              << '\n';
  }

  TextEntryElement::setEncoderParam(nullptr);
  if (element.getParam() || first->getValue() != 3 || second->getValue() != 7)
    return 5;
}
