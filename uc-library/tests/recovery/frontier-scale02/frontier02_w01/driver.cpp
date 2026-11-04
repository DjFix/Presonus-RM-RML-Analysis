#include "presonus/panel/SceneBook.hpp"
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int n = static_cast<int>(std::strtoll(argv[1], nullptr, 10));
  Presonus::Panel::SceneBook b(n);
  using I = presonus::panel::BookInspector;
  std::cout << I::initialValue(b.bookState()) << " "
            << b.opaqueDispatchIdentity() << " " << I::count(b.bookState())
            << " " << I::ownsStorage(b.bookState()) << " "
            << I::zero90(b.bookState()) << " " << I::zero94(b.bookState())
            << " " << (I::storage(b.bookState()) != nullptr) << "\n";
}
