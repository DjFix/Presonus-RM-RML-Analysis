#include "presonus/IconManager.hpp"
#include "presonus/SLChannel.hpp"

#include "core/portable/corefile.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string_view>

namespace {
using Category = IconManager::ChannelCategory;
using Core::CString256;
using Core::Portable::FileName;

bool observeArrays;
int deletions;

void addNamedFiles(Category &category, int count) {
  for (int i = 0; i < count; ++i) {
    char folder[32];
    std::snprintf(folder, sizeof(folder), "v/ordered/%d", i);
    category.parseIcons(FileName(folder), false);
  }
}

void printCategory(const Category &category) {
  std::puts(category.name());
  for (int index = 0; index < category.iconCount(); ++index)
    std::puts(category.iconFile(index));
}
} // namespace

extern "C" void __real__ZdaPv(void *pointer);
extern "C" void __wrap__ZdaPv(void *pointer) {
  if (observeArrays && pointer)
    ++deletions;
  __real__ZdaPv(pointer);
}

int main(int argc, char **argv) {
  if (argc >= 3 && std::string_view(argv[1]) == "list") {
    Core::Portable::FileIterator iterator(argv[2]);
    while (const auto *entry = iterator.next()) {
      FileName name;
      entry->name.getName(name);
      std::printf("%d %s\n", entry->directory, name.str());
    }
    return 0;
  }
  if (argc != 4)
    return 2;

  const int mode = std::atoi(argv[1]);
  const auto *probe = argv[2];
  const auto *input = std::strcmp(probe, "<null>") == 0 ? nullptr : probe;
  const bool option = std::atoi(argv[3]) != 0;

  if (mode == 1) {
    auto *category = new Category(FileName("v/missing"), false);
    addNamedFiles(*category, std::atoi(probe));
    std::printf("before %d\n", category->iconCount());
    observeArrays = true;
    delete category;
    observeArrays = false;
    std::printf("array deletions %d\n", deletions);
    return 0;
  }
  if (mode == 2) {
    Category category(FileName(), false);
    category.parseIcons(FileName("v/existing"), false);
    category.parseIcons(FileName(probe), option);
    printCategory(category);
    return 0;
  }
  if (mode == 3) {
    Category category(FileName(probe), option);
    printCategory(category);
    return 0;
  }
  if (mode == 4 || mode == 5) {
    Category category(FileName("v/missing"), false);
    addNamedFiles(category, 4);
    if (mode == 4)
      std::puts(category.getIconName(std::atoi(probe)));
    else
      std::printf("%d\n", category.getIconIndex(input));
    return 0;
  }

  Category drums(FileName("v/MANAGER/DRUMS"), false);
  Category keys(FileName("v/MANAGER/keys"), false);
  drums.parseIcons(FileName("v/ordered/0"), false);
  drums.parseIcons(FileName("v/ordered/2"), false);
  const Category *categories[] = {&drums, &keys};
  const IconManager manager(Core::ConstVector<const Category *>(
      categories, mode != 6 || option ? 2 : 0));
  const auto printResult = [&](const Category *result) {
    if (!result)
      std::puts("null");
    else if (result == &drums)
      std::puts("first");
    else if (result == &keys)
      std::puts("second");
    else if (result == manager.getCategory(999) && result->iconCount() == 0 &&
             result->name().isEmpty())
      std::puts("fallback");
  };

  if (mode == 6) {
    printResult(manager.getCategory(std::atoi(probe)));
  } else if (mode == 7) {
    printResult(manager.getCategoryForIconId(CString256(input)));
  } else if (mode == 8) {
    Presonus::SLChannelBase unused("fixture");
    CString256 output("overwritten");
    manager.suggestChannelName(input, unused, output);
    std::puts(output);
  } else {
    return 2;
  }
}
