#include "presonus/surface/GroupsEditPageComponent.hpp"
#include <array>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Core::Portable;
using Presonus::Surface::GroupsEditPageComponent;

namespace {
ParamInfo *info(int type, int tag, const char *name) {
  auto *result = new ParamInfo{};
  result->type = type;
  result->tag = tag;
  std::strncpy(result->name, name, sizeof(result->name) - 1);
  result->minValue = -100000.f;
  result->maxValue = 100000.f;
  return result;
}
class OwnedComponent : public Component {
public:
  void add(Parameter *parameter) { paramList.add(parameter); }
};

struct Scenario : presonus::surface::GroupsEditDependencies,
                  presonus::surface::GroupsPageDependencies,
                  presonus::page::Bindings {
  std::array<int, 23> values{};
  std::vector<std::string> trace;
  std::map<Parameter *, int> parameterIds;
  std::map<Component *, int> componentIds;
  std::vector<std::unique_ptr<OwnedComponent>> componentsOwned;
  std::array<Core::Vector<Component *>, 4> lists;
  std::array<std::unique_ptr<Parameter>, 32> slots;
  std::array<AliasParam *, 16> assignment{};
  std::array<AliasParam *, 16> names{};
  std::unique_ptr<StringParam> groupName;
  std::unique_ptr<NumericParam> event;
  presonus::surface::GroupsPageState groupsState;
  Presonus::Surface::GroupsPageComponent groupsPage{groupsState, *this};
  Presonus::PageComponent pageComponent{this, *this};
  OwnedComponent group;
  OwnedComponent slaveGroup;
  OwnedComponent navigation;
  // State must be destroyed before groups/channels so alias observers detach.
  presonus::surface::GroupsEditState state;
  GroupsEditPageComponent target{state, *this};

  Parameter *numeric(int id, int tag, OwnedComponent *owner = nullptr) {
    auto *p = new NumericParam(*info(ParamInfo::kFloat, tag, "numeric"), true);
    parameterIds[p] = id;
    if (owner)
      owner->add(p);
    return p;
  }
  Parameter *string(int id, int tag, const char *text,
                    OwnedComponent *owner = nullptr) {
    auto *p = new StringParam(*info(ParamInfo::kString, tag, "text"), true);
    p->fromString(text, false);
    parameterIds[p] = id;
    if (owner)
      owner->add(p);
    return p;
  }
  Component *channel(int id) {
    auto component = std::make_unique<OwnedComponent>();
    if (id != values[20])
      string(id, 1, ("Channel" + std::to_string(id)).c_str(), component.get());
    auto *result = component.get();
    componentIds[result] = id;
    componentsOwned.push_back(std::move(component));
    return result;
  }
  Scenario(char **argv) {
    for (int i = 0; i != 23; ++i)
      values[i] = static_cast<int>(std::stoll(argv[i]));
    state.mixerAvailable = values[0];
    state.listOffset = values[9];
    groupsState.selection = 3;
    componentIds[&group] = 1;
    componentIds[&slaveGroup] = 2;
    for (int tag = 600; tag < 1200; ++tag) {
      numeric(10000 + tag, tag, &group)->setValue(1.f);
      numeric(20000 + tag, tag, &slaveGroup)->setValue(1.f);
    }
    if (values[18])
      numeric(9000, 24, &navigation);
    if (values[17])
      state.navigation = &navigation;
    if (values[14])
      state.parameters.add(string(7000, 1007, argv[24]));
    if (values[15])
      groupName.reset(static_cast<StringParam *>(string(8000, 42, argv[23])));
    event.reset(static_cast<NumericParam *>(numeric(6000, values[12])));
    std::uint32_t bits = static_cast<std::uint32_t>(values[13]);
    float f;
    std::memcpy(&f, &bits, sizeof f);
    // Deliberately use the provider fast setter to preserve NaN/infinity tests.
    event->setValueFast(f);
    for (int list = 0; list < 4; ++list)
      for (int i = 0; i < values[4 + list]; ++i)
        lists[list].add(channel((list + 1) * 100 + i));
    for (int i = 0; i < values[8]; ++i)
      state.items.add({channel(500 + i), &group, 646 + i});
    for (int i = 0; i != 16; ++i) {
      if (values[19] != i + 1) {
        if (values[21] == i + 1) {
          slots[i * 2].reset(numeric(30000 + i, 2000 + i));
        } else {
          assignment[i] = new AliasParam(
              *info(ParamInfo::kAlias, 2000 + i, "assign"), true);
          slots[i * 2].reset(assignment[i]);
          if (values[22])
            assignment[i]->setOriginal(group.getParameterByTag(1000));
        }
        names[i] =
            new AliasParam(*info(ParamInfo::kAlias, 3000 + i, "name"), true);
        slots[i * 2 + 1].reset(names[i]);
      }
    }
  }
  ~Scenario() override {
    // Explicitly detach aliases before the group/channel providers are
    // destroyed.
    for (auto &slot : slots)
      slot.reset();
  }
  presonus::surface::GroupsEditSelection findGroupsPage() override {
    trace.push_back("findPage:groups");
    return {&groupsPage, values[2] ? &group : nullptr,
            values[3] ? &slaveGroup : nullptr};
  }
  bool hasSlaveMixer() override {
    trace.push_back("hasSlave");
    return values[1];
  }
  Core::ConstVector<Component *> components(const char *name,
                                            bool slave) override {
    trace.push_back(std::string("components:") + name + (slave ? ":1" : ":0"));
    int index = std::strcmp(name, "line") == 0       ? (slave ? 1 : 0)
                : std::strcmp(name, "fxreturn") == 0 ? 2
                                                     : 3;
    return {lists[index].getItems(), lists[index].count()};
  }
  Parameter *findParameter(const char *name) override {
    trace.push_back(std::string("find:") + name);
    if (std::strcmp(name, "group_name") == 0)
      return groupName.get();
    const std::string text(name);
    auto split = text.find_last_of('_');
    const int index = std::stoi(text.substr(split + 1)) - 1;
    return slots[index * 2 + (text.find("_name_") != std::string::npos)].get();
  }
  void startTextInput(Parameter *, const char *title,
                      GroupsEditPageComponent &) override {
    trace.push_back(std::string("start:") + title);
  }
  void pageOnShow(bool visible) override {
    trace.push_back(std::string("onShow:") + (visible ? "1" : "0"));
  }
  Presonus::PageComponent &page() override { return pageComponent; }
  void connect(const char *path, Parameter *parameter) override {
    trace.push_back(std::string("connect:") + path + ":" +
                    std::to_string(parameter ? parameterIds.at(parameter) : 0));
  }
  void refreshList() override {
    throw std::runtime_error("unexpected refresh");
  }
  void doselect() override { trace.push_back("deSelect"); }
  void observeGroup(Component *) override {
    throw std::runtime_error("unexpected observe");
  }
  void *castOwner(void *, int) const override {
    return const_cast<Scenario *>(this);
  }
  const void *currentPage(void *) const override {
    const_cast<Scenario *>(this)->trace.push_back("visible");
    return values[16] ? &pageComponent : nullptr;
  }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
  int id(Parameter *p) { return p ? parameterIds.at(p) : 0; }
  static std::string text(Parameter *p) {
    char text[256]{};
    if (p)
      p->toString(text, sizeof text);
    return text;
  }
  void output(int result) {
    std::cout << "{\"offset\":" << state.listOffset << ",\"result\":" << result
              << ",\"items\":[";
    for (int i = 0; i < state.items.count(); ++i) {
      if (i)
        std::cout << ',';
      const auto &item = state.items[i];
      std::cout << '[' << componentIds.at(item.channel) << ','
                << componentIds.at(item.group) << ',' << item.tag << ']';
    }
    std::cout << "],\"slots\":[";
    for (int i = 0; i < 16; ++i) {
      if (i)
        std::cout << ',';
      std::cout << '['
                << (assignment[i] ? id(assignment[i]->getOriginal()) : -1)
                << ',' << (names[i] ? id(names[i]->getOriginal()) : -1) << ','
                << (assignment[i] ? int(assignment[i]->isEnabled()) : -1)
                << ']';
    }
    std::cout << "],\"input\":"
              << std::quoted(text(state.parameters.byTag(1007)))
              << ",\"name\":" << std::quoted(text(groupName.get()))
              << ",\"navigation\":"
              << (navigation.getParameterByTag(24)
                      ? navigation.getParameterByTag(24)->getValue()
                      : 0)
              << ",\"event_bits\":";
    const float eventValue = event->getValue();
    std::uint32_t eventBits;
    std::memcpy(&eventBits, &eventValue, sizeof eventBits);
    std::cout << eventBits
              << ",\"group_value\":" << group.getParameterByTag(646)->getValue()
              << ",\"selection\":" << groupsState.selection << ",\"trace\":[";
    for (std::size_t i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << std::quoted(trace[i]);
    }
    std::cout << "]}\n";
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 27)
    return 2;
  Scenario scenario(argv + 2);
  const std::string method(argv[1]);
  int result = 0;
  if (method == "buildItemsList")
    scenario.target.buildItemsList();
  else if (method == "paramChanged")
    scenario.target.paramChanged(scenario.event.get(), scenario.values[11]);
  else if (method == "updateFilterAssignments")
    scenario.target.updateFilterAssignments();
  else if (method == "getMaxListOffset")
    result = scenario.target.getMaxListOffset();
  else if (method == "textInputFinished")
    scenario.target.textInputFinished(scenario.values[10]);
  else if (method == "setListOffset")
    scenario.target.setListOffset(scenario.values[10]);
  else if (method == "deleteGroup")
    scenario.target.deleteGroup();
  else if (method == "addListOffset")
    scenario.target.addListOffset(scenario.values[10]);
  else if (method == "rename")
    scenario.target.rename();
  else if (method == "onShow")
    scenario.target.onShow(scenario.values[10]);
  else
    return 2;
  scenario.output(result);
}
