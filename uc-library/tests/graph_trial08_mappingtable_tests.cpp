#include "presonus/MappingTable.hpp"
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
namespace {
std::vector<std::string> trace;
void event(const std::string &s) { trace.push_back(s); }
std::string str(const char *s) { return s ? s : "NULL"; }
struct Old : presonus::mapping::ItemOperations {
  void fullOff(Presonus::MappingTable::Item &) override {}
  void inverseMode(Presonus::MappingTable::Item &, bool) override {}
  void enabled(Presonus::MappingTable::Item &, bool) override {}
  void immediate(Presonus::MappingTable::Item &, bool) override {}
};
struct Colors : presonus::mapping::ColorOperations {
  int map(Core::Color c) override {
    event("maprgb:" +
          std::to_string(unsigned(c.red) | (unsigned(c.green) << 8) |
                         (unsigned(c.blue) << 16) | (unsigned(c.alpha) << 24)));
    return 7;
  }
  Core::Color map(const char *s) override {
    event("mapstr:" + str(s));
    return {17, 34, 51, 68};
  }
  int enumFromString(const char *s, int fallback) override {
    event("enum:" + str(s) + ":" + std::to_string(fallback));
    return 9;
  }
};
struct Ops : presonus::mapping::ExtendedOperations {
  int v;
  std::string value = "blue";
  Presonus::Panel::Control *ctrl = nullptr;
  Core::Portable::ParamInfo info = PARAM_ALIAS(1, "alias", 0);
  Core::Portable::AliasParam alias{info};
  Core::Portable::NumericParam target{info};
  explicit Ops(int variant) : v(variant) {
    if (v >= 2)
      ctrl = reinterpret_cast<Presonus::Panel::Control *>(0x100);
  }
  void blink(Presonus::MappingTable::Item &, const char *s) override {
    event("blink:" + str(s));
  }
  const char *pageName(Presonus::IMainScreenPageController &p) override {
    int i = reinterpret_cast<std::uintptr_t>(&p);
    event("page:" + std::to_string(i));
    return i == 1 ? "one" : "two";
  }
  Presonus::Panel::Control *control(Presonus::MappingTable::Item &) override {
    return ctrl;
  }
  void control(Presonus::MappingTable::Item &,
               Presonus::Panel::Control *p) override {
    ctrl = p;
  }
  Core::Portable::Parameter *
  parameter(Presonus::MappingTable::Item &) override {
    return nullptr;
  }
  int translateMode(const char *s) override {
    event("translate:" + str(s));
    return 3;
  }
  void bind(Presonus::Panel::Control &, Core::Portable::Parameter *,
            int mode) override {
    event("bind:" + std::to_string(mode));
  }
  Core::Portable::Parameter *alternate(Presonus::Panel::Control &,
                                       bool tertiary) override {
    event(tertiary ? "getter:1" : "getter:0");
    return v == 3 ? &alias : nullptr;
  }
  void alternate(Presonus::Panel::Control &, Core::Portable::Parameter *,
                 bool tertiary) override {
    event(tertiary ? "setter:1" : "setter:0");
  }
  bool hasLED(Presonus::Panel::Control &) override {
    event("ledcast");
    return v == 3;
  }
  void color(Presonus::Panel::Control &, int c) override {
    event("color:" + std::to_string(c));
  }
  const char *defaultColor(Presonus::MappingTable::Item &) override {
    return value.c_str();
  }
  void defaultColor(Presonus::MappingTable::Item &, const char *s) override {
    value = s;
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  int n = std::stoi(argv[1]), v = std::stoi(argv[2]);
  Old old;
  Colors colors;
  Ops ops(v);
  alignas(8) char token[8]{};
  auto *item = reinterpret_cast<Presonus::MappingTable::Item *>(token);
  presonus::mapping::Entry entry{"hit", item};
  Presonus::MappingTable table(&entry, 1, old);
  table.setExtendedOperations(ops);
  table.setColorOperations(colors);
  const char *name = v ? "hit" : "miss";
  int ret = 0, count = 0;
  switch (n) {
  case 1:
    table.setControlBlinkMode(name, v == 3 ? nullptr : "fast");
    break;
  case 2:
    ret = table.mapColor(Core::Color{1, 2, 3, 4});
    break;
  case 3:
    count = v == 0 ? 0 : v == 1 ? 127 : 128;
    for (int i = 0; i < count; ++i)
      table.addMainScreenPage(
          reinterpret_cast<Presonus::IMainScreenPageController *>(1));
    table.addMainScreenPage(
        reinterpret_cast<Presonus::IMainScreenPageController *>(2));
    count = table.sourcePortPageCount();
    break;
  case 4:
    table.setPanelControl(
        name, reinterpret_cast<Presonus::Panel::Control *>(0x100), "mode");
    break;
  case 5: {
    auto c = table.mapColor(v == 0 ? nullptr : "red");
    ret = c.red | (c.green << 8) | (c.blue << 16) | (c.alpha << 24);
    break;
  }
  case 6:
    table.connectAltParameter(name, v == 3 ? &ops.target : nullptr);
    break;
  case 7:
    table.connectTertiaryParameter(name, v == 3 ? &ops.target : nullptr);
    break;
  case 8:
    if (v) {
      table.addMainScreenPage(
          reinterpret_cast<Presonus::IMainScreenPageController *>(1));
      if (v >= 2)
        table.addMainScreenPage(
            reinterpret_cast<Presonus::IMainScreenPageController *>(2));
    }
    ret = reinterpret_cast<std::uintptr_t>(table.findPage(v == 1   ? "one"
                                                          : v == 3 ? "two"
                                                                   : "absent"));
    break;
  case 9:
    table.setControlColor(name, v == 3 ? "default" : nullptr);
    break;
  case 10:
    table.setControlDefaultColor(name,
                                 v == 1 ? nullptr
                                 : v == 3
                                     ? "abcdefghijklmnopqrstuvwxyz0123456789"
                                     : "red",
                                 v == 3);
    break;
  default:
    return 3;
  }
  // Real CCL AliasParam retargeting is observed through getOriginal.
  if ((n == 6 || n == 7) && v == 3) {
    if (ops.alias.getOriginal() != &ops.target)
      return 4;
    event("alias:1");
  }
  std::cout << ret << '|' << count << '|' << ops.value << '|'
            << (ops.ctrl ? 1 : 0) << '|';
  for (std::size_t i = 0; i < trace.size(); ++i) {
    if (i)
      std::cout << ';';
    std::cout << trace[i];
  }
  std::cout << '\n';
}
