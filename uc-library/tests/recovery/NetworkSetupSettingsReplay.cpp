#include "core/portable/corepersistence.h"
#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
std::vector<std::string> events;
struct Parameters : Component {
  void add(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct List : ListParam {
  using ListParam::ListParam;
  void setValue(float v, bool edit) override {
    if (edit)
      events.push_back("[\"set7\"," + std::to_string(v) + ",1]");
    ListParam::setValue(v, edit);
  }
};
struct Numeric : NumericParam {
  using NumericParam::NumericParam;
  bool capture = false;
  const presonus::surface::midi_port::State *observedMidi = nullptr;
  void setValue(float v, bool edit) override {
    if (capture)
      events.push_back("[\"set17\"," + std::to_string(v) + "," +
                       std::to_string(edit) + "," +
                       std::to_string(observedMidi->activeMapping) + "]");
    NumericParam::setValue(v, edit);
  }
};
struct MidiServices : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override {
    throw std::logic_error("unused");
  }
  bool recordParameterPresent() override { throw std::logic_error("unused"); }
  float recordParameterValue() override { throw std::logic_error("unused"); }
  void updateRecordMapping(bool) override { throw std::logic_error("unused"); }
  bool idleSlotPresent(unsigned) override { throw std::logic_error("unused"); }
  void invokeIdleSlot(unsigned) override { throw std::logic_error("unused"); }
};
struct Dependencies : presonus::surface::SurfaceNetworkDependencies {
  Presonus::Surface::MidiMixerHandler &midi;
  explicit Dependencies(Presonus::Surface::MidiMixerHandler &m) : midi(m) {}
  int mappingCount() const override {
    events.push_back("[\"sync\",7,0," +
                     std::to_string(midi.getActiveMapping()) + "]");
    return midi.countMappings();
  }
  const char *mappingName(int) const override { return "mapping"; }
  int kind(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {
    throw std::logic_error("unused");
  }
  const char *host(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  int targetType() const override { throw std::logic_error("unused"); }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    throw std::logic_error("unused");
  }
  void acquire(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void release(Presonus::UC::NetworkItem *, bool) override {
    throw std::logic_error("unused");
  }
  void *component(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void *mixerCast(void *) override { throw std::logic_error("unused"); }
  void *dawCast(void *) override { throw std::logic_error("unused"); }
  void setMixer(void *) override { throw std::logic_error("unused"); }
  void setDAW(void *) override { throw std::logic_error("unused"); }
  void setTransport(void *) override { throw std::logic_error("unused"); }
  void itemInfo(int, Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {
    throw std::logic_error("unused");
  }
  void setNetworkRoot(Component *) override {
    throw std::logic_error("unused");
  }
  void selectModelItem(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  int wiredAssignMode() const override { throw std::logic_error("unused"); }
  void configureNetwork(const char *) override {
    throw std::logic_error("unused");
  }
  void resumeAdaptors() override { throw std::logic_error("unused"); }
  void enableNetwork(bool) override { throw std::logic_error("unused"); }
  void setupLocalIP() override { throw std::logic_error("unused"); }
};
std::string decode(std::string x) { return x == "-" ? "" : x; }
} // namespace
int main() {
  int method, index, section, flags, count, optional, present;
  float value;
  std::string saved, key, sectionName;
  while (std::cin >> method >> index >> section >> saved >> flags >> key >>
         sectionName >> count >> optional >> value >> present) {
    saved = decode(saved);
    key = decode(key);
    sectionName = decode(sectionName);
    events.clear();
    Parameters params;
    const char *initial[] = {"None"};
    const ParamInfo li = PARAM_LIST(7, "daw", initial, 0, 0);
    const ParamInfo ni = PARAM_FLOAT(30, "target", -100000, 100000, 0, 0,
                                     nullptr, nullptr, 0, 0);
    const ParamInfo wi =
        PARAM_FLOAT(24, "wired", -100000, 100000, 0, 0, nullptr, nullptr, 0, 0);
    const ParamInfo oi =
        PARAM_FLOAT(17, "optional", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
    const ParamInfo mi =
        PARAM_FLOAT(0, "mixer", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
    List list(li);
    Numeric target(ni), wired(wi), option(oi), mixer(mi);
    for (int i = 0; i < 6; ++i)
      list.appendString("initial");
    params.add(&list);
    params.add(&target);
    if (present) {
      params.add(&wired);
      params.add(&mixer);
    }
    if (optional)
      params.add(&option);
    target.setValue(value, false);
    wired.setValue(value, false);
    option.capture = true;
    presonus::surface::midi_port::State midiState;
    midiState.mappingCount = count;
    option.observedMidi = &midiState;
    MidiServices midiServices;
    Presonus::Surface::MidiMixerHandler midi(midiState, midiServices);
    Dependencies deps(midi);
    presonus::surface::SurfaceNetworkProvider provider;
    Presonus::DelayTimer timer(0.f);
    presonus::surface::SurfaceNetworkState state{params, deps, provider, timer};
    SettingFile settings;
    state.settings = &settings;
    state.settingsSection = sectionName.c_str();
    state.midiHandler = &midi;
    if (section)
      settings.getSection(sectionName.c_str()).set(key.c_str(), saved.c_str());
    settings.setDirty(false);
    Presonus::Surface::NetworkSetupComponent component(state);
    if (method == 3) {
      component.loadSettings();
      // Regression of the reused dependency uses actual CCL list
      // implementation.
      if (list.getStringCount() != count + 1 ||
          list.getValue() != state.selectedMidiMapping + 1)
        throw std::logic_error("syncListParam regression");
      std::cout << "{\"selected\":" << state.selectedMidiMapping
                << ",\"active\":" << midi.getActiveMapping() << ",\"events\":[";
      for (size_t i = 0; i < events.size(); ++i) {
        if (i)
          std::cout << ',';
        std::cout << events[i];
      }
      std::cout << "]}";
    } else if (method == 4 || method == 6) {
      bool result = false;
      if (method == 4)
        component.storeSelected(key.c_str(), index, flags);
      else
        result = component.isStoredItem(key.c_str(), index);
      auto *s = settings.getAttributes(sectionName.c_str());
      const char *v = s ? s->getString(key.c_str()) : nullptr;
      std::cout << "{\"saved\":" << std::quoted(v ? v : "")
                << ",\"section\":" << int(s != nullptr)
                << ",\"dirty\":" << int(settings.isDirty());
      if (method == 6)
        std::cout << ",\"result\":" << int(result);
      std::cout << '}';
    } else {
      int result = method == 5
                       ? int(component.getSelectedMixerParam() == &mixer)
                   : method == 7 ? component.getTargetType()
                                 : component.getWiredNetworkAssignMode();
      std::cout << "{\"result\":" << result << '}';
    }
    std::cout << '\n';
    params.detach(&list);
    params.detach(&target);
    if (present) {
      params.detach(&wired);
      params.detach(&mixer);
    }
    if (optional)
      params.detach(&option);
  }
}
