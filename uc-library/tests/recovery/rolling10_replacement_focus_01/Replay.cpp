#include "presonus/FocusRestorer.hpp"
#include <cstring>
#include <iostream>
int main() {
  Core::Portable::View view(Core::Rect(5, 7, 35, 47));
  Core::Portable::View parent(Core::Rect(2, 9, 102, 109));
  view.setParent(&parent);
  view.wantsFocus(true);
  view.setName("focus");
  for (int i = 0; i < 11; ++i) {
    Presonus::FocusRestorer::FocusInfo info;
    info.observedState = {1449747831U, 0, 0, 30, 40, 12, 23};
    info.name = "focus";
    view.wantsFocus(i != 2);
    view.setName(i == 10 ? "other" : "focus");
    if (i == 3)
      info.observedState[0] = 0;
    if (i >= 4 && i <= 7)
      info.observedState[i - 3] = 99;
    if (i >= 8 && i <= 9)
      info.observedState[i - 3] = 99;
    Presonus::FocusRestorer::FindFilter filter(info);
    std::cout << filter.matches(i == 1 ? nullptr : &view) << ' ';
  }
  view.setParent(nullptr);
  std::cout << '\n';
}
