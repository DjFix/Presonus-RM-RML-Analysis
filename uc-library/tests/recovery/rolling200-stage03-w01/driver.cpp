#include "core/portable/coreattributes.h"
#include "presonus/MappingTable.hpp"
#include "presonus/StormMixSceneComponent.hpp"
#include "presonus/panel/FxPresetComponent.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
using namespace Core::Portable;
static int mode = -1;
static bool capture = false;
static std::vector<int> lookupTags;
static std::ostringstream events;
static Component *components[3]{};
static Parameter *params[3]{};
static int identity(Parameter *p) {
  for (int i = 0; i < 3; ++i)
    if (p == params[i])
      return i;
  std::abort();
}
static void require(bool v) {
  if (!v)
    std::abort();
}
static void event(std::string s) {
  if (capture) {
    if (events.tellp() > 0)
      events << ";";
    events << s;
  }
}
extern "C" Parameter *
realLookup(const Component *,
           int) asm("__real__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Parameter *wrapLookup(const Component *p, int tag) asm(
    "__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Parameter *wrapLookup(const Component *p, int tag) {
  if (capture && mode == 1)
    lookupTags.push_back(tag);
  if (capture && (mode == 2 || mode == 4)) {
    int i = 1;
    while (i < 3 && components[i] != p)
      ++i;
    require(i < 3);
    event("lookup:" + std::to_string(i) + ":" + std::to_string(tag));
  }
  return realLookup(p, tag);
}
extern "C" void realConnect(Presonus::MappingTable *, const char *, Parameter *,
                            const char *,
                            bool) asm("__real__"
                                      "ZN8Presonus12MappingTable7connectEPKcPN4"
                                      "Core8Portable9ParameterES2_b");
extern "C" void wrapConnect(Presonus::MappingTable *, const char *, Parameter *,
                            const char *,
                            bool) asm("__wrap__"
                                      "ZN8Presonus12MappingTable7connectEPKcPN4"
                                      "Core8Portable9ParameterES2_b");
extern "C" void wrapConnect(Presonus::MappingTable *t, const char *n,
                            Parameter *p, const char *s, bool b) {
  require(s == nullptr && !b);
  event("connect:" + std::to_string(n[0] - 'A') + ":" +
        std::to_string(identity(p)));
  realConnect(t, n, p, s, b);
}
extern "C" void
realColor(Presonus::MappingTable *, const char *, const char *) asm(
    "__real__ZN8Presonus12MappingTable15setControlColorEPKcS2_");
extern "C" void
wrapColor(Presonus::MappingTable *, const char *, const char *) asm(
    "__wrap__ZN8Presonus12MappingTable15setControlColorEPKcS2_");
extern "C" void wrapColor(Presonus::MappingTable *t, const char *n,
                          const char *c) {
  require(std::string(c) == "red");
  event("color:" + std::to_string(n[0] - 'A'));
  realColor(t, n, c);
}
extern "C" void realEnabled(Presonus::MappingTable *, const char *, bool) asm(
    "__real__ZN8Presonus12MappingTable17setControlEnabledEPKcb");
extern "C" void wrapEnabled(Presonus::MappingTable *, const char *, bool) asm(
    "__wrap__ZN8Presonus12MappingTable17setControlEnabledEPKcb");
extern "C" void wrapEnabled(Presonus::MappingTable *t, const char *n, bool s) {
  if (mode == 4)
    event("enabled:" + std::to_string(n[0] - 'A') + ":" + std::to_string(s));
  realEnabled(t, n, s);
}
// Deliberate Linux compiler ABI harness for an incomplete reference identity.
// No FocusInfo object, fields or C++ lifetime are fabricated or dereferenced.
extern "C" bool
focusABI(Presonus::Surface::MidiMixerHandler *, void *, Parameter *) asm(
    "_ZN8Presonus7Surface16MidiMixerHandler17getParamFocusInfoERNS_"
    "22MixerAssignmentHandler9FocusInfoEPN4Core8Portable9ParameterE");
