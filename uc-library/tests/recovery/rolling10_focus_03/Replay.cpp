#include "presonus/FocusRestorer.hpp"
#include <iostream>
int main() {
  int cases[][6] = {
      {5, 7, 30, 40, 0, 0}, {0, 0, 0, 0, 0, 0}, {10, 20, 90, 100, 30, 40}};
  for (auto &c : cases) {
    Core::Portable::View parent(Core::Rect(c[4], c[5], c[4] + 500, c[5] + 500));
    Core::Portable::View view(Core::Rect(c[0], c[1], c[0] + c[2], c[1] + c[3]));
    view.setParent(&parent);
    view.setName("focus");
    Presonus::FocusRestorer::FocusInfo info;
    info.setView(view);
    for (auto v : info.observedState)
      std::cout << v << ' ';
    std::cout << info.name.str() << '\n';
    view.setParent(nullptr);
  }
}
