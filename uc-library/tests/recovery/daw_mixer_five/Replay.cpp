#undef NDEBUG
#include "presonus/ColorMapping.hpp"
#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"
#include "presonus/DAWClientComponent.hpp"
#include "presonus/IMainScreenPageController.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using namespace Presonus;
using namespace Core::Portable;
namespace {
std::map<Parameter *, std::string> identities;
std::map<std::string, std::string> inputs;
int number(const char *key, int fallback = 1) {
  auto p = inputs.find(key);
  return p == inputs.end() ? fallback : std::stoi(p->second);
}
std::string id(Parameter *p) {
  if (!p)
    return "-";
  assert(identities.count(p));
  return identities.at(p);
}
const char *safe(const char *s) { return s ? s : "-"; }
void addParams(Component &component, int identity) {
  for (int tag : {0, 2, 3, 4, 5, 6, 8, 9, 10, 13, 14, 15, 17, 18, 21, 1000}) {
    ParamInfo info =
        PARAM_FLOAT(0, "value", -10000, 10000, 0, 0.1f, 0, 0, 0, 0);
    info.tag = tag;
    if (tag == 5)
      info.type = ParamInfo::kColor;
    component.addParameters(&info, 1, true);
    auto *p = component.getParameterByTag(tag);
    identities[p] = std::to_string(identity) + ":" + std::to_string(tag);
    if (tag == 5)
      ColorParam::cast(p)->setColor(0xffff0000, false);
    if (tag == 18)
      p->setValue(2, false);
  }
}
struct Channel : DAWChannel {
  explicit Channel(int identity, const char *type) {
    addParams(*this, identity);
    ParamInfo info = PARAM_STRING(22, "type", 0);
    addParameters(&info, 1, true);
    cachedParameters_[channelStateCache] = getParameterByTag(22);
    cachedParameters_[channelStateCache]->fromString(type, false);
  }
};
struct Group : DAWChannelGroup {
  Group() {
    static constexpr ParamInfo info =
        PARAM_INT(0, "count", -10, 100, 4, 0, 0, 0, 0);
    addParameters(&info, 1);
    cachedParameter_ = getParameterByTag(0);
  }
  ~Group() override {
    while (children.contains(nullptr))
      children.remove(nullptr);
  }
  void rawChild(Component *p) { children.add(p); }
  void used(int n) { cachedParameter_->setValue(n, false); }
};
struct Dependencies : presonus::surface::DAWMixerDependencies {
  [[noreturn]] static void unexpected() { std::abort(); }
  DAWChannel *focusChannel() override { unexpected(); }
  DAWChannel *mainChannel() override { unexpected(); }
  int selectedMix() const override { unexpected(); }
  bool showStripMeters() const override { unexpected(); }
  Component *component(DAWChannel *) const override { unexpected(); }
  DAWDeviceFolder *folder(DAWChannel *, bool) const override { unexpected(); }
  int usedCount(DAWDeviceFolder *) const override { unexpected(); }
  Component *slot(DAWDeviceFolder *, int) const override { unexpected(); }
  const char *channelType(DAWChannel *) const override { unexpected(); }
  void connect(const char *, Parameter *, const char *, bool) override {
    unexpected();
  }
  void assignChannels() override { unexpected(); }
  void assignControlLinkTargets() override { unexpected(); }
  void assignSelectedChannelTargets() override { unexpected(); }
  void assignFlexStrip() override { unexpected(); }
};
struct Controller : IMappingController {
  ParamList parameters;
  Controller() {
    for (int tag : {4, 5, 6}) {
      ParamInfo info = PARAM_FLOAT(0, "selector", 0, 1, 0, 1, 0, 0, 0, 0);
      info.tag = tag;
      parameters.add(info, true);
      parameters.byTag(tag)->setValue(number("selection", 0) == tag ? 1 : 0,
                                      false);
    }
  }
  int getModifiers() const override { return number("modifiers", 0); }
  int getRadioValue(int first, int) const override {
    return first == 0
               ? number("radio", 0)
               : (first == 13 ? number("mix", 33) : number("meterMode", 34));
  }
  int getBankScrollingOffset() const override { return number("bank", 0); }
  Parameter *getParamByTag(int tag) const override {
    return parameters.byTag(tag);
  }
  Parameter *getMainScreenParamByTag(int) const override { return nullptr; }
  bool isDisplayEncoderLocked() const override { return number("locked", 1); }
  bool areFadersLockedToMainMix() const override { return false; }
  void encoderChanged(int) const override {}
  void onSelectedChannelChanged() override {}
  void selectedChannelUpdated() override {}
  void setRadioGroup(int, int, int, bool) override {}
  void onDeviceDisconnected() override {}
};
// Test-only panel endpoint; all application and Core work remains real.
struct Extended : presonus::mapping::ExtendedOperations {
  int lastColor = -1;
  void blink(MappingTable::Item &, const char *) override { std::abort(); }
  const char *pageName(IMainScreenPageController &p) override {
    return p.getPageName();
  }
  Panel::Control *control(MappingTable::Item &i) override { return i.control; }
  void control(MappingTable::Item &i, Panel::Control *p) override {
    i.control = p;
  }
  Parameter *parameter(MappingTable::Item &i) override { return i.alias; }
  int translateMode(const char *p) override {
    return MappingTable::Item::translateMode(p);
  }
  void bind(Panel::Control &c, Parameter *p, int m) override {
    c.setParameter(p, m);
  }
  Parameter *alternate(Panel::Control &, bool) override { std::abort(); }
  void alternate(Panel::Control &, Parameter *, bool) override { std::abort(); }
  bool hasLED(Panel::Control &) override { return true; }
  void color(Panel::Control &, int c) override { lastColor = c; }
  const char *defaultColor(MappingTable::Item &i) override {
    return i.defaultColor;
  }
  void defaultColor(MappingTable::Item &i, const char *p) override {
    i.defaultColor = p;
  }
} extended;
struct Colors : presonus::mapping::ColorOperations {
  int map(Core::Color c) override { return ColorMapping::mapColorToEnum(c); }
  Core::Color map(const char *) override { std::abort(); }
  int enumFromString(const char *p, int fallback) override {
    return ColorMapping::enumFromString(Core::ConstString(p),
                                        static_cast<RGBLedColors>(fallback));
  }
} colors;
struct Header : IMainScreenPageController {
  bool connectParameter(const char *name, Parameter *p) override {
    bindings[name] = p;
    return true;
  }
  void disconnectMappables() override { bindings.clear(); }
  const char *getPageName() const override { return "header"; }
  std::map<std::string, Parameter *> bindings;
};
} // namespace
extern "C" void
__real__ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b(
    MappingTable *, const char *, Parameter *, const char *, bool);
