#include "presonus/GridPainter.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/PanelComponent.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>

struct Items final : presonus::mapping::ItemOperations {
  void fullOff(Presonus::MappingTable::Item &) override { throw 1; }
  void inverseMode(Presonus::MappingTable::Item &, bool) override { throw 1; }
  void enabled(Presonus::MappingTable::Item &, bool) override { throw 1; }
  void immediate(Presonus::MappingTable::Item &, bool) override { throw 1; }
};
// Test-only explicit boundary: every untested operation fails if reached.
struct Extended final : presonus::mapping::ExtendedOperations {
  std::uintptr_t result = 0;
  int calls = 0;
  void blink(Presonus::MappingTable::Item &, const char *) override { throw 1; }
  const char *pageName(Presonus::IMainScreenPageController &) override {
    throw 1;
  }
  Presonus::Panel::Control *control(Presonus::MappingTable::Item &) override {
    throw 1;
  }
  void control(Presonus::MappingTable::Item &,
               Presonus::Panel::Control *) override {
    throw 1;
  }
  Core::Portable::Parameter *
  parameter(Presonus::MappingTable::Item &) override {
    ++calls;
    return reinterpret_cast<Core::Portable::Parameter *>(result);
  }
  int translateMode(const char *) override { throw 1; }
  void bind(Presonus::Panel::Control &, Core::Portable::Parameter *,
            int) override {
    throw 1;
  }
  Core::Portable::Parameter *alternate(Presonus::Panel::Control &,
                                       bool) override {
    throw 1;
  }
  void alternate(Presonus::Panel::Control &, Core::Portable::Parameter *,
                 bool) override {
    throw 1;
  }
  bool hasLED(Presonus::Panel::Control &) override { throw 1; }
  void color(Presonus::Panel::Control &, int) override { throw 1; }
  const char *defaultColor(Presonus::MappingTable::Item &) override { throw 1; }
  void defaultColor(Presonus::MappingTable::Item &, const char *) override {
    throw 1;
  }
};
struct Panel final : presonus::panel_port::Services {
  int groupCount() const override { throw 1; }
  const Presonus::Panel::ControlGroup &groupAt(int) const override { throw 1; }
  std::uint32_t groupTag(const Presonus::Panel::ControlGroup &) const override {
    throw 1;
  }
  int controlCount(const Presonus::Panel::ControlGroup &) const override {
    throw 1;
  }
  void *controlAt(const Presonus::Panel::ControlGroup &, int) const override {
    throw 1;
  }
  void controlSlot10(void *, int, int) const override { throw 1; }
  void componentSlot38() override { throw 1; }
  void *findGroup(int) override { throw 1; }
  void *byTag(void *, int) override { throw 1; }
  void *castControlToLed(void *) override { throw 1; }
  void setBlinkMode(void *, int) override { throw 1; }
};
int main(int argc, char **argv) {
  if (argc != 4 && argc != 5)
    return 2;
  int target = std::atoi(argv[1]);
  if (target == 9) {
    if (argc != 5)
      return 2;
    Core::FormatterRegistry::add(
        const_cast<Core::Formatter *>(&Core::IntFormatter::instance()));
    presonus::grid_port::AxisState first{17, nullptr}, second{19, nullptr};
    Presonus::GridPainter painter(first, second);
    auto axis = std::atoi(argv[2]);
    auto orientation = std::atoi(argv[3]);
    painter.setGridOrientation(
        static_cast<Presonus::GridPainter::Axis>(axis),
        static_cast<Presonus::GridPainter::LabelOrientation>(orientation),
        argv[4]);
    auto &chosen = axis == 0 ? first : second;
    auto &other = axis == 0 ? second : first;
    std::printf("RESULT %d %d %d %d\n", chosen.orientation,
                chosen.formatter != nullptr, other.orientation,
                other.formatter != nullptr);
  } else if (target == 10) {
    Items items;
    Extended extended;
    extended.result = std::strtoull(argv[3], nullptr, 10);
    // Opaque identity only; no object dereference or layout assumption.
    auto *item = reinterpret_cast<Presonus::MappingTable::Item *>(
        std::uintptr_t(0x1234));
    presonus::mapping::Entry entry{"hit", item};
    Presonus::MappingTable table(&entry, 1, items);
    table.setExtendedOperations(extended);
    auto *result =
        table.getHardwareParameter(std::atoi(argv[2]) ? "hit" : "miss");
    std::printf("RESULT %llu %d\n",
                static_cast<unsigned long long>(
                    reinterpret_cast<std::uintptr_t>(result)),
                extended.calls);
  } else if (target == 15) {
    Panel services;
    Presonus::Panel::PanelComponent panel(services);
    char *args[] = {argv[0], nullptr};
    std::printf("RESULT %d\n",
                panel.runTests(std::atoi(argv[2]), std::atoi(argv[3]), args));
  } else
    return 3;
}
