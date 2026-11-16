#include "presonus/panel/ChannelPresetComponent.hpp"
#include <bit>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace Core::Portable;
using namespace Presonus::Panel;
struct Sink : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {}
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
};
// Explicit test boundary for service operations unrelated to category lookup.
// Unexpected operations fail rather than supplying a production fallback.
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameCache &cache;
  mutable int lookups = 0;
  explicit Services(PresetNameCache &c) : cache(c) {}
  static void unexpected() {
    throw std::logic_error("unrelated service boundary");
  }
  int selectedSlot(const PresetComponent &) const override {
    unexpected();
    return 0;
  }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    unexpected();
    return false;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    unexpected();
  }
  const char *presetFolder(const PresetComponent &) const override {
    return "channel";
  }
  void ensureNameManager() const override {}
  PresetNameCache *lookupCache(const char *) const override {
    ++lookups;
    return &cache;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    unexpected();
    return false;
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    unexpected();
  }
  const char *emptyNameMarker() const override {
    unexpected();
    return nullptr;
  }
  void updateSelection(PresetComponent &) override { unexpected(); }
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    unexpected();
    return 0;
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    unexpected();
  }
};
struct Setup : ChannelPresetComponent {
  using ChannelPresetComponent::ChannelPresetComponent;
  void add(Parameter *p) { paramList.add(p); }
  void paramChanged(Parameter *, int) override {
  } // isolate category method from event recursion
};
int main() {
  int present;
  unsigned bits;
  std::string selected;
  while (std::cin >> present >> bits >> std::quoted(selected)) {
    Sink sink;
    PresetNameCache cache("channel", FileName("unused"), 99, 0, sink);
    for (int i = 0; i < 99; ++i) {
      std::string category;
      std::cin >> std::quoted(category);
      cache.cachePreset("preset", category.c_str(), i);
    }
    Services services(cache);
    Presonus::Mixer::MixerComponentBase mixer;
    ParamInfo gateInfo PARAM_FLOAT(78, "gate", -1e30f, 1e30f, 0, 1, nullptr, 0,
                                   0, 0);
    NumericParam gate(gateInfo);
    gate.setValue(std::bit_cast<float>(bits), false);
    // Genuine CCL parameters preserve the native float gate inputs, including
    // NaN/infinity; the raw float setter does not perform display clamping.
    presonus::panel::ChannelPresetState state{
        mixer, Core::ConstVector<Component *>(nullptr, 0), nullptr,
        present ? &gate : nullptr};
    Setup page(services, state);
    auto *slotInfo =
        new ParamInfo PARAM_INT(0, "slot", 0, 98, 77, nullptr, nullptr, 0, 0);
    auto *slot = new NumericParam(*slotInfo, true);
    page.add(slot);
    auto *categoryInfo = new ParamInfo PARAM_STRING(100, "category", 0);
    auto *category = new StringParam(*categoryInfo, true);
    page.add(category);
    category->fromString(selected.c_str(), false);
    page.onPresetCategoryChanged();
    std::cout << static_cast<int>(slot->getValue()) << ' ' << services.lookups
              << '\n';
  }
}
