#include "presonus/panel/FXPresetRecallComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"

#include <cstdio>
#include <iostream>
#include <string>
#include <tuple>
#include <type_traits>
#include <vector>

using namespace Core::Portable;
using Presonus::Panel::FXPresetRecallComponent;
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
struct Services final : presonus::fx_preset_recall_port::FxRecallServices {
  FileName presetPath(unsigned, const char *) override {
    ++paths;
    return FileName();
  }
  void presetInfo(char *name, int capacity, unsigned index,
                  const char *) override {
    ++infos;
    std::snprintf(name, static_cast<std::size_t>(capacity), "preset %u", index);
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    ++lookups;
    return nullptr;
  }
  unsigned paths = 0, infos = 0, lookups = 0;
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

void dispatch(FXPresetRecallComponent &component, PresetNameCache &cache) {
  component.cacheUpdated(cache);
}
} // namespace

int main() {
  using Callback = void (FXPresetRecallComponent::*)(PresetNameCache &);
  static_assert(std::is_same_v<decltype(static_cast<Callback>(
                                   &FXPresetRecallComponent::cacheUpdated)),
                               Callback>);
  const ParamInfo numeric =
      PARAM_FLOAT(9, "index", 0, 31, 0, 1, "", nullptr, 0, 0);
  const ParamInfo text = PARAM_STRING(10, "label", 0);
  unsigned virtualDispatch, seed;
  while (std::cin >> virtualDispatch >> seed) {
    const int current = static_cast<int>(seed % 3);
    const int effect = static_cast<int>((seed / 17) % 3);
    Services provider;
    CacheObserver sink;
    FileName directory;
    PresetNameCache cache("fx", directory, 3, 1, sink);
    auto *delegate = reinterpret_cast<PresetNameCache::Delegate *>(&sink);
    cache.addObserver(delegate);
    cache.addCategory("indexed");
    cache.cachePreset("cached", "indexed", current);

    NumericParam slot(numeric), loaded(numeric), type(numeric);
    StringParam typeName(text), presetName(text);
    slot.setValue(static_cast<float>(current), false);
    loaded.setValue(static_cast<float>(current), false);
    type.setValue(1.f, false);
    typeName.fromString("before type", false);
    presetName.fromString("before name", false);
    FXPresetRecallComponent component(provider, slot, loaded, typeName,
                                      presetName, type, "test", effect);
    auto observe = [&] {
      return std::make_tuple(
          component.getSlotNum(), std::string(component.sourcePortCategory()),
          slot.getValue(), loaded.getValue(), type.getValue(),
          std::string(typeName.getText()), std::string(presetName.getText()),
          provider.paths, provider.infos, provider.lookups, sink.changes,
          sink.rebuilds, presonus::panel::PresetCacheAccess::snapshot(cache));
    };
    const auto before = observe();
    if (virtualDispatch)
      dispatch(component, cache);
    else
      component.FXPresetRecallComponent::cacheUpdated(cache);
    const bool unchanged = observe() == before;

    component.cacheUpdated(cache, current + 1, "ignored", "");
    if (observe() != before)
      return 2;
    component.cacheUpdated(cache, current, "first value", "");
    if (std::string(presetName.getText()) !=
            "preset " + std::to_string(current) ||
        std::string(typeName.getText()) !=
            (effect > 1 ? "FILTER DELAY" : "SMALL ROOM") ||
        provider.infos != 1 || provider.paths || provider.lookups ||
        sink.rebuilds || sink.changes != 1 ||
        presonus::panel::PresetCacheAccess::snapshot(cache) !=
            std::get<12>(before))
      return 4;
    std::cout << unchanged << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
