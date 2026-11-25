#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "presonus/mixer/FXComponent.hpp"
#include "presonus/panel/FXPresetRecallComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Core::Portable;
using Presonus::Panel::PresetNameCache;
namespace {
using Trace = std::vector<std::string>;
Trace trace;
const Attributes *archiveAttributes = nullptr;

void expect(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

BEGIN_PARAMINFO(infos)
PARAM_FLOAT(0, "slot", 0, 10, 1, 1, nullptr, 0, 0, 0),
    PARAM_FLOAT(1, "loaded", 0, 10, 0, 1, nullptr, 0, 0, 0),
    PARAM_FLOAT(2, "type", 0, 8, 1, 1, nullptr, 0, 0, 0),
    PARAM_STRING(3, "type_name", 0), PARAM_STRING(4, "preset_name", 0),
    PARAM_FLOAT(5, "loaded_num", 0, 99, 6, 1, nullptr, 0, 0, PARAM_STORABLE),
    PARAM_FLOAT(6, "depth", 0, 99, 4, 1, nullptr, 0, 0,
                PARAM_STORABLE) END_PARAMINFO

    struct Slot : NumericParam {
  Slot() : NumericParam(infos[0]) {}
  mutable const char *nextRead = nullptr;
  ParamValue getValue() const override {
    const auto value = NumericParam::getValue();
    if (nextRead) {
      trace.push_back(nextRead + std::to_string(static_cast<int>(value)));
      nextRead = nullptr;
    }
    return value;
  }
};

struct Loaded : NumericParam {
  Loaded() : NumericParam(infos[1]) {}
  void setValue(ParamValue value, bool edit) override {
    trace.push_back("loaded:" + std::to_string(static_cast<int>(value)) + ":" +
                    std::to_string(edit));
    NumericParam::setValue(value, edit);
  }
};

struct CacheServices : presonus::fx_preset_recall_port::FxRecallServices,
                       PresetNameCache::ObserverSink {
  explicit CacheServices(const FileName &path)
      : cache("fx", path, 4, 0, *this) {}
  FileName presetPath(unsigned index, const char *category) override {
    expect(std::string(category) == "fx", "preset category");
    trace.push_back("path:" + std::to_string(index));
    return cache.getFileNameForSlot(index, true);
  }
  void presetInfo(char *name, int capacity, unsigned index,
                  const char *category) override {
    expect(std::string(category) == "fx", "preset category");
    trace.push_back("ui:" + std::to_string(index));
    Core::CString64 found;
    Core::CString32 group;
    expect(cache.getPresetInfo(found, group, index), "preset info");
    std::snprintf(name, capacity, "%s", found.str());
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *category) override {
    expect(std::string(category) == "fx", "cache category");
    return &delegates;
  }
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {}
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
  PresetNameCache cache;
  presonus::fx_preset_recall_port::FxRecallCache delegates;
};

struct App : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override { expect(false, "unexpected app call"); }
  std::uint32_t getTypeNumber() override {
    expect(false, "unexpected app call");
    return 0;
  }
  void updateTypeName() override { expect(false, "unexpected app call"); }
  void handleTypeChange(bool) override { expect(false, "unexpected app call"); }
};

struct DspBoundary : Presonus::dspcomponent_port::Boundary {
  DspBoundary(Slot &slot, const std::string &scenario)
      : slot(slot), scenario(scenario), marker(values.add(infos[5])),
        depth(values.add(infos[6])) {}
  int count(Presonus::Dsp::IController &) override { return unexpected(); }
  float value(Presonus::Dsp::IController &, int) override {
    return unexpected();
  }
  void set(Presonus::Dsp::IController &, int, float) override { unexpected(); }
  unsigned flags(Presonus::Dsp::IController &) override { return unexpected(); }
  void acknowledge(Presonus::Dsp::IController &) override { unexpected(); }
  bool readout(Presonus::Dsp::IController &, int) override {
    return unexpected();
  }
  void idle() override { unexpected(); }
  void changed(Parameter *, int) override { unexpected(); }

  int load(const InputStorage &storage) override {
    ++calls;
    expect(storage.getMode() == Core::ConstString("ignoreAltMemory"),
           "FX load adaptation mode");
    expect(storage.getFilter() && &storage.getAttributes() == archiveAttributes,
           "adapted storage identity");
    if (scenario == "failure")
      return 0;
    values.restoreValues(storage);
    if (scenario == "move") {
      slot.NumericParam::setValue(2, false);
      roster->at(1) = nullptr;
    }
    slot.nextRead = "live:";
    return 1;
  }

  int unexpected() {
    expect(false, "unexpected DSP call");
    return 0;
  }