struct Recall : presonus::scene_port::Recall {
  bool recall(unsigned int) const override { std::abort(); }
};
struct Store : presonus::scene_port::StoreDelegate {
  void enter(Presonus::StormMixSceneComponent &) override { std::abort(); }
  void leave(Presonus::StormMixSceneComponent &) override { std::abort(); }
};
struct PresetServices : presonus::panel::PresetApplicationServices {
  int selectedSlot(const Presonus::Panel::PresetComponent &) const override {
    std::abort();
  }
  bool slotEmpty(const Presonus::Panel::PresetComponent &,
                 unsigned) const override {
    std::abort();
  }
  void slotFileName(Core::CString256 &,
                    const Presonus::Panel::PresetComponent &,
                    unsigned) const override {
    std::abort();
  }
  const char *
  presetFolder(const Presonus::Panel::PresetComponent &) const override {
    return "";
  }
  void ensureNameManager() const override {}
  Presonus::Panel::PresetNameCache *lookupCache(const char *) const override {
    return nullptr;
  }
  bool hasSelectedSlotParameter(
      const Presonus::Panel::PresetComponent &) const override {
    std::abort();
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    std::abort();
  }
  const char *emptyNameMarker() const override { std::abort(); }
  void updateSelection(Presonus::Panel::PresetComponent &) override {
    std::abort();
  }
  int recallAttributes(Presonus::Panel::PresetComponent &, Attributes &,
                       bool) override {
    std::abort();
  }
  void notifyDelegate(Presonus::Panel::PresetComponent::Delegate *,
                      const Presonus::Panel::PresetComponent &, int,
                      bool) const override {
    std::abort();
  }
};
struct FxServices : presonus::fx_preset_recall_port::FxRecallServices {
  FileName presetPath(unsigned int, const char *) override { std::abort(); }
  void presetInfo(char *, int, unsigned int, const char *) override {
    std::abort();
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    std::abort();
  }
};
struct MidiServices : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override { std::abort(); }
  bool recordParameterPresent() override { std::abort(); }
  float recordParameterValue() override { std::abort(); }
  void updateRecordMapping(bool) override { std::abort(); }
  bool idleSlotPresent(unsigned) override { std::abort(); }
  void invokeIdleSlot(unsigned) override { std::abort(); }
};
struct ItemOps : presonus::mapping::ItemOperations {
  int count = 0;
  void fullOff(Presonus::MappingTable::Item &) override { std::abort(); }
  void inverseMode(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
  void enabled(Presonus::MappingTable::Item &, bool s) override {
    require(!s);
    ++count;
  }
  void immediate(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
};
struct Extended : presonus::mapping::ExtendedOperations {
  void blink(Presonus::MappingTable::Item &, const char *) override {
    std::abort();
  }
  const char *pageName(Presonus::IMainScreenPageController &) override {
    std::abort();
  }
  Presonus::Panel::Control *control(Presonus::MappingTable::Item &) override {
    return nullptr;
  }
  void control(Presonus::MappingTable::Item &,
               Presonus::Panel::Control *) override {
    std::abort();
  }
  Parameter *parameter(Presonus::MappingTable::Item &) override {
    std::abort();
  }
  int translateMode(const char *) override { std::abort(); }
  void bind(Presonus::Panel::Control &, Parameter *, int) override {
    std::abort();
  }
  Parameter *alternate(Presonus::Panel::Control &, bool) override {
    std::abort();
  }
  void alternate(Presonus::Panel::Control &, Parameter *, bool) override {
    std::abort();
  }
  bool hasLED(Presonus::Panel::Control &) override { std::abort(); }
  void color(Presonus::Panel::Control &, int) override { std::abort(); }
  const char *defaultColor(Presonus::MappingTable::Item &) override {
    std::abort();
  }
  void defaultColor(Presonus::MappingTable::Item &, const char *) override {
    std::abort();
  }
};
static const ParamInfo buttonInfos[] = {
    PARAM_INT(1, "one", 0, 10, 0, 0, 0, 0, 0),
    PARAM_INT(2, "two", 0, 10, 0, 0, 0, 0, 0),
    PARAM_INT(3, "three", 0, 10, 0, 0, 0, 0, 0)};
static const ParamInfo targetInfo[] = {
    PARAM_INT(7, "target", 0, 10, 0, 0, 0, 0, 0)};
static const ParamInfo aliasInfos[] = {
    PARAM_ALIAS(1, "a", 0), PARAM_ALIAS(2, "b", 0), PARAM_ALIAS(3, "c", 0)};
int main() {
  long long av, bv, cv, dv;
  while (std::cin >> mode >> av >> bv >> cv >> dv) {
    capture = false;
    events.str("");
    events.clear();
    int a = static_cast<int>(av), b = static_cast<int>(bv),
        c = static_cast<int>(cv), d = static_cast<int>(dv);
    if (mode == 0 || mode == 1) {
      Recall r;
      Store store;
      Presonus::StormMixSceneComponent object(r);
      object.configureStoreDelegate(&store);
      object.addParameters(buttonInfos, 3);
      object.getParameterByTag(1)->setValue(9, false);
      object.getParameterByTag(2)->setValue(8, false);
      object.getParameterByTag(3)->setValue(7, false);
      if (mode == 0) {
        object.setDelegate(
            reinterpret_cast<Presonus::StormMixSceneComponent::Delegate *>(
                static_cast<std::uintptr_t>(av)));
        object.setDelegate(
            reinterpret_cast<Presonus::StormMixSceneComponent::Delegate *>(
                static_cast<std::uintptr_t>(bv)));
        std::cout << mode << " "
                  << reinterpret_cast<std::uintptr_t>(
                         object.sourcePortDelegate())
                  << "\n";
      } else {
        PresetServices ps;
        Presonus::Panel::PresetComponent preset(ps);
        lookupTags.clear();
        capture = true;
        object.presetRecalled(preset, a);
        capture = false;
        require(lookupTags == std::vector<int>({2, 3, 4}));
        require(object.getParameterByTag(1)->getValue() == 9 &&
                object.getParameterByTag(2)->getValue() == 0 &&
                object.getParameterByTag(3)->getValue() == 0 &&
                object.recalledIndex() == UINT32_MAX);
        std::cout << mode << " clear\n";
      }
    } else if (mode == 2 || mode == 3) {
      FxServices services;
      NumericParam dummy(buttonInfos[0]);
      Presonus::Panel::FXPresetRecallComponent first(
          services, dummy, dummy, dummy, dummy, dummy, "reverb", 0),
          second(services, dummy, dummy, dummy, dummy, dummy, "reverb", 1);
      first.addParameters(targetInfo, 1);
      second.addParameters(targetInfo, 1);
      Presonus::Panel::FXPresetRecallComponent *items[] = {&first, nullptr,
                                                           &second};
      Presonus::Panel::FxPresetComponent object(items, 3);
      components[1] = &first;
      components[2] = &second;
      params[1] = first.getParameterByTag(7);
      params[2] = second.getParameterByTag(7);
      if (mode == 2) {
        auto &error = Core::ConstVector<
            Presonus::Panel::FXPresetRecallComponent *>::getError();
        auto *old = error;
        error = c == 1 ? &first : c == 2 ? &second : nullptr;
        capture = true;
        auto *result = object.getRecallParameter(a, b);
        capture = false;
        error = old;
        std::cout << mode << " " << identity(result) << " "
                  << (events.str().empty() ? "-" : events.str()) << "\n";
      } else {
        DefaultAllocatedAttributes attrs;
        attrs.set("sentinel", 17);
        auto count = attrs.countAttributes();
        bool result = object.recall(attrs, a);
        require(attrs.countAttributes() == count &&
                attrs.getInt("sentinel") == 17);
        std::cout << mode << " " << result << " unchanged\n";
      }
    } else {
      MidiServices service;
      presonus::surface::midi_port::State state;
      ItemOps ops;
      Extended extended;
      Component normal, alternate;
      normal.addParameters(targetInfo, 1);
      alternate.addParameters(targetInfo, 1);
      components[1] = &normal;
      components[2] = &alternate;
      params[1] = normal.getParameterByTag(7);
      params[2] = alternate.getParameterByTag(7);
      AliasParam aa(aliasInfos[0]), bb(aliasInfos[1]), cc(aliasInfos[2]);
      Presonus::MappingTable::Item ia(aa), ib(bb), ic(cc);
      presonus::mapping::Entry entries[] = {{"A", &ia}, {"B", &ib}, {"C", &ic}};
      Presonus::MappingTable table(entries, 3, ops);
      table.setExtendedOperations(extended);
      state.mappingTable = &table;
      state.normalParameters = &normal;
      state.alternateParameters = &alternate;
      Presonus::Surface::MidiMixerHandler object(state, service);
      if (mode == 4) {
        Presonus::Surface::MidiMixerHandler::MappingItem items[4]{};
        for (int i = 0; i < a; ++i) {
          items[i].name[0] = 'A' + i;
          items[i].tag = i == 0 ? -1 : i == 1 ? 7 : 65535;
          items[i].alternate = b & (1 << i) ? 255 : 0;
          items[i].disable = d & (1 << i) ? 255 : 0;
          items[i].color = c & (1 << i) ? "red" : nullptr;
        }
        capture = true;
        object.updateMapping(items);
        capture = false;
        AliasParam *aliases[] = {&aa, &bb, &cc};
        int disabled = 0;
        for (int i = 0; i < a; ++i) {
          Parameter *wanted =
              i == 1 ? (b & (1 << i) ? params[2] : params[1]) : nullptr;
          require(aliases[i]->getOriginal() == wanted);
          if (d & (1 << i))
            ++disabled;
        }
        require(ops.count == disabled);
        std::cout << mode << " " << (events.str().empty() ? "-" : events.str())
                  << "\n";
      } else if (mode == 5) {
        alignas(16) unsigned char bytes[128];
        std::memset(bytes, 0x5a, sizeof(bytes));
        bool result = focusABI(&object, bytes, b ? params[1] : nullptr);
        for (auto x : bytes)
          require(x == 0x5a);
        std::cout << mode << " " << result << " unchanged\n";
      } else {
        std::array<unsigned char, 44> descriptions[4]{};
        int expected = 0;
        for (int i = 0; i < a; ++i) {
          descriptions[i][0] = 'A' + i;
          descriptions[i][37] = b & (1 << i) ? 255 : 0;
          if (descriptions[i][37])
            ++expected;
        }
        state.controlDescriptions = descriptions;
        object.connect();
        require(ops.count == expected);
        std::cout << mode << " disable\n";
      }
    }
  }
}
