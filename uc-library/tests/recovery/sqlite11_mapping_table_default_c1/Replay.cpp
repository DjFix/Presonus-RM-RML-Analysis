#include "presonus/MappingTable.hpp"
#include "presonus/panel/switch_control.hpp"

#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>
#include <utility>

namespace {
using Presonus::MappingTable;
using presonus::panel::ControlAccess;
using Presonus::Panel::SwitchControl;
using presonus::panel_binding::SwitchAccess;
using presonus::surface_panel_port::LEDLifecycleAccess;

void require(bool truth) {
  if (!truth)
    std::abort();
}

struct BaseConstruction : MappingTable {
  BaseConstruction() : MappingTable() {}
};

class InjectedOperations final : public presonus::mapping::ItemOperations {
public:
  void fullOff(MappingTable::Item &item) override { record(item, 1); }
  void inverseMode(MappingTable::Item &item, bool state) override {
    record(item, state ? 2 : 3);
  }
  void enabled(MappingTable::Item &item, bool state) override {
    record(item, state ? 4 : 5);
  }
  void immediate(MappingTable::Item &item, bool state) override {
    record(item, state ? 6 : 7);
  }

  int calls = 0, last = 0;
  MappingTable::Item *address = nullptr;

private:
  void record(MappingTable::Item &item, int event) {
    address = &item;
    last = event;
    ++calls;
  }
};

void exercise(MappingTable &table) {
  require(!table.sourcePortItemAt(0) && !table.findItem("") &&
          !table.findItem("first") && table.sourcePortPageCount() == 0 &&
          !table.findPage("unknown"));
  table.setControlFullOff("absent");
  table.setControlInverseMode("absent", true);
  table.setControlEnabled("absent", false);
  table.setControlImmediate("absent", true);
  table.addItem("first");
  auto *item = table.findItem("first");
  require(item && item == table.sourcePortItemAt(0) &&
          !table.sourcePortItemAt(1));
  require(item->alias && item->alias->getOriginal() == nullptr &&
          std::string_view(item->alias->getName()) == "hwparam" &&
          item->alias->getType() == Core::Portable::ParamInfo::kAlias &&
          item->defaultColor.isEmpty() && !item->control);
  table.setControlFullOff("first");
  table.setControlInverseMode("first", true);
  table.setControlEnabled("first", false);
  table.setControlImmediate("first", true);

  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1.f;
  Core::Portable::NumericParam parameter(info);
  parameter.setValue(.75f);
  SwitchControl control(3, 0, false);
  require(control.setParameter(&parameter, 0));
  item->control = &control;

  table.setControlEnabled("first", false);
  require(SwitchAccess::disabled(control) && parameter.getValue() == .75f);
  table.setControlEnabled("first", true);
  require(!SwitchAccess::disabled(control) && parameter.getValue() == .75f);
  table.setControlImmediate("first", true);
  require(control.isImmediate());
  table.setControlImmediate("first", false);
  require(!control.isImmediate());
  table.setControlInverseMode("first", true);
  require(LEDLifecycleAccess::on(control) == 0 &&
          LEDLifecycleAccess::off(control) == 1);
  table.setControlInverseMode("first", false);
  require(LEDLifecycleAccess::on(control) == 1 &&
          LEDLifecycleAccess::off(control) == 0);
  table.setControlFullOff("first");
  require(ControlAccess::lastLevel(control) == 3);
  item->control = nullptr;

  MappingTable copy(table);
  MappingTable moved(std::move(copy));
  moved.addItem("after move");
  require(table.findItem("after move") == moved.findItem("after move") &&
          moved.findItem("first") == item);
  for (int i = 2; i < 1024; ++i) {
    const auto name = "item" + std::to_string(10000 + i);
    table.addItem(name.c_str());
  }
  for (int i = 0; i < 1024; ++i)
    require(table.sourcePortItemAt(i) && table.sourcePortItemAt(i)->alias);
  require(!table.sourcePortItemAt(1024));
  table.addItem("before capacity");
  require(!table.findItem("before capacity"));
}

void exerciseInjected() {
  InjectedOperations recorder;
  MappingTable owned(MappingTable::OwnedItems{}, recorder);
  owned.addItem("owned");
  owned.setControlEnabled("owned", true);
  require(recorder.calls == 1 && recorder.last == 4 &&
          recorder.address == owned.findItem("owned"));

  MappingTable::Item item("borrowed", nullptr);
  const presonus::mapping::Entry entry{item.name, &item};
  MappingTable table(&entry, 1, recorder);
  MappingTable copy(table);
  MappingTable moved(std::move(copy));
  moved.addItem("unavailable");
  require(moved.findItem("borrowed") == &item &&
          !moved.findItem("unavailable"));
  moved.setControlFullOff("borrowed");
  require(recorder.calls == 2 && recorder.last == 1 &&
          recorder.address == &item);
  moved.setControlInverseMode("borrowed", false);
  require(recorder.calls == 3 && recorder.last == 3);
  moved.setControlImmediate("borrowed", false);
  require(recorder.calls == 4 && recorder.last == 7);
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  if (std::string_view(argv[1]) == "c1") {
    MappingTable table;
    exercise(table);
  } else if (std::string_view(argv[1]) == "c2") {
    BaseConstruction table;
    exercise(table);
  } else {
    return 2;
  }
  MappingTable independent;
  require(!independent.sourcePortItemAt(0) && !independent.findItem("first"));
  exerciseInjected();
  std::cout << argv[1]
            << " empty roster, 1024 slots, typed Item forwarding,"
               " independent instances and injected contracts\n";
}
