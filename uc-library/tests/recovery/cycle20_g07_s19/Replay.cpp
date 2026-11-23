#include "core/portable/coreparams.h"
#include "presonus/panel/Book.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Presonus::Panel::Book;
using presonus::panel::BookInspector;
using Presonus::Panel::Element;
using Presonus::Panel::Page;
using Presonus::Panel::TextEntryElement;
using presonus::panel::portable::TextEntryState;

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const std::string_view selection(argv[1]), slots(argv[3]);
  const bool present = std::string_view(argv[2]) == "1";
  ParamInfo info{};
  NumericParam parameter(info);
  TextEntryState state;
  TextEntryElement textEntry(state);
  Page::TextEntrySelection textElement(textEntry);
  Element base;
  Page page;
  if (selection == "Element")
    page.activeElement(&base);
  else if (selection == "TextEntryElement")
    page.activeElement(&textElement);
  else if (selection != "none")
    return 2;

  Book book(0);
  for (const char slot : slots)
    book.add(slot == '1' ? &page : nullptr);
  BookInspector::setActivePosition(book, std::atoi(argv[4]));
  auto &error = Core::ConstVector<Page *>::getError();
  if (error)
    return 1;
  error = std::string_view(argv[5]) == "1" ? &page : nullptr;
  TextEntryElement::setEncoderParam(present ? &parameter : nullptr);
  const Book &receiver = book;
  const auto *found = receiver.getActiveParam();
  error = nullptr;
  TextEntryElement::setEncoderParam(nullptr);
  if (found && found != &parameter)
    return 1;
  std::cout << (found ? 1 : 0) << '\n';
}
