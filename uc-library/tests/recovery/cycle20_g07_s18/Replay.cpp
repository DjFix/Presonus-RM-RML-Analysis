#include "core/portable/coreparams.h"
#include "presonus/panel/Page.hpp"

#include <iostream>
#include <string_view>

using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Presonus::Panel::Element;
using Presonus::Panel::Page;
using Presonus::Panel::TextEntryElement;
using presonus::panel::portable::TextEntryState;

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view selection(argv[1]);
  const bool present = std::string_view(argv[2]) == "1";
  ParamInfo info{};
  NumericParam parameter(info);
  TextEntryState state;
  TextEntryElement textEntry(state);
  Page::TextEntrySelection textElement(textEntry);
  Element base;
  Page page;
  if (selection == "Element") {
    if (base.getParam() != 0)
      return 1;
    page.activeElement(&base);
  } else if (selection == "TextEntryElement") {
    page.activeElement(&textElement);
  } else if (selection != "none") {
    return 2;
  }
  TextEntryElement::setEncoderParam(present ? &parameter : nullptr);
  const Page &receiver = page;
  const auto *found = receiver.getActiveParam();
  TextEntryElement::setEncoderParam(nullptr);
  if (found && found != &parameter)
    return 1;
  std::cout << (found ? 1 : 0) << '\n';
}
