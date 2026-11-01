#include "presonus/panel/PresetComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using Presonus::Panel::PresetComponent;
namespace presonus::panel {
struct PresetTestAccess {
  static auto &delegates(PresetComponent &component) {
    return component.delegates;
  }
};
} // namespace presonus::panel

namespace {
struct Observation {
  std::string name, edit = "untouched", category = "untouched";
  int resets = 0;
  std::vector<std::string> trace;
};
std::string jsonQuote(const std::string &s) {
  std::ostringstream out;
  out << std::quoted(s);
  return out.str();
}
class TextParameter : public Core::Portable::StringParam {
  Observation &observation;
  std::string &value;
  int tag;

public:
  TextParameter(const Core::Portable::ParamInfo &info, Observation &o,
                std::string &v, bool ownsInfo = false)
      : StringParam(info, ownsInfo), observation(o), value(v), tag(info.tag) {}
  void toString(char *buffer, int size) const override {
    std::strncpy(buffer, value.c_str(), size - 1);
    buffer[size - 1] = 0;
    observation.trace.push_back("[\"toString\"," + std::to_string(tag) + "," +
                                std::to_string(size) + "]");
  }
  void fromString(const char *text, bool edit) override {
    value = text;
    observation.trace.push_back("[\"fromString\"," + std::to_string(tag) + "," +
                                jsonQuote(value) + "," + std::to_string(edit) +
                                "]");
  }
  void resetValue(bool edit) override {
    value = "<default>";
    ++observation.resets;
    observation.trace.push_back("[\"reset\"," + std::to_string(tag) + "," +
                                std::to_string(edit) + "]");
  }
};
struct Services : presonus::panel::PresetApplicationServices {
  Observation &o;
  int slot, empty, result, ready;
  std::string marker, name, category, filename;
  mutable std::vector<std::string> callbacks;
  Services(Observation &o, char **argv)
      : o(o), slot(std::atoi(argv[5])), empty(std::atoi(argv[6])),
        result(std::atoi(argv[8])), ready(std::atoi(argv[9])), marker(argv[4]),
        name(argv[14]), category(argv[15]), filename(argv[16]) {}
  int selectedSlot(const PresetComponent &) const override {
    o.trace.push_back("[\"slot\"]");
    return slot;
  }
  bool slotEmpty(const PresetComponent &, unsigned s) const override {
    o.trace.push_back("[\"empty\"," + std::to_string(s) + "]");
    return empty;
  }
  void slotFileName(Core::CString256 &out, const PresetComponent &,
                    unsigned s) const override {
    o.trace.push_back("[\"filename\"," + std::to_string(s) + "]");
    out = filename.c_str();
  }
  const char *presetFolder(const PresetComponent &) const override {
    o.trace.push_back("[\"folder\"]");
    return "fixture";
  }
  void ensureNameManager() const override {}
  Presonus::Panel::PresetNameCache *lookupCache(const char *) const override {
    o.trace.push_back("[\"lookup-cache\"]");
    return reinterpret_cast<Presonus::Panel::PresetNameCache *>(1);
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    return ready;
  }
  void presetInfo(Core::CString64 &n, Core::CString32 &c, int s,
                  const char *) const override {
    o.trace.push_back("[\"preset-info\"," + std::to_string(s) + "]");
    n = name.c_str();
    c = category.c_str();
  }
  const char *emptyNameMarker() const override { return marker.c_str(); }
  void updateSelection(PresetComponent &) override {
    o.trace.push_back("[\"update\"]");
  }
  int recallAttributes(PresetComponent &, Core::Portable::Attributes &,
                       bool edit) override {
    o.trace.push_back("[\"recall\"," + std::to_string(edit) + "]");
    return result;
  }
  void notifyDelegate(PresetComponent::Delegate *d, const PresetComponent &,
                      int s, bool stored) const override {
    std::string row = "[\"" + std::string(stored ? "stored" : "recalled") +
                      "\"," +
                      std::to_string(reinterpret_cast<std::uintptr_t>(d)) +
                      "," + std::to_string(s) + "]";
    callbacks.push_back(row);
    o.trace.push_back(row);
  }
};
class Component : public PresetComponent {
  std::vector<Core::Portable::ParamInfo> infos;

public:
  Component(Services &s, Observation &o, int present)
      : PresetComponent(s), infos(3) {
    int tags[] = {1, 2, 100};
    std::string *values[] = {&o.name, &o.edit, &o.category};
    for (int i = 0; i < 3; ++i) {
      infos[i].clear();
      infos[i].type = Core::Portable::ParamInfo::kString;
      infos[i].tag = tags[i];
      if (present & (1 << i))
        paramList.add(new TextParameter(
            *new Core::Portable::ParamInfo(infos[i]), o, *values[i], true));
    }
  }
};
void rows(const std::vector<std::string> &v) {
  std::cout << '[';
  for (std::size_t i = 0; i < v.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << v[i];
  }
  std::cout << ']';
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 17)
    return 2;
  Observation o;
  o.name = argv[3];
  Services services(o, argv);
  Component component(services, o, std::atoi(argv[2]));
  auto &delegates = presonus::panel::PresetTestAccess::delegates(component);
  std::istringstream items(argv[10]);
  std::string item;
  while (std::getline(items, item, ','))
    if (!item.empty())
      component.addDelegate(
          reinterpret_cast<PresetComponent::Delegate *>(std::stoul(item)));
  const int method = std::atoi(argv[1]);
  int result = 0;
  bool cache = false;
  Core::CString128 output;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kString;
  info.tag = std::atoi(argv[11]);
  TextParameter changed(info, o, o.name);
  auto *target =
      reinterpret_cast<PresetComponent::Delegate *>(std::stoul(argv[12]));
  switch (method) {
  case 1:
    component.paramChanged(&changed, std::atoi(argv[13]));
    break;
  case 2:
    component.updatePresetName();
    break;
  case 3:
    component.presetStored();
    break;
  case 4:
    cache = component.getCache() != nullptr;
    break;
  case 5:
    component.updateEditName();
    break;
  case 6:
    result = component.getCurrentPresetName(output);
    break;
  case 7:
    result = component.recall();
    break;
  case 8:
    component.removeDelegate(target);
    break;
  case 9:
    component.presetRecalled();
    break;
  case 10:
    component.addDelegate(target);
    break;
  default:
    return 2;
  }
  std::cout << "{\"observed\":{\"name\":" << jsonQuote(o.name)
            << ",\"edit\":" << jsonQuote(o.edit)
            << ",\"category\":" << jsonQuote(o.category)
            << ",\"resets\":" << o.resets << ",\"delegates\":[";
  for (int i = 0; i < delegates.count(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << reinterpret_cast<std::uintptr_t>(delegates.at(i));
  }
  std::cout << "],\"callbacks\":";
  rows(services.callbacks);
  if (method == 6 || method == 7)
    std::cout << ",\"return\":" << result;
  if (method == 6)
    std::cout << ",\"output\":" << jsonQuote(output.str());
  if (method == 4)
    std::cout << ",\"cache_found\":" << (cache ? "true" : "false");
  std::cout << "},\"trace\":";
  rows(o.trace);
  std::cout << "}\n";
}
