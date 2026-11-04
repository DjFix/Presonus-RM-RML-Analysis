#include "presonus/panel/FXPresetRecallComponent.hpp"
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
const ParamInfo numericInfo =
    PARAM_FLOAT(0, "n", -1000, 1000, 0, 1, nullptr, nullptr, 0, 0);
const ParamInfo stringInfo = PARAM_STRING(0, "s", 0);
std::vector<std::string> trace;
struct Observer : ParamObserverBase {
  std::string key;
  explicit Observer(const char *key) : key(key) {}
  void paramChanged(Parameter *p, int message) override {
    if (message == Parameter::kChanged && key != "slot") {
      char text[256];
      p->toString(text, sizeof(text));
      trace.push_back(key + ":" + text);
    }
    if (message == Parameter::kEdit && key == "slot")
      trace.push_back("set:" + std::to_string(static_cast<int>(p->getValue())) +
                      ":1");
  }
};
struct Services : presonus::fx_preset_recall_port::FxRecallServices {
  std::string path;
  presonus::fx_preset_recall_port::FxRecallCache cache;
  bool hasCache = true;
  FileName presetPath(unsigned int index, const char *) override {
    trace.push_back("path:" + std::to_string(index));
    return FileName(path.c_str());
  }
  void presetInfo(char *text, int size, unsigned int index,
                  const char *) override {
    trace.push_back("info:" + std::to_string(index));
    std::string name = "preset-" + std::to_string(index);
    std::snprintf(text, size, "%s", name.c_str());
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    return hasCache ? &cache : nullptr;
  }
};
struct IdleChild : Component {
  int count = 0;
  void onIdle() override { ++count; }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 15)
    return 2;
  std::string method = argv[1];
  Observer labelObserver("label"), nameObserver("name"), slotObserver("slot");
  NumericParam slot(numericInfo), loaded(numericInfo), type(numericInfo);
  slot.setValue(std::stof(argv[2]));
  loaded.setValue(std::stof(argv[3]));
  type.setValue(std::stof(argv[4]));
  StringParam label(stringInfo), name(stringInfo);
  label.fromString("initial");
  name.fromString("initial");
  label.addObserver(&labelObserver);
  name.addObserver(&nameObserver);
  slot.setController(&slotObserver);
  Services services;
  services.path = argv[6];
  services.hasCache = std::atoi(argv[12]);
  Presonus::Panel::FXPresetRecallComponent c(
      services, slot, loaded, label, name, type, "fx", std::atoi(argv[5]));
  if (std::atoi(argv[10]))
    services.cache.delegates.add(&c);
  int childCount = std::atoi(argv[9]);
  // The native test-double list and real CCL list contain the same identity
  // order.
  Parameter *params[] = {&slot, &loaded, &label, &name, &type};
  // addParameters owns its real CCL objects; test identities use these rather
  // than inventing a Core component/provider implementation.
  for (int i = 0; i < childCount; ++i)
    c.addParameters(&numericInfo, 1);
  IdleChild *idle = new IdleChild;
  c.addChild(idle);
  int arg = std::atoi(argv[7]), result = -999;
  FileName path;
  if (method == "onIdle")
    c.onIdle();
  else if (method == "getSlotNum")
    result = c.getSlotNum();
  else if (method == "cacheUpdated") {
    // The native body does not read this reference; no object/layout assertion.
    alignas(void *) unsigned char opaque[sizeof(void *)] = {};
    c.cacheUpdated(
        *reinterpret_cast<Presonus::Panel::PresetNameCache *>(opaque), arg,
        "cache-name", "unused");
  } else if (method == "isSlotEmpty")
    result = c.isSlotEmpty(arg);
  else if (method == "isChildParameter") {
    Parameter &p = (arg < childCount) ? *c.getParameterAt(arg) : *params[arg];
    result = c.isChildParameter(p);
  } else if (method == "paramChanged")
    c.paramChanged(params[arg], std::atoi(argv[8]));
  else if (method == "getFileName")
    result = c.getFileName(arg, path);
  else if (method == "getFxName")
    c.getFxName(name, arg);
  else if (method == "init")
    c.init();
  else if (method == "updateFxName")
    c.updateFxName();
  else
    return 3;
  std::cout << "name=" << name.getText() << "\nlabel=" << label.getText()
            << "\nslot=" << slot.getValue()
            << "\nregistered=" << services.cache.delegates.count()
            << "\nidle=" << idle->count << '\n';
  if (result != -999)
    std::cout << "return=" << result << '\n';
  if (method == "getFileName")
    std::cout << "path=" << path.str() << '\n';
  for (auto &item : trace)
    std::cout << "trace=" << item << '\n';
}
