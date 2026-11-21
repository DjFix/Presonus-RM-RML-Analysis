#include "presonus/IconManager.hpp"

#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include "presonus/utilities/string_utils.hpp"

#include <cstring>
#include <memory>

namespace {
using Core::CString256;
using Core::Portable::FileIterator;
using Core::Portable::FileName;

bool sameName(const char *left, const char *right) {
  return std::strcmp(left, right) == 0;
}
} // namespace

IconManager::ChannelCategory::ChannelCategory(const FileName &path,
                                              bool recurse)
    : icons_(1) {
  path.getName(name_);
  name_.toLowercase();
  parseIcons(path, recurse);
}

IconManager::ChannelCategory::~ChannelCategory() = default;

void IconManager::ChannelCategory::parseIcons(const FileName &path,
                                              bool recurse) {
  const auto appendName = [this](const FileName &fullPath) {
    FileName name;
    fullPath.getName(name);
    if (icons_.count() < icons_.getCapacity() ||
        icons_.resize(icons_.count() + 1)) {
      icons_.add(name);
    }
  };

  FileIterator outer(path);
  while (const auto *entry = outer.next()) {
    if (entry->hidden || (entry->directory && !recurse))
      continue;

    if (entry->directory) {
      FileIterator middle(entry->name);
      while (const auto *child = middle.next()) {
        if (child->hidden)
          continue;
        if (child->directory) {
          FileIterator inner(child->name);
          while (const auto *descendant = inner.next()) {
            if (descendant->hidden)
              continue;
            if (descendant->directory)
              parseIcons(descendant->name, true);
            appendName(descendant->name);
          }
        }
        appendName(child->name);
      }
    }
    appendName(entry->name);
  }
}

Core::CStringBuffer<256>
IconManager::ChannelCategory::getIconName(int index) const {
  // The original body exposes bytes via its scratch address. Return an owning
  // string in the portable model. The original return declaration is unknown.
  FileName name = icons_.isValidIndex(index) ? icons_.at(index) : FileName{};
  name.setExtension("", true);
  if (name.lastChar() == '.')
    name.truncate(name.length() - 1);
  name.toLowercase();
  return name;
}

int IconManager::ChannelCategory::getIconIndex(const char *name) const {
  const char *search = name ? name : "";
  for (int index = 0; index < icons_.count(); ++index) {
    auto normalized = getIconName(index);
    presonus::utilities::removeWhitespace(normalized);
    if (sameName(normalized, search))
      return index;
  }
  return -1;
}

IconManager::~IconManager() {
  for (auto *category : loadedCategories_)
    delete category;
}

int IconManager::categoryCount() const {
  return borrowedCategories_.count() + loadedCategories_.count();
}

const IconManager::ChannelCategory *IconManager::categoryAt(int index) const {
  const int borrowedCount = borrowedCategories_.count();
  return index < borrowedCount ? borrowedCategories_.at(index)
                               : loadedCategories_.at(index - borrowedCount);
}

void IconManager::loadIcons() {
  const auto append = [this](std::unique_ptr<ChannelCategory> category) {
    if (category->iconCount() == 0)
      return;

    const int count = loadedCategories_.count();
    if ((count < loadedCategories_.getCapacity() ||
         loadedCategories_.resize(count + 1)) &&
        loadedCategories_.add(category.get())) {
      category.release();
    }
  };

  auto all = std::make_unique<ChannelCategory>(iconRoot_, true);
  all->name_ = FileName("All");
  append(std::move(all));

  FileIterator iterator(iconRoot_);
  while (const auto *entry = iterator.next()) {
    if (entry->hidden)
      continue;
    if (!entry->directory) {
      // The pinned POSIX sink treats its rendered message as a format string.
      // Escape path percent signs before handing the message to that sink.
      Core::CStringBuffer<1024> diagnostic("Track icon with no category!?");
      for (const char *unit = entry->name.str(); *unit; ++unit) {
        if (*unit == '%')
          diagnostic.append('%');
        diagnostic.append(*unit);
      }
      diagnostic.append('\n');
      Core::DebugPrint(diagnostic.str());
      continue;
    }
    append(std::make_unique<ChannelCategory>(entry->name, false));
  }
}

const IconManager::ChannelCategory *IconManager::getCategory(int index) const {
  if (index < categoryCount())
    return index >= 0 ? categoryAt(index) : nullptr;

  static const ChannelCategory empty(FileName{}, false);
  return &empty;
}

const IconManager::ChannelCategory *
IconManager::getCategoryForIconId(Core::CStringBuffer<256> id) const {
  if (id.isEmpty())
    return nullptr;

  FileName parent(id);
  parent.ascend();
  for (int index = 0; index < categoryCount(); ++index) {
    const auto *category = categoryAt(index);
    if (sameName(category->name(), parent))
      return category;
  }
  return nullptr;
}

void IconManager::suggestChannelName(const char *id, Presonus::SLChannelBase &,
                                     Core::CStringBuffer<256> &output) const {
  const CString256 input(id);
  if (const auto *category = getCategoryForIconId(input)) {
    FileName name(input);
    name.getName(name);
    const int index = category->getIconIndex(name);
    if (index >= 0) {
      output = category->getIconName(index);
      presonus::utilities::makeProperMixedCase(output);
      return;
    }
  }
  output = input;
}
