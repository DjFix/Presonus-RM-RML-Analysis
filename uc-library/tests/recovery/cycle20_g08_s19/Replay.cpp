#include "presonus/panel/PresetComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"

#include <cstdio>
#include <iostream>
#include <string>
#include <tuple>
#include <type_traits>
#include <vector>

using namespace Core::Portable;
using Presonus::Panel::PresetComponent;
using Presonus::Panel::PresetNameCache;

namespace presonus::panel {
struct PresetCacheAccess {
  static auto snapshot(const PresetNameCache &cache) {
    std::vector<std::pair<std::string, std::string>> entries;
    for (int index = 0; index < cache.entries.count(); ++index) {
      auto &entry = cache.entries[index];
      entries.emplace_back(entry.name.str(), entry.category.str());
    }
    std::vector<std::string> categories;
    for (int index = 0; index < cache.categories.count(); ++index)
      categories.emplace_back(cache.categories[index].str());
    return std::make_tuple(cache.dirty, cache.protectedSlots, cache.capacity,
                           cache.observers.count(), cache.receivers.count(),
                           entries, categories);
  }
};
} // namespace presonus::panel

namespace {
struct Services final : presonus::panel::PresetApplicationServices {
  explicit Services(PresetNameCache &cache) : cache_(cache) {}
  int selectedSlot(const PresetComponent &c) const override {
    ++calls;
    return static_cast<int>(c.getParameterByTag(0)->getValue());
  }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    ++calls;
    return true;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    ++calls;
  }
  const char *presetFolder(const PresetComponent &) const override {
    ++calls;
    return "test";
  }
  void ensureNameManager() const override { ++calls; }
  PresetNameCache *lookupCache(const char *) const override {
    ++calls;
    return &cache_;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    ++calls;
    return true;
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    ++calls;
  }
  const char *emptyNameMarker() const override {
    ++calls;
    return "* Empty Location *";
  }
  void updateSelection(PresetComponent &) override { ++calls; }
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    ++calls;
    return 0;
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    ++calls;
  }

  mutable unsigned calls = 0;
  PresetNameCache &cache_;
};
struct CacheObserver final : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    ++changes;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {
    ++rebuilds;
  }
  unsigned changes = 0, rebuilds = 0;
};

void dispatch(PresetComponent &component, PresetNameCache &cache) {
  component.cacheUpdated(cache);
}
} // namespace

int main() {
  using Callback = void (PresetComponent::*)(PresetNameCache &);
  static_assert(std::is_same_v<decltype(static_cast<Callback>(
                                   &PresetComponent::cacheUpdated)),
                               Callback>);
  const ParamInfo params[] = {
      PARAM_FLOAT(0, "slot", 0, 30, 0, 1, "", nullptr, 0, 0),
      PARAM_STRING(1, "name", 0),
      PARAM_STRING(2, "edit", 0),
      PARAM_STRING(100, "category", 0),
  };
  unsigned virtualDispatch, seed;
  while (std::cin >> virtualDispatch >> seed) {
    const int current = static_cast<int>(seed % 3);
    CacheObserver sink;
    FileName directory;
    PresetNameCache cache("preset", directory, 3, 1, sink);
    auto *delegate = reinterpret_cast<PresetNameCache::Delegate *>(&sink);
    cache.addObserver(delegate);
    cache.addCategory("indexed");
    cache.cachePreset("cached", "indexed", current);
    Services provider(cache);
    PresetComponent component(provider);
    component.addParameters(params, 4);
    component.getParameterByTag(0)->setValue(static_cast<float>(current),
                                             false);
    const auto text = [&](int tag) -> StringParam & {
      return *StringParam::cast(component.getParameterByTag(tag));
    };
    text(1).fromString("before name", false);
    text(2).fromString("before edit", false);
    text(100).fromString("before category", false);
    auto values = [&] {
      return std::make_tuple(
          component.getParameterByTag(0)->getValue(),
          std::string(text(1).getText()), std::string(text(2).getText()),
          std::string(text(100).getText()), sink.changes, sink.rebuilds,
          presonus::panel::PresetCacheAccess::snapshot(cache));
    };
    const auto before = values();
    const auto beforeCalls = provider.calls;
    if (virtualDispatch)
      dispatch(component, cache);
    else
      component.PresetComponent::cacheUpdated(cache);
    const bool unchanged = values() == before && beforeCalls == provider.calls;
    component.cacheUpdated(cache, current + 1, "ignored", "ignored");
    if (values() != before)
      return 2;
    component.cacheUpdated(cache, current, "updated name", "updated category");
    if (std::string(text(1).getText()) != "updated name" ||
        std::string(text(2).getText()) != "updated name" ||
        std::string(text(100).getText()) != "updated category" ||
        sink.rebuilds || sink.changes != 1 ||
        presonus::panel::PresetCacheAccess::snapshot(cache) !=
            std::get<6>(before))
      return 4;
    std::cout << unchanged << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
