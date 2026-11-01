#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
using namespace Core::Portable;
using namespace presonus::surface;
struct Config {
  int method, mixer, handler, count, rows, offset, selected, visible, arg,
      category, nameMode, missing, presetNull;
};
struct Capture {
  std::vector<std::string> events;
  void add(std::string v) { events.push_back(v); }
};
struct Text : StringParam {
  Capture &capture;
  Text(const ParamInfo &i, Capture &c) : StringParam(i, true), capture(c) {}
  void fromString(const char *s, bool edit) override {
    capture.add("text:" + std::to_string(getTag()) + ":" + s);
    StringParam::fromString(s, edit);
  }
};
struct Value : NumericParam {
  Capture &capture;
  Value(const ParamInfo &i, Capture &c) : NumericParam(i, true), capture(c) {}
  void setValue(float v, bool edit) override {
    capture.add("value:" + std::to_string(getTag()) + ":" +
                std::to_string(static_cast<int>(v)));
    NumericParam::setValue(v, edit);
  }
};
struct Parameters : Component {
  void text(int tag, Capture &c) {
    auto *i = new ParamInfo PARAM_STRING(tag, "name", 0);
    paramList.add(new Text(*i, c));
  }
  void value(int tag, Capture &c) {
    auto *i = new ParamInfo PARAM_TOGGLE(tag, "selected", 0, nullptr, 0);
    paramList.add(new Value(*i, c));
  }
};
struct Boundary : PresetsPageDependencies {
  Config &c;
  Capture &t;
  PresetEntry entry{1, {}};
  Boundary(Config &c, Capture &t) : c(c), t(t) {
    entry.name = c.nameMode == 0   ? "Alpha"
                 : c.nameMode == 1 ? ""
                 : c.nameMode == 2 ? "* Empty Location *"
                                   : "prefix * Empty Location * suffix";
  }
  bool handlerAvailable() override {
    t.add("handler");
    return c.handler;
  }
  int count(int cat) override {
    t.add("count:" + std::to_string(cat));
    return c.count;
  }
  const PresetEntry *preset(int cat, int n) override {
    t.add("preset:" + std::to_string(cat) + ":" + std::to_string(n));
    return !c.presetNull && n >= 0 && n < c.count ? &entry : nullptr;
  }
  void reload(int cat) override { t.add("reload:" + std::to_string(cat)); }
  void defaultName(int cat, Core::CString128 &v) override {
    t.add("default:" + std::to_string(cat));
    v = "Generated";
  }
  void categoryName(int cat, Core::CString128 &v) override {
    t.add("category:" + std::to_string(cat));
    v = "Channel";
  }
  const char *emptyMarker() override { return "* Empty Location *"; }
  void baseShow(bool b) override {
    t.add("show:" + std::to_string(b));
    c.visible = b;
  }
  bool visible() override {
    t.add("visible:" + std::to_string(c.visible));
    return c.visible;
  }
  void connect(const char *name, Parameter *p) override {
    t.add(std::string("connect:") + name + ":" +
          std::to_string(p ? p->getTag() : -1));
  }
  void recallOptions(Core::CString256 &v) override {
    t.add("options");
    v = "opt";
  }
  void recall(const PresetEntry *, int cat,
              const Core::CString256 &v) override {
    t.add("recall:" + std::to_string(cat) + ":" + v.str());
  }
  void remove(const PresetEntry *, int cat) override {
    t.add("remove:" + std::to_string(cat));
  }
  void store() override { t.add("store"); }
  void startTextInput(Parameter *p, const char *s) override {
    t.add("input:" + std::to_string(p->getTag()) + ":" + s);
  }
};
int main(int argc, char **argv) {
  if (argc != 14)
    return 2;
  Config c{};
  int *fields[] = {&c.method,    &c.mixer,    &c.handler,  &c.count,
                   &c.rows,      &c.offset,   &c.selected, &c.visible,
                   &c.arg,       &c.category, &c.nameMode, &c.missing,
                   &c.presetNull};
  for (int i = 0; i < 13; ++i)
    *fields[i] = std::stoi(argv[i + 1]);
  Capture capture;
  Parameters params;
  for (int i = 0; i < c.rows; ++i) {
    params.text(i * 3, capture);
    params.value(i * 3 + 1, capture);
  }
  if (!c.missing)
    params.text(1006, capture);
  params.value(1004, capture);
  params.value(1005, capture);
  PresetsPageState state{c.category, c.rows,        c.offset,
                         c.selected, bool(c.mixer), params};
  Boundary boundary(c, capture);
  Presonus::Surface::PresetsPageComponent page(state, boundary);
  int result = 0;
  switch (c.method) {
  case 1:
    result = page.getSelectedPreset() ? 1 : 0;
    break;
  case 2:
    page.onShow(c.arg);
    break;
  case 3:
    result = page.getMaxListOffset();
    break;
  case 4:
    page.textInputFinished(c.arg);
    break;
  case 5:
    page.addListOffset(c.arg);
    break;
  case 6:
    page.recall();
    break;
  case 7:
    page.promptToStore();
    break;
  case 8:
    page.updatePresets();
    break;
  case 9:
    page.remove();
    break;
  case 10:
    page.onObjectChanged(
        static_cast<Presonus::IMixerComponentObserver::ObjectChangeMessage>(
            c.arg));
    break;
  default:
    return 3;
  }
  std::cout << "{\"result\":" << result << ",\"offset\":" << state.offset
            << ",\"selected\":" << state.selected << ",\"events\":[";
  bool first = true;
  for (const auto &s : capture.events) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << std::quoted(s);
  }
  std::cout << "]}\n";
}
