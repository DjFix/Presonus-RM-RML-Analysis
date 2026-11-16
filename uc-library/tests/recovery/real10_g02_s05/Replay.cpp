#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>
#include <vector>
namespace {
bool recording = false;
std::vector<std::string> events;
void event(const std::string &s) {
  if (recording)
    events.push_back(s);
}
struct Param final : Core::Portable::NumericParam {
  Param(int tag, float v, bool storable)
      : NumericParam(*make(tag, storable), true) {
    NumericParam::setValue(v, false);
  }
  static Core::Portable::ParamInfo *make(int tag, bool storable) {
    auto *i = new Core::Portable::ParamInfo{};
    i->type = Core::Portable::ParamInfo::kFloat;
    i->tag = tag;
    i->minValue = -10;
    i->maxValue = 10;
    i->flags = storable ? Core::Portable::ParamInfo::kStorable : 0;
    std::snprintf(i->name, sizeof(i->name), "p%d", tag);
    return i;
  }
  float getValue() const override {
    event("v" + std::to_string(getTag()));
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit) override {
    event("s" + std::to_string(getTag()));
    NumericParam::setValue(v, edit);
  }
};
struct Parameters final : Core::Portable::Component {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
};
struct Dependencies final : presonus::surface::PresetsPageDependencies {
  presonus::surface::PresetEntry entry{123, Core::CString128("Valid")};
  bool handlerAvailable() override { return true; }
  int count(int) override { return 1000; }
  const presonus::surface::PresetEntry *preset(int, int) override {
    return &entry;
  }
  void reload(int) override { throw 1; }
  void defaultName(int, Core::CString128 &) override { throw 1; }
  void categoryName(int, Core::CString128 &) override { throw 1; }
  const char *emptyMarker() override { return "EMPTY"; }
  void baseShow(bool) override { throw 1; }
  bool visible() override { return false; }
  void connect(const char *, Core::Portable::Parameter *) override { throw 1; }
  void recallOptions(Core::CString256 &) override { throw 1; }
  void recall(const presonus::surface::PresetEntry *, int,
              const Core::CString256 &) override {
    throw 1;
  }
  void remove(const presonus::surface::PresetEntry *, int) override { throw 1; }
  void store() override { throw 1; }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    event("prompt");
  }
};
struct Page final : Presonus::Surface::PresetsPageComponent {
  using PresetsPageComponent::PresetsPageComponent;
  void recall() override { event("recall"); }
  void remove() override { event("remove"); }
  void rowSelected() override {
    event("row");
    PresetsPageComponent::rowSelected();
  }
};
unsigned bits(float v) {
  unsigned u;
  std::memcpy(&u, &v, 4);
  return u;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  int tag = std::atoi(argv[1]), msg = std::atoi(argv[2]),
      rows = std::atoi(argv[4]), mask = std::atoi(argv[5]),
      included = std::atoi(argv[6]), storable = std::atoi(argv[7]);
  float value = std::strtof(argv[3], nullptr);
  Core::Portable::ParamInfo textInfo{};
  Parameters parameters;
  Dependencies dependencies;
  presonus::surface::PresetsPageState state{0, rows, 20, 4, true, parameters};
  Page page(state, dependencies);
  Param *changed = nullptr;
  for (int j = 0; j < rows; ++j)
    if (mask & (1 << j)) {
      auto *p = new Param(1 + 3 * j, tag == 1 + 3 * j && included ? value : 1.f,
                          storable);
      parameters.add(p);
      if (tag == 1 + 3 * j && included)
        changed = p;
    }
  std::unique_ptr<Param> external;
  if (!changed) {
    external = std::make_unique<Param>(tag, value, storable);
    changed = external.get();
  }
  textInfo.type = Core::Portable::ParamInfo::kString;
  textInfo.tag = 1006;
  std::strcpy(textInfo.name, "name");
  parameters.add(new Core::Portable::StringParam(textInfo));
  Core::Portable::Component baseline;
  baseline.paramChanged(changed, msg);
  recording = true;
  page.paramChanged(changed, msg);
  recording = false;
  std::printf("%d %d %u", state.selected, state.offset,
              bits(changed->NumericParam::getValue()));
  for (int j = 0; j < rows; ++j) {
    auto *p = parameters.getParameterByTag(1 + 3 * j);
    std::printf(" %u", p ? bits(p->getValue()) : 0xffffffffu);
  }
  std::printf(" | ");
  for (std::size_t j = 0; j < events.size(); ++j)
    std::printf("%s%s", j ? "," : "", events[j].c_str());
  std::puts("");
  std::printf("base %d\n", page.needsSave() == baseline.needsSave());
}
