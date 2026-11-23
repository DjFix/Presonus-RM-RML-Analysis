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

  TextEntryElement::setEncoderParam(first);
  unsigned cursor;
  bool dirty;
  while (std::cin >> cursor >> dirty) {
    state.cursor = cursor;
    state.dirty = dirty;
    const auto moved = element.previous();
    if (element.getParam() != first || otherState.cursor || otherState.dirty)
      return 3;
    std::cout << moved << ' ' << state.cursor << ' ' << state.dirty << '\n';
  }

  TextEntryElement::setEncoderParam(nullptr);
  if (element.getParam() || first->getValue() != 3 || second->getValue() != 7)
    return 5;
}
