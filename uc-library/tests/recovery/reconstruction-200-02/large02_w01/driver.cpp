#include "presonus/reconstruction200/large02_w01.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using E = Presonus::Surface::SLMixerHandler;
using X = presonus::surface::SLMixerEncoderAccess;
std::vector<std::string> events;
bool capture = false;
void emit(std::string s) {
  if (capture)
    events.push_back(s);
}
float floating(unsigned v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}
class Parameter : public Core::Portable::NumericParam {
public:
  using NumericParam::NumericParam;
  std::string actor = "mapping";
  int tag = 0;
  void setValue(float v, bool edit) override {
    unsigned bits;
    std::memcpy(&bits, &v, 4);
    emit("[\"set\",\"" + actor + "\"," + std::to_string(tag) + "," +
         std::to_string(bits) + "," + std::to_string(edit) + "]");
    NumericParam::setValue(v, edit);
  }
};
std::string quoted(const char *text) {
  std::string result = "\"";
  for (; *text; ++text) {
    if (*text == '\\' || *text == '"')
      result += '\\';
    result += *text;
  }
  return result + "\"";
}
class TextParameter : public Core::Portable::StringParam {
public:
  using StringParam::StringParam;
  int tag = 0;
  void fromString(const char *text, bool edit) override {
    emit("[\"string\"," + std::to_string(tag) + "," + quoted(text) + "," +
         std::to_string(edit) + "]");
    StringParam::fromString(text, edit);
  }
};
class Items : public presonus::mapping::ItemOperations {
public:
  void fullOff(Presonus::MappingTable::Item &) override { std::abort(); }
  void inverseMode(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
  void enabled(Presonus::MappingTable::Item &, bool) override { std::abort(); }
  void immediate(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
};
class Mapping : public Presonus::IMappingController {
public:
  Core::Portable::Parameter *parameters[256]{};
  int meter = 0;
  int radio = -1;
  int bankOffset = 3;
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int first, int) const override {
    return first == 34 ? (meter > 0 ? meter + 33 : -1) : radio;
  }
  int getBankScrollingOffset() const override { return bankOffset; }
  Core::Portable::Parameter *getParamByTag(int tag) const override {
    emit("[\"param\"," + std::to_string(static_cast<unsigned>(tag)) + "]");
    return parameters[static_cast<unsigned>(tag) & 255];
  }
  Core::Portable::Parameter *getMainScreenParamByTag(int tag) const override {
    return parameters[128 + tag];
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void encoderChanged(int) const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int a, int b, int c, bool edit) override {
    emit("[\"radio\"," + std::to_string(a) + "," + std::to_string(b) + "," +
         std::to_string(c) + "," + std::to_string(edit) + "]");
  }
  void onDeviceDisconnected() override { std::abort(); }
};
class Fixture : public E {
public:
  const char *getName() const override { std::abort(); }
  void updateConnections() override { emit("[\"update\"]"); }
  void initialize(Core::Portable::Component *) override { std::abort(); }
  void setController(Presonus::IMappingController *) override { std::abort(); }
  void updatePanEncoderConnection() override { std::abort(); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override {
    std::abort();
  }
  void handleFootswitch(FootswitchMode, bool) override { std::abort(); }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  void paramChanged(Core::Portable::Parameter *, int) override { std::abort(); }
  void onSelectionChanged() override { std::abort(); }
  void onObjectChanged(ObjectChangeMessage) override { std::abort(); }
  void onComponentReplaced(const ReplaceArgs &) override { std::abort(); }
  void onEqEncoderModeChanged() override { std::abort(); }
  void onGeqScrollOffsetChanged() override { std::abort(); }
};
extern "C" void realReset(Presonus::DelayTimer *) asm(
    "__real__ZN8Presonus10DelayTimer5resetEv");
extern "C" void wrappedReset(Presonus::DelayTimer *) asm(
    "__wrap__ZN8Presonus10DelayTimer5resetEv");
extern "C" void wrappedReset(Presonus::DelayTimer *p) {
  emit("[\"reset\"]");
  realReset(p);
}
const Core::Portable::ParamList *localParameters = nullptr;
const Core::Portable::ParamList *eqParameters = nullptr;
extern "C" Core::Portable::Parameter *
realByTag(const Core::Portable::ParamList *,
          int) asm("__real__ZNK4Core8Portable9ParamList5byTagEi");
extern "C" Core::Portable::Parameter *
wrappedByTag(const Core::Portable::ParamList *,
             int) asm("__wrap__ZNK4Core8Portable9ParamList5byTagEi");
extern "C" Core::Portable::Parameter *
wrappedByTag(const Core::Portable::ParamList *p, int tag) {
  if (p == localParameters || p == eqParameters)
    emit("[\"local\"," + std::to_string(tag) + "]");
  return realByTag(p, tag);
}
extern "C" void
realColor(Presonus::MappingTable *, const char *, const char *) asm(
    "__real__ZN8Presonus12MappingTable15setControlColorEPKcS2_");
extern "C" void
wrappedColor(Presonus::MappingTable *, const char *, const char *) asm(
    "__wrap__ZN8Presonus12MappingTable15setControlColorEPKcS2_");
extern "C" void wrappedColor(Presonus::MappingTable *table, const char *name,
                             const char *color) {
  emit("[\"color\"," + quoted(name) + "," + quoted(color) + "]");
  realColor(table, name, color);
}
int main(int argc, char **argv) {
  if (argc != 12 + 256)
    return 2;
  int index = std::stoi(argv[1]);
  bool controller = std::stoi(argv[2]);
  int radio = std::stoi(argv[3]);
  bool present = std::stoi(argv[4]), component = std::stoi(argv[5]),
       longer = std::stoi(argv[7]);
  int saved = std::stoi(argv[8]);
  bool mixer = std::stoi(argv[9]), secondary = std::stoi(argv[10]);
  Core::Portable::ParamInfo infos[256]{};
  Mapping mapping;
  mapping.radio = radio;
  presonus::surface::SLMappingState state;
  localParameters = &state.parameters;
  Core::Portable::Component tree;
  std::vector<std::unique_ptr<Parameter>> mappingOwned;
  std::vector<long long> config;
  std::istringstream configInput(argv[11]);
  std::string item;
  while (std::getline(configInput, item, ','))
    config.push_back(std::stoll(item));
  if (config.size() != 17)
    return 5;
  mapping.bankOffset = config[2];
  mapping.meter = config[11];
  state.bankSwitchBlocked = config[12];
  Items items;
  Presonus::MappingTable mappingTable(nullptr, 0, items);
  state.mappingTable = &mappingTable;
  Core::Portable::Component bankComponents[5], secondaryTree, groupsTree;
  for (int i = 0; i < 5; ++i)
    state.banks[i] = &bankComponents[i];
  state.secondaryInputs = config[3] ? &secondaryTree : nullptr;
  state.groups = &groupsTree;
  groupsTree.addChild(new Core::Portable::Component("filtergroup"));
  groupsTree.addChild(new Core::Portable::Component("autofiltergroup"));
  for (int i = 0; i < config[1]; ++i)
    state.busGeqs.add(new Core::Portable::Component);
  Core::Portable::Component mainGeq[2];
  state.mainGeqs[0] = &mainGeq[0];
  state.mainGeqs[1] = &mainGeq[1];
  Presonus::Surface::EQPageComponent eqPage;
  eqParameters =
      &presonus::surface::PageObserverAccess::encoderParameters(eqPage);
  state.mixer = mixer ? &tree : nullptr;
  state.hasSecondaryMixer = secondary;
  for (int tag = 0; tag < 256; ++tag) {
    auto &info = infos[tag];
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = tag;
    info.minValue = -1e30f;
    info.maxValue = 1e30f;
    info.deltaValue = .01f;
    auto *p = new Parameter(info);
    p->NumericParam::setValue(floating(std::stoul(argv[12 + tag])), false);
    p->tag = tag;
    mapping.parameters[tag] = p;
    mappingOwned.emplace_back(p);
    if (present && (tag == 3 || tag == 5)) {
      auto *infoCopy = new Core::Portable::ParamInfo(info);
      infoCopy->type = Core::Portable::ParamInfo::kString;
      auto *local = new TextParameter(*infoCopy, true);
      local->tag = tag;
      state.parameters.add(local);
    } else if (present) {
      auto *local = new Parameter(info);
      local->actor = "local";
      local->tag = tag;
      local->NumericParam::setValue(floating(std::stoul(argv[12 + tag])),
                                    false);
      state.parameters.add(local);
    }
  }
  E::FootswitchMode unused{};
  (void)unused;
  Fixture handler;
  X::bind(handler, controller ? &mapping : nullptr);
  presonus::surface::SLMappingAccess::bind(handler, state);
  presonus::surface::SLMappingAccess::bindEq(handler,
                                             config[0] ? &eqPage : nullptr);
  Core::Portable::ParamInfo eqInfo{};
  eqInfo.type = Core::Portable::ParamInfo::kFloat;
  eqInfo.tag = 1000;
  eqInfo.minValue = -1e30f;
  eqInfo.maxValue = 1e30f;
  auto *eqParam = new Parameter(eqInfo);
  eqParam->NumericParam::setValue(floating(std::stoul(argv[12 + 255])), false);
  presonus::surface::PageObserverAccess::encoderParameters(eqPage).add(eqParam);
  X::savedMeterMode(handler) = saved;
  presonus::timing::DelayTimerAccess::set(X::timer(handler),
                                          {0, 1, longer ? 1 : 0, 1.f, false});
  Core::Portable::ParamInfo textInfo{};
  textInfo.type = Core::Portable::ParamInfo::kString;
  textInfo.tag = 600;
  // String fixture uses the real CCL component-owned parameter API.
  if (present && index == 11) {
    tree.addParameters(&textInfo, 1);
    tree.getParameterByTag(600)->fromString(argv[6], false);
  }
  E::StripAssignData stripData;
  stripData.bankOffset = static_cast<int>(0xeeeeeeeeU);
  stripData.mix = static_cast<int>(0xddddddddU);
  stripData.inputs = true;
  Core::Portable::Component channel;
  Core::Portable::Parameter *pan =
                                reinterpret_cast<Core::Portable::Parameter *>(
                                    0xdead),
                            *link =
                                reinterpret_cast<Core::Portable::Parameter *>(
                                    0xbeef);
  auto addParam = [&](Core::Portable::Component &c, int tag, unsigned bits) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = tag;
    info.minValue = -1e30f;
    info.maxValue = 1e30f;
    c.addParameters(new Core::Portable::ParamInfo(info), 1, true);
    c.getParameterByTag(tag)->setValue(floating(bits), false);
  };
  if (index == 1) {
    for (int i = 0; i < 16; ++i) {
      auto *bus = new Core::Portable::Component;
      addParam(*bus, 21, std::stoul(argv[12 + 201]));
      auto *info = new Core::Portable::ParamInfo{};
      info->type = Core::Portable::ParamInfo::kString;
      info->tag = 600;
      std::strcpy(info->name, "username");
      bus->addParameters(info, 1, true);
      bus->getParameterByTag(600)->fromString(argv[6], false);
      bankComponents[4].addChild(bus);
    }
  }
  if (index == 20) {
    addParam(channel, 21, config[4]);
    if (config[8])
      addParam(channel, 411, config[7]);
    for (int tag : {19, 20, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249,
                    250, 251, 252, 253, 254, 255})
      addParam(channel, tag, 0);
    for (int i = 0; i < 16; ++i) {
      auto *bus = new Core::Portable::Component;
      addParam(*bus, 21, config[5]);
      addParam(*bus, 411, config[6]);
      bankComponents[4].addChild(bus);
    }
  }
  if (index == 16 || index == 18)
    infos[static_cast<unsigned>(config[13]) & 255].tag = config[13];
  events.clear();
  capture = true;
  int result = 0;
  if (index == 5)
    result = handler.getCurrentMix();
  else if (index == 9)
    result = handler.getSelectedBank();
  else if (index == 8 || index == 12) {
    result = index == 8 ? handler.showAutoGroups() : handler.showPeakHold();
  } else if (index == 11)
    result = handler.isValidGroup(component ? &tree : nullptr);
  else if (index == 7)
    handler.E::onIdle();
  else if (index == 19)
    handler.E::onModifiersChanged();
  else if (index == 10) {
    auto *p = handler.getSelectedGeq();
    result = 0;
    for (int n = 0; n < state.busGeqs.count(); ++n)
      if (p == state.busGeqs.at(n))
        result = 1000 + n;
    for (int n = 0; n < 2; ++n)
      if (p == state.mainGeqs[n])
        result = 2000 + n;
  } else if (index == 15)
    result = handler.getEqEncoderMode();
  else if (index == 17)
    result = handler.getStripAssignData(stripData);
  else if (index == 20)
    handler.getChannelPanAndLinkParams(channel, &pan, &link);
  else if (index == 18)
    handler.E::onMappingParamChanged(
        mapping.parameters[static_cast<unsigned>(config[13]) & 255]);
  else if (index == 16)
    result = handler.E::handleMappingRadioGroup(
        mapping.parameters[static_cast<unsigned>(config[13]) & 255]);
  else if (index == 1) {
    E::StripAssignData data;
    data.mix = config[14];
    handler.updateSelectedMix(data);
  } else
    return 4;
  capture = false;
  std::cout << "{\"result\":" << result << ",\"trace\":[";
  for (size_t j = 0; j < events.size(); ++j) {
    if (j)
      std::cout << ',';
    std::cout << events[j];
  }
  std::cout << "]";
  if (index == 18)
    std::cout << ",\"meterFlag\":" << int(state.meterModeTwo);
  if (index == 17) {
    std::cout << ",\"data\":[" << static_cast<unsigned>(stripData.bankOffset)
              << ',' << static_cast<unsigned>(stripData.mix) << ','
              << int(stripData.inputs) << ",[";
    for (int n = 0; n < stripData.lists.count(); ++n) {
      if (n)
        std::cout << ',';
      auto *p = stripData.lists.at(n);
      unsigned id = 0;
      for (int k = 0; k < 5; ++k)
        if (p == &bankComponents[k])
          id = 0x304000 + k * 0x100;
      if (p == &secondaryTree)
        id = 0x305100;
      for (int k = 0; k < 2; ++k)
        if (p == groupsTree.getChild(k))
          id = 0x308000 + k * 0x100;
      std::cout << id;
    }
    std::cout << "]]";
  }
  if (index == 20) {
    auto identify = [&](Core::Portable::Parameter *p) {
      if (p == reinterpret_cast<Core::Portable::Parameter *>(0xdead))
        return 0xdeadU;
      if (p == reinterpret_cast<Core::Portable::Parameter *>(0xbeef))
        return 0xbeefU;
      if (!p)
        return 0U;
      return 0x360000U + static_cast<unsigned>(p->getTag()) * 4U;
    };
    std::cout << ",\"pan\":" << identify(pan) << ",\"link\":" << identify(link);
  }
  std::cout << "}\n";
  for (int i = 0; i < state.busGeqs.count(); ++i)
    delete state.busGeqs.at(i);
}
