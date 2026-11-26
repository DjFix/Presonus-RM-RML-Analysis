#include "core/portable/coreattributes.h"
#include "presonus/IDAWDialogHandler.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

using Menu = Presonus::IDAWDialogHandler::DialogMenu;
using Core::Portable::AttributeAllocator;
using Core::Portable::AttributeQueue;
using Core::Portable::DefaultAllocatedAttributes;

namespace {

const void *tracked[16]{};
int trackedCount = 0;
bool recording = false;

const char *printable(const char *text) { return text ? text : "~"; }

void recordTree(const Menu &menu, const char *mode) {
  if (std::strcmp(mode, "parse") == 0)
    std::printf("%u:%s:%s:%s:%d,", menu.sourcePortDepth(),
                printable(menu.sourcePortTitle()),
                printable(menu.sourcePortName()),
                printable(menu.sourcePortCategory()),
                menu.sourcePortChildren().count());
  else if (std::strcmp(mode, "children") == 0)
    std::printf("%d,", menu.hasChildren());
  else if (std::strcmp(mode, "separator") == 0)
    std::printf("%d,", menu.isSeparator());
  else
    tracked[trackedCount++] = &menu;
  const auto &children = menu.sourcePortChildren();
  for (int index = 0; index < children.count(); ++index)
    recordTree(*children.at(index), mode);
}

void addItem(AttributeQueue &items, const char *title, const char *name,
             const char *category, bool nested = false) {
  auto &allocator = AttributeAllocator::getDefault();
  auto &item = *items.appendAttributes(allocator);
  if (title)
    item.set("title", title, *title == 0);
  if (name)
    item.set("name", name);
  if (category)
    item.set("category", category);
  if (nested) {
    auto &submenu = *item.makeAttributes("subMenu")->makeQueue("items");
    addItem(submenu, "", "blank", "more");
    addItem(submenu, "-x", nullptr, nullptr);
  }
}

struct DerivedMenu : Menu {};
} // namespace

void operator delete(void *pointer) noexcept {
  if (recording)
    for (int index = 0; index < trackedCount; ++index)
      if (tracked[index] == pointer)
        std::printf("%d,", index);
  std::free(pointer);
}

void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const char *mode = argv[1];
  for (int scenario = 0; scenario < 5; ++scenario) {
    DefaultAllocatedAttributes attributes;
    if (scenario > 0) {
      auto &items = *attributes.makeQueue("items");
      if (scenario >= 2)
        addItem(items, "-", "first", "category");
      if (scenario >= 3) {
        items.append(7);
        addItem(items, nullptr, nullptr, nullptr);
        addItem(items, ".", "parent", nullptr, true);
        addItem(items, "+", nullptr, "category");
      }
    }

    alignas(DerivedMenu) unsigned char storage[sizeof(DerivedMenu)]{};
    const bool base = std::strcmp(mode, "D2") == 0;
    auto *derived = base ? new (storage) DerivedMenu : nullptr;
    auto *menu = base ? static_cast<Menu *>(derived) : new (storage) Menu;
    menu->parse(attributes);
    if (scenario == 4)
      menu->parse(attributes);
    std::printf("%d|", scenario);
    trackedCount = 0;
    recordTree(*menu, mode);
    recording = base || std::strcmp(mode, "D1") == 0;
    if (base)
      derived->~DerivedMenu();
    else
      menu->~Menu();
    recording = false;
    std::puts("");
  }
}
