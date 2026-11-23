#include "presonus/panel/Page.hpp"

#include <array>
#include <iostream>
#include <string_view>
#include <utility>

using Presonus::Panel::Element;
using Presonus::Panel::Page;

namespace {
void *receiver;
std::array<void *, 8> children;
std::array<int, 16> events;
std::size_t count;

void logDelete(void *address, bool unsized) {
  if (address == receiver) {
    events.at(count++) = unsized ? 90 : 91;
    receiver = nullptr;
  }
  for (std::size_t index = 0; index < children.size(); ++index) {
    if (address == children[index] && address) {
      events.at(count++) = 10 + static_cast<int>(index);
      children[index] = nullptr;
    }
  }
}

void destroyPage(Page *page) { delete page; }

// Retain virtual deletion even when the fixture knows the exact dynamic type.
void (*volatile deleteThroughPage)(Page *) = destroyPage;

struct DerivedPage final : Page {
  using Page::Page;
};
} // namespace

extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;

extern "C" void __wrap__ZdlPv(void *address) noexcept {
  logDelete(address, true);
  __real__ZdlPv(address);
}

extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) noexcept {
  logDelete(address, false);
  __real__ZdlPvm(address, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view slots = argv[2];
  if (slots.size() > children.size())
    return 2;

  Page::Elements elements;
  for (std::size_t index = 0; index < slots.size(); ++index) {
    if (slots[index] == '1') {
      auto child = std::make_unique<Element>();
      children[index] = child.get();
      elements.push_back(std::move(child));
    } else if (slots[index] == '0') {
      elements.push_back(nullptr);
    } else {
      return 2;
    }
  }

  const int variant = argv[1][0] - '0';
  bool enabled = false;
  if (variant == 0) {
    auto *page = new Page(std::move(elements));
    receiver = page;
    enabled = page->isEnabled();
    deleteThroughPage(page);
  } else if (variant == 1) {
    Page page(std::move(elements));
    receiver = &page;
    enabled = page.isEnabled();
  } else if (variant == 2) {
    DerivedPage page(std::move(elements));
    receiver = static_cast<Page *>(&page);
    enabled = page.isEnabled();
  } else {
    return 2;
  }

  receiver = nullptr;
  std::cout << enabled;
  for (std::size_t index = 0; index < count; ++index)
    std::cout << ' ' << events[index];
  std::cout << '\n';
}