extern "C" void
__wrap__ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b(
    MappingTable *table, const char *name, Parameter *parameter,
    const char *mode, bool force) {
  // Observe the app call, then execute actual MappingTable and CCL AliasParam.
  if (std::string(name).rfind("page:", 0) != 0 && !table->findItem(name))
    table->addItem(name);
  __real__ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b(
      table, name, parameter, mode, force);
  auto *item = table->findItem(name);
  if (item && item->alias)
    assert(item->alias->getOriginal() == parameter);
  std::cout << "connect|" << name << '|' << id(parameter) << '|' << safe(mode)
            << '|' << force << '\n';
}
extern "C" void __real__ZN8Presonus12MappingTable15setControlColorEPKcS2_(
    MappingTable *, const char *, const char *);
extern "C" void __wrap__ZN8Presonus12MappingTable15setControlColorEPKcS2_(
    MappingTable *table, const char *name, const char *color) {
  Panel::Control endpoint(0);
  auto *item = table->findItem(name);
  assert(item);
  item->control = &endpoint;
  extended.lastColor = -1;
  __real__ZN8Presonus12MappingTable15setControlColorEPKcS2_(table, name, color);
  assert(extended.lastColor == colors.enumFromString(color, 17));
  item->control = nullptr;
  std::cout << "color|" << name << '|' << safe(color) << '\n';
}
int main(int argc, char **argv) {
  assert(argc >= 2);
  std::string method = argv[1];
  for (int i = 2; i < argc; ++i) {
    std::string arg = argv[i];
    auto equal = arg.find('=');
    assert(equal != std::string::npos);
    inputs[arg.substr(0, equal)] = arg.substr(equal + 1);
  }
  DAWClientComponent client;
  Group main, input, output;
  Controller controller;
  auto populate = [](Group &g, int first = 1) {
    if (first == 0)
      g.rawChild(nullptr);
    else if (first == 2)
      g.rawChild(new Component("wrong"));
    else
      g.rawChild(new Channel(1, "AudioInput"));
    g.rawChild(new Component("wrong"));
    g.rawChild(new Channel(3, "AudioEffect"));
    g.rawChild(new Channel(4, "AudioGroup"));
  };
  populate(main, number("first", 1));
  populate(input);
  populate(output);
  main.used(number("used", 4));
  auto *focus = new Channel(1, "AudioInput");
  client.addChild(focus);
  client.setFocusChannel(number("focus", 1) ? focus : nullptr);
  auto *controls = new Component("controls");
  if (number("control", 1))
    client.addChild(controls);
  if (number("populated", 1))
    for (int i = 0; i < 25; ++i) {
      auto *p = new Component(("p" + std::to_string(i)).c_str());
      addParams(*p, 10 + i);
      controls->addChild(p);
    }
  MappingTable table;
  table.setExtendedOperations(extended);
  MappingTable::setColorOperations(colors);
  Header header;
  table.useTypedPageControllers();
  table.addMainScreenPage(&header);
  Dependencies dependencies;
  presonus::surface::DAWMixerState state;
  state.client = number("client", 1) ? &client : nullptr;
  state.mappingTable = &table;
  state.mappingController = number("controller", 1) ? &controller : nullptr;
  state.mainGroup = number("group", 1) ? &main : nullptr;
  state.inputGroup = &input;
  state.outputGroup = &output;
  state.shift = number("shift", 0);
  state.stripMeters = number("meters", 0);
  Surface::DAWMixerHandler handler(dependencies, state);
  for (int tag = 0; tag < 4; ++tag) {
    ParamInfo info = PARAM_FLOAT(0, "automation", 0, 1, 0, 1, 0, 0, 0, 0);
    info.tag = tag;
    handler.automationParameters().add(info, true);
  }
  if (method == "getMainChannel")
    std::cout << "main|" << (handler.getMainChannel() != nullptr) << '\n';
  else if (method == "assignControlLinkTargets")
    handler.assignControlLinkTargets();
  else if (method == "assignSelectedChannelTargets")
    handler.assignSelectedChannelTargets();
  else if (method == "assignStripTargets")
    handler.assignStripTargets(number("group", 1) ? &input : nullptr,
                               number("offset", 0), inputs["filter"].c_str());
  else if (method == "assignChannels")
    handler.assignChannels();
  else
    return 2;
  if (method == "assignSelectedChannelTargets" && state.client &&
      state.mappingController) {
    for (int tag = 0; tag < 4; ++tag)
      assert(handler.automationParameters().byTag(tag)->getValue() ==
             (number("focus", 1) && tag == 1 ? 1.f : 0.f));
    for (auto name : {"channel_name", "channel_info", "channel_number"})
      assert(header.bindings.count(name));
  }
  if (!number("control", 1))
    delete controls;
}
