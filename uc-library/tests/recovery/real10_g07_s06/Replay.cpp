#include "core/public/coreformatter.h"
#include "presonus/panel/ChannelPresetComponent.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace Core::Portable;
using namespace Presonus::Panel;
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameCache *cache = nullptr;
  mutable int lookups = 0;
  Services() = default;
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
    return cache;
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

// The explicit symbols invoke each host ABI constructor variant independently.
extern "C" void
selectedConstructor(void *, Presonus::Mixer::MixerComponentBase &) asm(
    "_ZN8Presonus5Panel22ChannelPresetComponentC1ERNS_"
    "5Mixer18MixerComponentBaseE");
int main() {
  static Core::IntFormatter formatter("channelnum");
  Core::FormatterRegistry::add(&formatter);
  int mode;
  while (std::cin >> mode) {
    Services services;
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.presetApplicationServices = &services;
    alignas(ChannelPresetComponent) unsigned char
        storage[sizeof(ChannelPresetComponent)];
    selectedConstructor(storage, mixer);
    auto *page =
        std::launder(reinterpret_cast<ChannelPresetComponent *>(storage));
    auto *category = page->sourcePortCategoryParameter();
    if (!category || category != page->getParameterByTag(100))
      throw std::runtime_error("missing actual CCL ListParam binding");
    Core::CString64 display;
    page->getParameterByTag(2)->toString(display.getBuffer(),
                                         display.getSize());
    std::cout << std::quoted(std::string(page->getName().str())) << ' '
              << std::quoted(std::string(display.str())) << ' '
              << std::quoted(
                     page->getParameterByTag(0)->getFormatter()->getName())
              << ' ' << page->countParameters() << ' ' << category->getTag()
              << ' ' << category->getType() << ' ' << category->getMin() << ' '
              << category->getMax() << ' ' << category->getDefault() << ' '
              << category->isPublic();
    for (int i = 0; i < 9; ++i) {
      category->setValue(static_cast<float>(i), false);
      Core::CString32 text;
      category->toString(text.getBuffer(), text.getSize());
      std::cout << ' ' << std::quoted(std::string(text.str()));
    }
    // Separate actual provider cast observations for native boundary variants.
    ParamList list;
    const ParamInfo wrong PARAM_STRING(100, "wrong", 0);
    const char *names[] = {"a", "b"};
    const ParamInfo right PARAM_LIST(100, "right", names, 0, 0);
    if (mode == 1)
      list.add(wrong);
    if (mode == 2)
      list.add(right);
    auto *found = list.byTag(100);
    const bool cast = core_cast<ListParam>(found) != nullptr;
    std::cout << ' ' << static_cast<bool>(found) << ' ' << cast << '\n';
    page->~ChannelPresetComponent();
  }
}
