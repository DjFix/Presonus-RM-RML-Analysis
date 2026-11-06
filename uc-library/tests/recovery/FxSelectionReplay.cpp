#include "presonus/panel/FxPresetComponent.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace presonus::panel {
struct PresetCacheAccess {
  static void clean(Presonus::Panel::PresetNameCache &c) { c.dirty = false; }
  static auto &observers(Presonus::Panel::PresetNameCache &c) {
    return c.observers;
  }
};
struct PresetTestAccess {
  static auto &registered(Presonus::Panel::PresetComponent &p) {
    return p.registeredCaches;
  }
};
struct FxPresetTestAccess {
  static void select(Presonus::Panel::FxPresetComponent &fx,
                     Presonus::Panel::FXPresetRecallComponent *p) {
    fx.currentChild = p;
  }
};
} // namespace presonus::panel
namespace {
using namespace Presonus::Panel;
using namespace Core::Portable;
using presonus::panel::PresetCacheAccess;
BEGIN_PARAMINFO(baseParams)
PARAM_INT_(0, "slot", -100, 100, 0, "", "", 0, 0, "Slot", nullptr),
    PARAM_STRING_(1, "name", 0, "Name", nullptr),
    PARAM_STRING_(2, "edit", 0, "Edit", nullptr),
    PARAM_STRING_(100, "category", 0, "Category", nullptr) END_PARAMINFO
    BEGIN_PARAMINFO(selectionParams)
        PARAM_FLOAT_(13, "fx", -100, 101, 0, .001, "", "", 0, 0, "Fx",
                     nullptr) END_PARAMINFO BEGIN_PARAMINFO(childParams)
            PARAM_INT_(100, "loaded", 0, 98, 7, "", "", 0, 0, "Loaded",
                       nullptr) END_PARAMINFO struct Sink
    : PresetNameCache::ObserverSink {
  int calls = 0;
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    ++calls;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {
    ++calls;
  }
};
struct Services : presonus::panel::PresetApplicationServices {
  mutable int selectedCalls = 0;
  int selections = 0;
  int selectedSlot(const PresetComponent &p) const override {
    ++selectedCalls;
    return static_cast<int>(p.getParameterByTag(0)->getValue());
  }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    return false;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    std::abort();
  }
  const char *presetFolder(const PresetComponent &) const override {
    return "reverb";
  }
  void ensureNameManager() const override {}
  PresetNameCache *lookupCache(const char *) const override { std::abort(); }
  bool hasSelectedSlotParameter(const PresetComponent &p) const override {
    return p.getParameterByTag(0);
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    std::abort();
  }
  const char *emptyNameMarker() const override { return "* Empty Location *"; }
  void updateSelection(PresetComponent &) override { ++selections; }
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    std::abort();
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    std::abort();
  }
};
struct RecallServices : presonus::fx_preset_recall_port::FxRecallServices {
  FileName presetPath(unsigned, const char *) override { std::abort(); }
  void presetInfo(char *, int, unsigned, const char *) override {
    std::abort();
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    std::abort();
  }
};
struct Counter : ParamObserverBase {
  int count = 0;
  std::string *order = nullptr;
  char label = 0;
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kChanged) {
      ++count;
      if (order)
        *order += label;
    }
  }
};
std::string text(Parameter &p) {
  char b[256];
  p.toString(b, 256);
  return b;
}
void initReplay(PresetNameManager &manager, PresetNameCache &cache,
                Services &services) {
  const auto initial = PresetCacheAccess::observers(cache).count();
  {
    PresetComponent p(services);
    p.addParameters(baseParams, 4);
    p.sourcePortBindManager(manager);
    auto *identity = reinterpret_cast<PresetNameCache::Delegate *>(&p);
    auto &list = PresetCacheAccess::observers(cache);
    list.add(identity);
    list.add(identity);
    const int count = list.count();
    p.init();
    assert(list.count() == count && list[count - 1] == identity &&
           list[count - 2] == identity);
    assert(text(*p.getParameterByTag(1)) == "NAME");
    p.init();
    assert(list.count() == count);
    services.selectedCalls = 0;
    cache.cachePreset("CHANGED", "room", 0);
    assert(services.selectedCalls == 2);
    assert(text(*p.getParameterByTag(1)) == "CHANGED");
    assert(text(*p.getParameterByTag(2)) == "CHANGED");
    // Remove the deliberately injected duplicate; the real owner removes its
    // remaining registration and typed routing on destruction.
    list.remove(identity);
  }
  assert(PresetCacheAccess::observers(cache).count() == initial);
}
} // namespace
int main(int argc, char **argv) {
  if (argc >= 3 && std::string(argv[1]) == "init") {
    Sink sink;
    Services services;
    PresetNameCache cache("reverb", FileName(""), 99, 0, sink);
    PresetCacheAccess::clean(cache);
    cache.cachePreset("NAME", "room", 0);
    PresetNameCache *items[] = {&cache};
    PresetNameManager manager(items, 1);
    PresetComponent p(services);
    p.addParameters(baseParams, 4);
    p.sourcePortBindManager(manager);
    auto *self = reinterpret_cast<PresetNameCache::Delegate *>(&p);
    auto *external = reinterpret_cast<PresetNameCache::Delegate *>(0x1111);
    auto &list = PresetCacheAccess::observers(cache);
    for (char c : std::string(argv[2]))
      list.add(c == '1' ? self : external);
    p.init();
    for (int i = 0; i < list.count(); ++i)
      std::cout << (list[i] == self ? '1' : '2');
    std::cout << "|" << text(*p.getParameterByTag(1)) << '\n';
    // Keep one self registration for destructor and discard injected extras.
    while (list.count() > 1)
      list.removeAt(0);
    return 0;
  }
  if (argc >= 3 && std::string(argv[1]) == "lookup") {
    Sink sink;
    std::vector<std::unique_ptr<PresetNameCache>> storage;
    std::vector<PresetNameCache *> pointers;
    for (int i = 3; i < argc; ++i) {
      storage.push_back(
          std::make_unique<PresetNameCache>(argv[i], FileName(""), 0, 0, sink));
      pointers.push_back(storage.back().get());
    }
    PresetNameManager manager(pointers.data(),
                              static_cast<int>(pointers.size()));
    auto *result = manager.lookupCache(
        std::string(argv[2]) == "<null>" ? nullptr : argv[2]);
    int index = -1;
    for (unsigned i = 0; i < pointers.size(); ++i)
      if (pointers[i] == result)
        index = static_cast<int>(i);
    std::cout << index << '\n';
    return 0;
  }
  assert(argc == 5);
  Sink sink;
  Services services;
  RecallServices recalls;
  PresetNameCache empty(
      "", FileName("temp/recovery-work/fx-selection-no-files"), 99, 0, sink),
      reverb("reverb", FileName("temp/recovery-work/fx-selection-no-files"), 99,
             0, sink),
      delay("delay", FileName("temp/recovery-work/fx-selection-no-files"), 99,
            0, sink),
      duplicate("reverb", FileName("temp/recovery-work/fx-selection-no-files"),
                99, 0, sink);
  PresetNameCache *caches[] = {&empty, &reverb, &delay, &duplicate};
  PresetNameManager manager(caches, 4);
  for (auto *c : caches) {
    PresetCacheAccess::clean(*c);
    for (int i = 0; i < 99; ++i)
      c->cachePreset("NAME", "room", i);
  }
  assert(manager.lookupCache(nullptr) == &empty);
  assert(manager.lookupCache("") == &empty);
  assert(manager.lookupCache("reverb") == &reverb);
  assert(manager.lookupCache("Reverb") == nullptr);
  assert(manager.lookupCache("missing") == nullptr);
  initReplay(manager, reverb, services);
  reverb.cachePreset("NAME", "room", 0);
  Component values;
  values.addParameters(selectionParams, 1);
  auto *observed = values.getParameterByTag(13);
  observed->setValue(std::strtof(argv[1], nullptr), false);
  Component params;
  params.addParameters(baseParams, 4);
  auto &slot = *params.getParameterByTag(0);
  auto &name = *params.getParameterByTag(1);
  auto &edit = *params.getParameterByTag(2);
  auto &category = *params.getParameterByTag(100);
  FXPresetRecallComponent a(recalls, slot, slot, name, edit, category, "reverb",
                            0),
      b(recalls, slot, slot, name, edit, category, "delay", 2);
  a.addParameters(childParams, 1);
  b.addParameters(childParams, 1);
  FXPresetRecallComponent *children[] = {&a, &a, &b, &b};
  {
    FxPresetComponent fx(services, observed, children, 4);
    auto &base = *fx.sourcePortPreset();
    base.addParameters(baseParams, 4);
    base.sourcePortBindManager(manager);
    int old = std::atoi(argv[2]);
    presonus::panel::FxPresetTestAccess::select(fx, old < 0 ? nullptr
                                                            : children[old]);
    int msg = std::atoi(argv[3]), match = std::atoi(argv[4]);
    Counter names, edits;
    std::string order;
    names.order = &order;
    edits.order = &order;
    names.label = 'N';
    edits.label = 'E';
    base.getParameterByTag(1)->addObserver(&names);
    base.getParameterByTag(2)->addObserver(&edits);
    bool fault = false;
    try {
      if (msg == 3 && match) { // Exercise real CCL notification routing.
        observed->changed();
      } else
        fx.paramChanged(match ? observed : &slot, msg);
    } catch (const std::domain_error &) {
      fault = true;
    }
    int index = static_cast<int>(observed->getValue());
    bool processed = msg == 3 && match;
    std::string formatter =
        processed ? (index <= 1 ? "reverbnum" : "delaynum") : "none";
    // Registry may have no named app formatters; verify the exact provider
    // result.
    if (processed)
      assert(base.getParameterByTag(0)->getFormatter() ==
             Core::FormatterRegistry::find(formatter.c_str()));
    int mirror = processed && index >= 0 && index < 4 ? 7 : -1;
    assert(base.getParameterByTag(0)->getValue() == (mirror < 0 ? 0 : mirror));
    auto &registered = presonus::panel::PresetTestAccess::registered(base);
    std::string regs;
    for (int i = 0; i < registered.count(); ++i) {
      if (i)
        regs += ",";
      regs += registered[i] == &empty    ? ""
              : registered[i] == &reverb ? "reverb"
                                         : "delay";
    }
    assert(names.count == (processed && !fault ? 1 : 0));
    assert(edits.count == (processed && !fault ? 1 : 0));
    assert(order == (processed && !fault ? "NE" : ""));
    assert(services.selections == (mirror >= 0 ? 1 : 0));
    std::cout << formatter << '|' << mirror << '|' << fx.getPresetType() << '|'
              << regs << '|' << names.count << '|' << edits.count << '|'
              << fault << '\n';
    if (processed && !fault) {
      if (registered.count() == 0)
        base.init();
      auto *cache = manager.lookupCache(fx.getPresetType());
      cache->cachePreset("LIVE", "live", 7);
      assert(text(*base.getParameterByTag(1)) == "LIVE" &&
             text(*base.getParameterByTag(2)) == "LIVE");
      // Base-first edit handling still reaches the real composed tree.
      fx.paramChanged(base.getParameterByTag(0), 2);
      assert(services.selections >= 1);
    }
    base.getParameterByTag(1)->removeObserver(&names);
    base.getParameterByTag(2)->removeObserver(&edits);
  }
  assert(observed->observerList.count() == 0);
  for (auto *c : caches)
    assert(PresetCacheAccess::observers(*c).count() == 0);
  return 0;
}