  Slot &slot;
  const std::string &scenario;
  ParamList values;
  Parameter *marker;
  Parameter *depth;
  Core::Vector<Presonus::Mixer::FXComponent *> *roster = nullptr;
  int calls = 0;
};

struct Effect : Presonus::Mixer::FXComponent {
  Effect(presonus::mixer_fx::State &state, int index)
      : FXComponent(state), index(index) {}
  bool load(const InputStorage &storage) override {
    trace.push_back("fx:" + std::to_string(index));
    expect(storage.getMode().isEmpty() && storage.getFilter() &&
               !storage.getCancelHook() && !storage.getLock() &&
               !storage.getParentAttributes() &&
               &storage.getAttributes() == archiveAttributes,
           "recall storage at FX load");
    expect(storage.getAttributes().getFloat("depth") == 41 &&
               storage.getAttributes().getFloat("loaded_num") == 32,
           "saved attributes");
    return FXComponent::load(storage);
  }
  int index;
};

struct Fx {
  Fx(App &app, Slot &slot, NumericParam &type, Loaded &loaded,
     const std::string &scenario, int index)
      : boundary(slot, scenario), dsp("dsp", nullptr),
        load{dsp, *boundary.depth, *boundary.depth, *boundary.marker},
        state{owner, type, loaded, app}, effect(state, index) {
    dsp.bind(boundary);
    state.load = &load;
  }
  DspBoundary boundary;
  Presonus::DspComponent dsp;
  Component owner;
  presonus::mixer_fx::LoadState load;
  presonus::mixer_fx::State state;
  Effect effect;
};
} // namespace

extern "C" bool
__real__ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_10AttributesEPKcNS0_8Archiver6FormatEPNS0_18FileStorageContextEib(
    Attributes &, const char *, Archiver::Format, FileStorageContext *, int,
    bool);
extern "C" bool
__wrap__ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_10AttributesEPKcNS0_8Archiver6FormatEPNS0_18FileStorageContextEib(
    Attributes &attributes, const char *filename, Archiver::Format format,
    FileStorageContext *context, int size, bool inplace) {
  trace.push_back("archive");
  expect(format == Archiver::kJSON && !context && size == 0 && !inplace,
         "archive defaults");
  archiveAttributes = &attributes;
  return __real__ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_10AttributesEPKcNS0_8Archiver6FormatEPNS0_18FileStorageContextEib(
      attributes, filename, format, context, size, inplace);
}

int main(int argc, char **argv) {
  expect(argc == 4, "case arguments");
  int selected = std::stoi(argv[1]);
  std::string scenario = argv[2];
  FileName folder(argv[3]);
  CacheServices services(folder);
  const auto path = services.cache.buildFileName(1, "First", "", nullptr, true);
  Attributes attributes(AttributeAllocator::getDefault());
  attributes.set("loaded_num", 32.);
  attributes.set("depth", 41.);
  if (scenario == "malformed") {
    std::ofstream(path.str()) << "malformed";
  } else if (scenario != "missing") {
    expect(ArchiveUtils::saveToFile(path, attributes), "save test archive");
    const auto second =
        services.cache.buildFileName(2, "Second", "", nullptr, true);
    expect(ArchiveUtils::saveToFile(second, attributes), "save second archive");
  }

  Slot slot;
  Loaded loaded;
  NumericParam type(infos[2]);
  StringParam typeName(infos[3]), presetName(infos[4]);
  App app;
  Fx first(app, slot, type, loaded, scenario, 0);
  Fx second(app, slot, type, loaded, scenario, 1);
  Core::Vector<Presonus::Mixer::FXComponent *> roster;
  expect(roster.add(nullptr) && roster.add(nullptr), "allocate live roster");
  Presonus::Panel::FXPresetRecallComponent recall(
      services, slot, loaded, typeName, presetName, type, "fx", selected);
  recall.sourcePortBindEffects(roster);
  roster.at(0) = &first.effect;
  roster.at(1) = &second.effect;
  first.boundary.roster = second.boundary.roster = &roster;
  recall.init();
  trace.clear();
  slot.nextRead = "slot:";

  const auto previousName = presetName.getText();
  const auto previousType = typeName.getText();
  const bool success = recall.recallFxPreset();

  for (const auto &item : trace)
    std::cout << item << '\n';
  std::cout << "result:" << success << "\nloadedValue:" << loaded.getIntValue()
            << '\n';
  for (int at = 0; at < 2; ++at) {
    const auto &boundary = at == 0 ? first.boundary : second.boundary;
    expect(boundary.calls == (selected == at && scenario != "missing" &&
                              scenario != "malformed"),
           "one actual DSP load through selected FX");
    expect(boundary.marker->getIntValue() == 6, "loaded_num stays filtered");
    expect(boundary.depth->getIntValue() ==
               (success && selected == at ? 41 : 4),
           "ordinary parameter restore");
  }
  expect(typeName.getText() == (success ? "SMALL ROOM" : previousType.str()),
         "type display");
  expect(presetName.getText() ==
             (success && scenario == "move" ? "Second" : previousName.str()),
         "preset display");
  return 0;
}
