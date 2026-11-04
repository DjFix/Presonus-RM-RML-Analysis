#include "presonus/panel/PresetComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include <iostream>
#include <stdexcept>
#include <string>

using Presonus::Panel::PresetComponent;
using Presonus::Panel::PresetNameCache;
struct Sink : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {}
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
};
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameCache &cache;
  std::string folder;
  mutable std::string trace;
  Services(PresetNameCache &c, const char *f) : cache(c), folder(f) {}
  int selectedSlot(const PresetComponent &) const override {
    throw std::runtime_error("unexpected selectedSlot");
  }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    throw std::runtime_error("unexpected slotEmpty callback");
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    throw std::runtime_error("unexpected slotFileName callback");
  }
  const char *presetFolder(const PresetComponent &) const override {
    trace += "folder,";
    return folder.c_str();
  }
  void ensureNameManager() const override { trace += "ensure,"; }
  PresetNameCache *lookupCache(const char *f) const override {
    if (folder != f)
      throw std::runtime_error("folder mismatch");
    trace += "cache,";
    return &cache;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    throw std::runtime_error("unexpected hasSelectedSlotParameter");
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    throw std::runtime_error("unexpected presetInfo");
  }
  const char *emptyNameMarker() const override {
    throw std::runtime_error("unexpected marker");
  }
  void updateSelection(PresetComponent &) override {
    throw std::runtime_error("unexpected updateSelection");
  }
  int recallAttributes(PresetComponent &, Core::Portable::Attributes &,
                       bool) override {
    throw std::runtime_error("unexpected recallAttributes");
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    throw std::runtime_error("unexpected delegate");
  }
};
int main(int argc, char **argv) {
  if (argc == 3 && std::string(argv[1]) == "provider") {
    std::cout << Core::Portable::FileUtils::fileExists(argv[2]) << '\n';
    return 0;
  }
  if (argc != 6)
    return 2;
  Sink sink;
  Core::Portable::FileName folder(argv[2]);
  PresetNameCache cache("preset", folder, 4, 0, sink);
  cache.rebuild();
  unsigned slot = std::stoul(argv[3]);
  if (slot >= 4)
    return 3;
  cache.cachePreset(argv[4], argv[5], slot);
  Services services(cache, argv[2]);
  PresetComponent component(services);
  if (std::string(argv[1]) == "path") {
    std::cout << component.getFileNameForSlot(slot).str() << '\n';
  } else if (std::string(argv[1]) == "app") {
    std::cout << component.isSlotEmpty(slot) << '\n' << services.trace << '\n';
  } else
    return 4;
}
