#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
using Presonus::Panel::PresetNameCache;
using Presonus::Panel::PresetNameManager;
namespace {
std::vector<PresetNameCache *> identities;
bool providerMode = false;
bool infoResult = false;
const char *nullable(const char *s) {
  return std::string(s) == "~" ? nullptr : s;
}
std::string text(const char *s) { return s ? s : "~"; }
int identity(PresetNameCache *p) {
  for (unsigned i = 0; i < identities.size(); ++i)
    if (identities[i] == p)
      return static_cast<int>(i);
  return -1;
}
struct Sink : PresetNameCache::ObserverSink {
  int changes = 0;
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    ++changes;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
};
} // namespace
extern "C" void realCache(
    PresetNameCache *, const char *, const char *,
    int) asm("__real__ZN8Presonus5Panel15PresetNameCache11cachePresetEPKcS3_i");
extern "C" bool
realInfo(PresetNameCache *, Core::CStringBuffer<64> &,
         Core::CStringBuffer<32> &,
         int) asm("__real__"
                  "ZN8Presonus5Panel15PresetNameCache13getPresetInfoERN4Core13C"
                  "StringBufferILi64EEERNS3_ILi32EEEi");
extern "C" Core::Portable::FileName
realPath(PresetNameCache *, unsigned, bool) asm(
    "__real__ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb");
extern "C" void wrappedCache(
    PresetNameCache *p, const char *name, const char *category,
    int slot) asm("__wrap__"
                  "ZN8Presonus5Panel15PresetNameCache11cachePresetEPKcS3_i");
extern "C" void wrappedCache(PresetNameCache *p, const char *name,
                             const char *category, int slot) {
  if (providerMode) {
    realCache(p, name, category, slot);
    return;
  }
  std::cout << "cache|cache" << identity(p) << '|' << text(name) << '|'
            << text(category) << '|' << slot << '\n';
}
extern "C" bool
wrappedInfo(PresetNameCache *, Core::CStringBuffer<64> &,
            Core::CStringBuffer<32> &,
            int) asm("__wrap__"
                     "ZN8Presonus5Panel15PresetNameCache13getPresetInfoERN4Core"
                     "13CStringBufferILi64EEERNS3_ILi32EEEi");
extern "C" bool wrappedInfo(PresetNameCache *p, Core::CStringBuffer<64> &name,
                            Core::CStringBuffer<32> &category, int slot) {
  if (providerMode)
    return realInfo(p, name, category, slot);
  std::cout << "info|cache" << identity(p) << '|' << slot << '\n';
  name = "NativeName";
  category = "NativeCategory";
  return infoResult;
}
extern "C" Core::Portable::FileName
wrappedPath(PresetNameCache *, unsigned, bool) asm(
    "__wrap__ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb");
extern "C" Core::Portable::FileName wrappedPath(PresetNameCache *p,
                                                unsigned slot, bool full) {
  if (providerMode)
    return realPath(p, slot, full);
  std::cout << "path|cache" << identity(p) << '|' << slot << '|' << full
            << '\n';
  return Core::Portable::FileName("BoundaryPath");
}
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  Sink sink;
  Core::Portable::FileName folder("/nonexistent-presets-test-only");
  if (std::string(argv[1]) == "providers") {
    providerMode = true;
    PresetNameCache cache("channel", folder, 4, 0, sink);
    auto *observer = reinterpret_cast<PresetNameCache::Delegate *>(&sink);
    cache.addObserver(observer);
    cache.cachePreset("Voice", "Vocal", 1);
    Core::CString64 name;
    Core::CString32 category;
    bool result = cache.getPresetInfo(name, category, 1);
    if (!result || std::string(name.str()) != "Voice" ||
        std::string(category.str()) != "Vocal" || sink.changes != 1)
      return 3;
    const auto path = cache.getFileNameForSlot(1, false);
    if (std::string(path.str()) != "02.Voice.Vocal.channel")
      return 4;
    cache.cachePreset("Voice", "Vocal", 1);
    cache.cachePreset("Outside", "Outside", -1);
    cache.cachePreset("Outside", "Outside", 4);
    if (sink.changes != 1)
      return 5;
    cache.cachePreset(nullptr, nullptr, 1);
    cache.getPresetInfo(name, category, 1);
    if (std::string(name.str()) != "* Empty Location *" || !category.isEmpty())
      return 6;
    for (int length : {0, 1, 63, 254, 255, 256, 300}) {
      std::string input(length, 'x');
      Core::Portable::FileName bounded(input.c_str());
      if (bounded.length() != std::min(length, 255))
        return 7;
    }
    Core::Portable::FileName nullPath(nullptr);
    if (!nullPath.isEmpty())
      return 8;
    std::cout << "actual providers: cache update/info/path/observer, no-op and "
                 "bounds; CCL copy 0..300 and null\n";
    return 0;
  }
  if (argc < 10)
    return 2;
  std::string task(argv[1]);
  int slot = std::stoi(argv[2]);
  infoResult = std::stoi(argv[3]) != 0;
  int count = std::stoi(argv[9]);
  if (argc != 10 + count)
    return 2;
  std::vector<std::unique_ptr<PresetNameCache>> storage;
  for (int i = 0; i < count; ++i) {
    storage.emplace_back(new PresetNameCache(argv[10 + i], folder, 4, 0, sink));
    identities.push_back(storage.back().get());
  }
  PresetNameManager manager(identities.data(), count);
  if (task == "rolling10_presets_01")
    manager.cachePreset(nullable(argv[6]), nullable(argv[4]), nullable(argv[5]),
                        slot);
  else if (task == "rolling10_presets_02") {
    Core::CString64 name("OriginalName");
    Core::CString32 category("OriginalCategory");
    bool result =
        manager.getPresetInfo(name, category, slot, nullable(argv[6]));
    std::cout << "result|" << result << '|' << name.str() << '|'
              << category.str() << '\n';
  } else if (task == "rolling10_presets_03") {
    auto path = manager.getPresetFilePath(slot, nullable(argv[6]), infoResult);
    std::cout << "result|" << path.str() << '\n';
  } else if (task == "rolling10_replacement_presets_01") {
    auto *result = manager.lookupCacheForRemoteUrl(nullable(argv[7]));
    std::cout << "result|" << identity(result) << '\n';
  } else
    return 2;
  return 0;
}
