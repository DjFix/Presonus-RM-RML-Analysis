#include "presonus/IconManager.hpp"

#include "core/portable/corefile.h"

#include <array>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string_view>

namespace {
using Category = IconManager::ChannelCategory;
using Core::Portable::FileIterator;
using Core::Portable::FileName;

bool observe;
bool failNextCategoryGrowth;
std::array<void *, 64> allocations;
std::size_t allocated;
std::size_t deleted;

void noteDeletion(void *pointer) {
  if (!observe)
    return;
  for (auto &entry : allocations) {
    if (entry && entry == pointer) {
      entry = nullptr;
      ++deleted;
      return;
    }
  }
}
} // namespace

extern "C" void *__real__Znwm(std::size_t size);
extern "C" void *__wrap__Znwm(std::size_t size) {
  auto *pointer = __real__Znwm(size);
  if (observe && size == sizeof(Category)) {
    if (allocated == allocations.size())
      std::abort();
    allocations[allocated++] = pointer;
  }
  return pointer;
}

extern "C" void __real__ZdlPvm(void *pointer, std::size_t size);
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  noteDeletion(pointer);
  __real__ZdlPvm(pointer, size);
}

extern "C" void *__real__Znam(std::size_t size);
extern "C" void *__wrap__Znam(std::size_t size) {
  if (failNextCategoryGrowth && size == 5 * sizeof(Category *)) {
    failNextCategoryGrowth = false;
    throw std::bad_alloc();
  }
  return __real__Znam(size);
}

int main(int argc, char **argv) {
  if (argc == 3 && std::string_view(argv[1]) == "list") {
    FileIterator iterator(argv[2]);
    while (const auto *entry = iterator.next()) {
      FileName name;
      entry->name.getName(name);
      std::printf("%d %s\n", entry->directory, name.str());
    }
    return 0;
  }
  if (argc != 4)
    return 2;

  observe = true;
  failNextCategoryGrowth = std::string_view(argv[1]) == "failure";
  {
    IconManager manager{FileName(argv[2])};
    const int repeat = std::atoi(argv[3]);
    for (int load = 0; load < repeat; ++load) {
      std::printf("begin %d\n", load);
      try {
        manager.loadIcons();
      } catch (const std::bad_alloc &) {
        std::puts("allocation failure");
      }
      for (int index = 0;; ++index) {
        const auto *category = manager.getCategory(index);
        if (category->iconCount() == 0)
          break;
        std::printf("category %s\n", category->name().str());
        for (int icon = 0; icon < category->iconCount(); ++icon)
          std::printf("icon %s\n", category->iconFile(icon).str());
      }
      std::printf("live %zu\n", allocated - deleted);
    }
  }
  std::printf("allocated %zu\ndeleted %zu\n", allocated, deleted);
}
