#include "presonus/FocusRestorer.hpp"
#include <iostream>
int main() {
  Presonus::FocusRestorer::FocusInfo x;
  for (auto v : x.observedState)
    std::cout << v << ' ';
  std::cout << static_cast<int>(x.name.str()[0]) << '\n';
}
