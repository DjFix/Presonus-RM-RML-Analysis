#include "presonus/PageComponent.hpp"

#include <cstdlib>
#include <iostream>

struct Bindings final : presonus::page::Bindings {
  const Presonus::PageComponent *current = nullptr;
  mutable int calls = 0;

  void *castOwner(void *owner, int id) const override {
    if (owner != this || id != 1296843588)
      std::abort();
    ++calls;
    return owner;
  }
  const void *currentPage(void *) const override {
    ++calls;
    return current;
  }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool visible = std::atoi(argv[2]);
  Bindings bindings;
  Presonus::PageComponent page(&bindings, bindings, visible ? "one" : "two");
  page.bindObservedPageState(visible ? 98 : -43, visible ? 27 : 9);
  if (visible)
    bindings.current = &page;
  const auto state = [&] {
    std::cout << page.getPageTag() << ' ' << page.getFormName() << ' '
              << static_cast<int>(page.observedByte89()) << ' '
              << page.isVisible() << ' ';
  };
  state();
  const int start = bindings.calls;
  page.onShow(std::atoi(argv[1]));
  state();
  std::cout << bindings.calls - start - 2 << '\n';
}
