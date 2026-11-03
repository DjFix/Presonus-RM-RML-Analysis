#include "presonus/MackieControlModel.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/frontier01/frontier01_w04.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
#include <iostream>
#include <memory>
#include <string>
#include <vector>
// Test-only opaque Item boundary: no production Item implementation or layout.
namespace Presonus {
class MappingTable::Item {};
} // namespace Presonus
namespace {
const char *names[]{"", "alpha", "beta", "gamma", "delta"};
using State = presonus::surface::midi_port::State;
using Record = std::array<unsigned char, 44>;
struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override { throw 1; }
  bool recordParameterPresent() override { throw 1; }
  float recordParameterValue() override { throw 1; }
  void updateRecordMapping(bool) override { throw 1; }
  bool idleSlotPresent(unsigned) override { throw 1; }
  void invokeIdleSlot(unsigned) override { throw 1; }
};
struct Operations : presonus::mapping::ItemOperations {
  State &state;
  Presonus::MappingTable::Item items[4];
  const Record *replacement;
  bool mutate;
  std::vector<int> trace;
  explicit Operations(State &s, const Record *r, bool m)
      : state(s), replacement(r), mutate(m) {}
  void fullOff(Presonus::MappingTable::Item &) override { throw 1; }
  void inverseMode(Presonus::MappingTable::Item &, bool) override { throw 1; }
  void immediate(Presonus::MappingTable::Item &, bool) override { throw 1; }
  void enabled(Presonus::MappingTable::Item &item, bool value) override {
    trace.push_back(static_cast<int>(&item - items) + 1);
    trace.push_back(value);
    if (mutate && trace.size() == 2)
      state.controlDescriptions = replacement;
  }
};
std::vector<int> destroyed;
int childNext = 0, freed = 0;
struct Child : Core::Portable::Component {
  int id = ++childNext;
  ~Child() override { destroyed.push_back(id); }
  static void operator delete(void *p) noexcept {
    ++freed;
    ::operator delete(p);
  }
};
template <class T> void lifecycle(int count) {
  destroyed.clear();
  childNext = freed = 0;
  {
    T parent;
    if (count & 1)
      parent.addChild(new Child);
    if (count & 2)
      parent.addChildren(new Core::Portable::TComponentArray<Child>(2));
    if (count & 4)
      parent.addChild(new Child);
  }
  for (int id : destroyed)
    std::cout << id << ' ';
  std::cout << -1 << ' ' << freed << '\n';
}
} // namespace
int main() {
  char mode;
  while (std::cin >> mode) {
    if (mode == 'M') {
      int accepted, value;
      std::cin >> accepted;
      Presonus::MackieControlModel model;
      for (auto &v : model.hostConnectionIdentity) {
        std::cin >> value;
        v = value;
      }
      unsigned calls = 0;
      model.midiSink = [&](const unsigned char *data, unsigned size,
                           unsigned flags) {
        if (flags != 0 || size != 14)
          throw 1;
        ++calls;
        for (unsigned i = 0; i < size; ++i)
          std::cout << unsigned(data[i]) << ' ';
      };
      model.sendHostConnectionConfirmation(accepted);
      if (calls != 1)
        return 3;
      std::cout << '\n';
    } else if (mode == 'C') {
      int enabled, mutate, count;
      std::cin >> enabled >> mutate >> count;
      std::vector<Record> rows(count + 1), replacement(5);
      auto set = [](Record &r, int name, int eligible) {
        std::copy(names[name],
                  names[name] + std::char_traits<char>::length(names[name]),
                  r.begin());
        r[37] = eligible;
      };
      for (int i = 0; i < count; ++i) {
        int name, eligible;
        std::cin >> name >> eligible;
        set(rows[i], name, eligible);
      }
      set(replacement[0], 4, 1);
      set(replacement[1], 3, 255);
      set(replacement[2], 2, 0);
      set(replacement[3], 1, 1);
      State state;
      state.controlDescriptions = rows.data();
      Operations operations(state, replacement.data(), mutate);
      presonus::mapping::Entry entries[]{{"alpha", &operations.items[0]},
                                         {"beta", &operations.items[1]},
                                         {"delta", &operations.items[3]},
                                         {"gamma", &operations.items[2]}};
      Presonus::MappingTable table(entries, 4, operations);
      state.mappingTable = &table;
      Services services;
      Presonus::Surface::MidiMixerHandler handler(state, services);
      handler.setControlsEnabled(enabled);
      for (int v : operations.trace)
        std::cout << v << ' ';
      std::cout << '\n';
    } else if (mode == 'D') {
      int target, count;
      std::cin >> target >> count;
      switch (target) {
      case 0:
        lifecycle<Core::Portable::Component>(count);
        break;
      case 3:
        lifecycle<Presonus::Surface::AudioUtilitiesPage>(count);
        break;
      case 4:
        lifecycle<Presonus::Surface::StartPageComponent>(count);
        break;
      case 5:
        lifecycle<Presonus::MackieControlExtender>(count);
        break;
      case 6:
        lifecycle<Presonus::FaderUnitComponent>(count);
        break;
      case 7:
        lifecycle<Presonus::MackieControlComponent>(count);
        break;
      case 8:
        lifecycle<Presonus::Surface::FaderUtilitiesPage>(count);
        break;
      default:
        return 4;
      }
    } else
      return 5;
  }
}
