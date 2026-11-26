#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "presonus/panel/GeqPresetComponent.hpp"
#include <chrono>
#include <filesystem>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace Core::Portable;
using Presonus::Panel::GeqPresetComponent;
using Presonus::Panel::PresetComponent;
using Presonus::Panel::PresetNameCache;

namespace {
BEGIN_PARAMINFO(presetParams)
PARAM_INT(0, "slot", 0, 4, 0, "", "", 0, 0),
    PARAM_STRING(2, "loaded_name", 0) END_PARAMINFO
    constexpr ParamInfo selectorInfo = PARAM_FLOAT(0, "selection", -100, 100, 0,
                                                   0, "", "", 0, 0);

struct Sink : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {}
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
};

struct Services : presonus::panel::PresetApplicationServices {
  explicit Services(PresetNameCache &cache) : cache(cache) {}
  PresetNameCache &cache;
  mutable std::vector<int> notifications;

  int selectedSlot(const PresetComponent &) const override { return 0; }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    return true;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {}
  const char *presetFolder(const PresetComponent &) const override {
    return "geq";
  }
  void ensureNameManager() const override {}
  PresetNameCache *lookupCache(const char *) const override { return &cache; }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    return true;
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {}
  const char *emptyNameMarker() const override { return ""; }
  void updateSelection(PresetComponent &) override {}
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    return 0;
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &,
                      int slot, bool stored) const override {
    notifications.push_back(stored ? slot : -1);
  }
};

struct Equalizer : Component {
  Equalizer(int id, bool saveResult) : id(id), saveResult(saveResult) {}
  int id;
  bool saveResult;
  mutable int saves = 0;
  bool save(OutputStorage &storage) const override {
    if (++saves != 1 || storage.getFilter() || storage.getCancelHook() ||
        storage.getLock())
      throw std::logic_error("unexpected storage state");
    std::cout << "save|" << id << '|' << storage.getMode() << '\n';
    storage.getWriter().setValue("equalizer",
                                 static_cast<Core::int64>(71 + id));
    return saveResult;
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 6)
    return 1;
  const std::string selectorArg = argv[1];
  const std::string roster = argv[2];
  const bool saveResult = std::string(argv[3]) == "1";
  const char *name = argv[4];
  const std::filesystem::path folder = argv[5];
  Sink sink;
  PresetNameCache cache("geq", FileName(argv[5]), 4, 0, sink);
  Services services(cache);
  NumericParam selector(selectorInfo);
  if (selectorArg != "~")
    selector.setValueFast(std::stof(selectorArg));
  Equalizer first(0, saveResult), second(1, saveResult);
  std::vector<Component *> equalizers;
  for (char entry : roster)
    equalizers.push_back(entry == 'x'   ? nullptr
                         : entry == '0' ? &first
                                        : &second);
  GeqPresetComponent component(
      services, {{equalizers.data(), static_cast<int>(equalizers.size())},
                 selectorArg == "~" ? nullptr : &selector});
  component.addParameters(presetParams, 2);
  component.getParameterByTag(2)->fromString(name, false);
  auto *identity = reinterpret_cast<PresetComponent::Delegate *>(&services);
  component.addDelegate(identity);

  const bool result = component.store();
  std::cout << "result|" << result << '\n';
  auto &io = FileIOManager::instance();
  if (result) {
    if (services.notifications != std::vector<int>{0})
      return 2;
    for (int i = 0; i < 1000 && services.notifications.size() == 1; ++i) {
      io.idle();
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    if (services.notifications != std::vector<int>{0, 0})
      return 3;
    Core::CString64 cachedName;
    Core::CString32 category;
    cache.getPresetInfo(cachedName, category, 0);
    auto entry = std::filesystem::directory_iterator(folder);
    if (entry == std::filesystem::directory_iterator())
      return 4;
    Attributes attributes(AttributeAllocator::getDefault());
    if (!ArchiveUtils::loadFromFile(attributes, entry->path().c_str()))
      return 5;
    if (++entry != std::filesystem::directory_iterator())
      return 6;
    std::cout << "persist|" << cachedName.str() << '|' << category.str() << '|'
              << attributes.getInt("equalizer") << '\n';
  } else if (!services.notifications.empty() ||
             !std::filesystem::is_empty(folder)) {
    return 7;
  }
  component.removeDelegate(identity);
  io.terminate();
}
