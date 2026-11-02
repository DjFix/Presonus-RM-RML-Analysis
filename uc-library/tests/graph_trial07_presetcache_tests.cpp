#include "presonus/panel/PresetNameCache.hpp"
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

using Presonus::Panel::PresetNameCache;
namespace presonus::panel {
struct PresetCacheAccess {
  static void clean(PresetNameCache &c) { c.dirty = false; }
  static auto &entries(PresetNameCache &c) { return c.entries; }
  static auto &observers(PresetNameCache &c) { return c.observers; }
  static auto &categories(PresetNameCache &c) { return c.categories; }
};
} // namespace presonus::panel
using Access = presonus::panel::PresetCacheAccess;
std::string hex(const char *s) {
  if (!s)
    return "null";
  std::ostringstream out;
  for (auto *p = reinterpret_cast<const unsigned char *>(s); *p; ++p)
    out << std::hex << std::setw(2) << std::setfill('0')
        << static_cast<unsigned>(*p);
  return out.str();
}
struct Sink final : PresetNameCache::ObserverSink {
  std::string events;
  void changed(PresetNameCache::Delegate *d, PresetNameCache &, int slot,
               const char *name, const char *category) override {
    events += "change," + std::to_string(reinterpret_cast<uintptr_t>(d)) + "," +
              std::to_string(slot) + "," + hex(name) + "," + hex(category) +
              ";";
  }
  void rebuilt(PresetNameCache::Delegate *d, PresetNameCache &) override {
    events += "rebuild," + std::to_string(reinterpret_cast<uintptr_t>(d)) + ";";
  }
};
int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  const std::string op = argv[1];
  int slot = std::stoi(argv[2]);
  auto text = [](char *s) -> const char * {
    return std::string(s) == "~" ? nullptr : s;
  };
  const char *name = text(argv[3]);
  const char *category = text(argv[4]);
  const char *extra = text(argv[5]);
  bool full = std::stoi(argv[6]) != 0;
  Sink sink;
  PresetNameCache cache("preset", Core::Portable::FileName(argv[7]), 3, 2,
                        sink);
  cache.addCategory("Vocal");
  cache.addCategory("Drums");
  Access::clean(cache);
  for (uintptr_t i = 1; i <= 2; ++i)
    cache.addObserver(reinterpret_cast<PresetNameCache::Delegate *>(i));
  int result = -999;
  Core::CString64 parsedName("unchanged");
  Core::CString32 parsedCategory("unchanged");
  Core::Portable::FileName path;
  if (op == "parse")
    result = cache.parseFileName(Core::Portable::FileName(name), parsedName,
                                 parsedCategory, slot);
  else if (op == "static")
    path = PresetNameCache::buildFileName(
        static_cast<unsigned>(slot), Core::Portable::FileName(argv[7]),
        "preset", name, category, extra, full);
  else if (op == "member")
    path = cache.buildFileName(static_cast<unsigned>(slot), name, category,
                               extra, full);
  else if (op == "canDelete")
    result = cache.canDelete(slot);
  else if (op == "cache")
    cache.cachePreset(name, category, slot);
  else if (op == "info")
    result = cache.getPresetInfo(parsedName, parsedCategory, slot);
  else if (op == "file")
    path = cache.getFileNameForSlot(static_cast<unsigned>(slot), full);
  else if (op == "category")
    cache.addCategory(name);
  else if (op == "observer")
    cache.addObserver(reinterpret_cast<PresetNameCache::Delegate *>(
        static_cast<uintptr_t>(slot)));
  else if (op == "rebuild") {
    // Use a new cache so native and portable dirty transitions are exercised.
    PresetNameCache fresh("preset", Core::Portable::FileName(argv[7]), 3, 2,
                          sink);
    fresh.addCategory("Vocal");
    fresh.addCategory("Drums");
    for (uintptr_t i = 1; i <= 2; ++i)
      fresh.addObserver(reinterpret_cast<PresetNameCache::Delegate *>(i));
    fresh.rebuild();
    fresh.rebuild();
    for (int i = 0; i < 3; ++i)
      Access::entries(cache)[i] = Access::entries(fresh)[i];
  } else
    return 3;
  std::cout << "result=" << result << "\nslot=" << slot
            << "\nname=" << hex(parsedName)
            << "\ncategory=" << hex(parsedCategory) << "\npath=" << hex(path)
            << "\nevents=" << sink.events << "\n";
  for (int i = 0; i < 3; ++i)
    std::cout << "entry=" << hex(Access::entries(cache)[i].name) << ","
              << hex(Access::entries(cache)[i].category) << "\n";
  for (int i = 0; i < Access::categories(cache).count(); ++i)
    std::cout << "cat=" << hex(Access::categories(cache)[i]) << "\n";
  for (int i = 0; i < Access::observers(cache).count(); ++i)
    std::cout << "observer="
              << reinterpret_cast<uintptr_t>(Access::observers(cache)[i])
              << "\n";
}
