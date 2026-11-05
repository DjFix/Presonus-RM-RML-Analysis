#include "presonus/panel/PresetNameCache.hpp"
#include <cstdio>
#include <cstring>
namespace Presonus::Panel {
namespace {
constexpr const char *emptyMarker = "* Empty Location *";
}
PresetNameCache::CacheInfo::CacheInfo()
    : name(emptyMarker), category(nullptr) {}

PresetNameCache::PresetNameCache(const char *kind,
                                 const Core::Portable::FileName &path,
                                 int slots, int protectedCount,
                                 ObserverSink &callback)
    : type(kind), folder(path), protectedSlots(protectedCount), capacity(slots),
      sink(callback) {
  for (int i = 0; i < slots; ++i) {
    Entry e;
    e.name = emptyMarker;
    entries.add(e);
  }
}
int PresetNameCache::getCapacity() const { return capacity; }

bool PresetNameCache::parseFileName(const Core::Portable::FileName &path,
                                    Core::CStringBuffer<64> &name,
                                    Core::CStringBuffer<32> &category,
                                    int &slot) {
  name = emptyMarker;
  category.empty();
  slot = -1;
  if (path.isEmpty())
    return false;
  Core::Portable::FileName base;
  path.getName(base);
  Core::Vector<const char *> parts;
  // The native tokenizer discards empty dot-separated fields.
  char *cursor = base.getBuffer();
  while (*cursor) {
    while (*cursor == '.')
      ++cursor;
    if (!*cursor)
      break;
    char *start = cursor;
    while (*cursor && *cursor != '.')
      ++cursor;
    if (*cursor)
      *cursor++ = 0;
    parts.add(start);
  }
  if (parts.count() <= 2)
    return false;
  long long parsed = 0;
  std::sscanf(parts[0], "%lld", &parsed);
  slot = static_cast<int>(static_cast<unsigned long long>(parsed) - 1);
  Core::CString32 candidate(parts[parts.count() - 2]);
  bool known = false;
  for (int i = 0; i < categories.count(); ++i)
    if (candidate == categories[i].str() && parts.count() != 3) {
      known = true;
      break;
    }
  if (known)
    category = candidate;
  name.empty();
  for (int i = 1, end = parts.count() - (known ? 2 : 1); i < end; ++i)
    name += parts[i];
  return true;
}
Core::Portable::FileName PresetNameCache::buildFileName(
    unsigned slot, const Core::Portable::FileName &folder, const char *type,
    const char *name, const char *category, const char *subfolder, bool full) {
  Core::CString64 cleanName(name);
  cleanName.trimWhitespace();
  Core::CString32 cleanCategory(category);
  cleanCategory.trimWhitespace();
  Core::Portable::FileName result;
  result.appendFormat("%02d.%s.", static_cast<int>(slot + 1), cleanName.str());
  if (!cleanCategory.isEmpty())
    result.appendFormat("%s.", cleanCategory.str());
  result += type;
  result.makeValid();
  if (!full)
    return result;
  Core::Portable::FileName absolute(folder);
  if (subfolder)
    absolute.descend(subfolder);
  absolute.descend(result);
  return absolute;
}
Core::Portable::FileName PresetNameCache::buildFileName(unsigned slot,
                                                        const char *name,
                                                        const char *category,
                                                        const char *subfolder,
                                                        bool full) const {
  return buildFileName(slot, folder, type, name, category, subfolder, full);
}
bool PresetNameCache::canDelete(int slot) const {
  return slot >= protectedSlots;
}
void PresetNameCache::cachePreset(const char *name, const char *category,
                                  int slot) {
  if (slot < 0 || slot >= entries.count())
    return;
  auto &entry = entries[slot];
  if (entry.name == (name ? name : "") &&
      entry.category == (category ? category : ""))
    return;
  entry.name = name;
  entry.category = category;
  if (entry.name.isEmpty()) {
    entry.name = emptyMarker;
    entry.category.empty();
  }
  for (int i = 0, count = observers.count(); i < count; ++i)
    sink.changed(observers[i], *this, slot, name, category);
}
void PresetNameCache::rebuild() {
  if (!dirty)
    return;
  dirty = false;
  Core::Portable::FileIterator files(folder);
  while (auto *file = files.next()) {
    if (file->directory || file->hidden)
      continue;
    Core::CString64 name;
    Core::CString32 category;
    int slot = 0;
    parseFileName(file->name, name, category, slot);
    cachePreset(name, category, slot);
  }
  for (int i = 0, count = observers.count(); i < count; ++i)
    sink.rebuilt(observers[i], *this);
}
void PresetNameCache::addCategory(const char *category) {
  categories.add(Core::CString32(category));
}
void PresetNameCache::addObserver(Delegate *observer) {
  observers.addOnce(observer);
}
bool PresetNameCache::getPresetInfo(Core::CStringBuffer<64> &name,
                                    Core::CStringBuffer<32> &category,
                                    int slot) {
  if (slot >= entries.count())
    return false;
  // The native signed guard does not reject negative indices. The portable
  // contract requires slot >= 0; negative inputs are outside its valid domain.
  rebuild();
  name = entries[slot].name;
  category = entries[slot].category;
  return true;
}
Core::Portable::FileName PresetNameCache::getFileNameForSlot(unsigned slot,
                                                             bool full) {
  rebuild();
  return buildFileName(slot, entries[slot].name, entries[slot].category,
                       nullptr, full);
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
void PresetNameCache::sourcePortRemoveObserver(Delegate *observer) {
  observers.remove(observer);
}
} // namespace Presonus::Panel
