#include "presonus/panel/SystemAboutPage.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <vector>

using Presonus::Panel::Element;
using Presonus::Panel::Page;
using Presonus::Panel::SystemAboutPage;

namespace {
constexpr bool deleting = true;
struct Allocation {
  void *pointer;
  unsigned label;
  bool released;
};
std::array<Allocation, 5> allocations{};
std::array<unsigned, 5> releaseOrder{};
std::array<unsigned, 4> destroyedChildren{};
unsigned releasedCount = 0;
unsigned destroyedCount = 0;

void track(void *p, unsigned label) {
  for (auto &entry : allocations) {
    if (!entry.pointer) {
      entry = {p, label, false};
      return;
    }
  }
  std::abort();
}

struct Child final : Element {
  explicit Child(unsigned label) : label(label) {}
  ~Child() override { destroyedChildren.at(destroyedCount++) = label; }
  static void operator delete(void *p) noexcept { ::operator delete(p); }
  unsigned label;
};
} // namespace

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __wrap__ZdlPv(void *p) noexcept {
  for (auto &entry : allocations) {
    if (p && entry.pointer == p) {
      if (entry.released)
        std::abort();
      entry.released = true;
      releaseOrder.at(releasedCount++) = entry.label;
      break;
    }
  }
  __real__ZdlPv(p);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::vector<std::vector<bool>> layouts{{},
                                               {false},
                                               {true},
                                               {false, true, false, true},
                                               {true, true, false, true}};
  const auto &layout = layouts.at(std::atoi(argv[1]));
  Page::Elements elements;
  for (unsigned index = 0; index < layout.size(); ++index) {
    if (layout[index]) {
      auto child = std::make_unique<Child>(index);
      track(child.get(), index);
      elements.push_back(std::move(child));
    } else {
      elements.push_back(nullptr);
    }
  }
  void *storage = ::operator new(sizeof(SystemAboutPage));
  Page *object = ::new (storage) SystemAboutPage(std::move(elements), nullptr);
  track(object, 99);
  if (deleting)
    delete object;
  else
    static_cast<SystemAboutPage *>(object)->~SystemAboutPage();

  if (releasedCount != destroyedCount + deleting)
    return 1;
  for (unsigned i = 0; i < destroyedCount; ++i)
    if (releaseOrder[i] != destroyedChildren[i])
      return 1;
  if (deleting && releaseOrder[destroyedCount] != 99)
    return 1;
  for (unsigned i = 0; i < releasedCount; ++i)
    std::cout << releaseOrder[i] << ' ';
  std::cout << '\n';

  // Release the complete variant's surviving storage after the observation.
  if (!deleting)
    __real__ZdlPv(object);
}
