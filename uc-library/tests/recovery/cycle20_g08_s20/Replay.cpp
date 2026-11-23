#include "presonus/panel/AlertBook.hpp"
#include "presonus/panel/Book.hpp"

#include <iostream>

using Presonus::Panel::AlertBook;
using presonus::panel::BookInspector;

int main() {
  int input;
  while (std::cin >> input) {
    AlertBook book(input);
    auto *base = book.portableOwnedBook();
    if (!base)
      return 1;
    auto &state = book.portableAlertState();
    auto &parameters = book.portableParameters();
    bool zero = state.mode == 0 && !state.page && !state.selection &&
                state.startedMilliseconds == 0 &&
                BookInspector::count(*base) == 0;
    std::cout << BookInspector::initialValue(*base) << '|'
              << parameters.getName() << '|' << zero;
    for (int i = 0; i < parameters.countParameters(); ++i) {
      auto *param = parameters.getParameterAt(i);
      if (!param || parameters.getParameterByTag(param->getTag()) != param)
        return 1;
      std::cout << '|' << param->getType() << '|' << param->getTag() << '|'
                << param->getName() << '|' << param->getTitle();
    }
    std::cout << '\n';
  }
}
