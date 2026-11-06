#include "presonus/MappingTable.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <new>
#include <sstream>
#include <string>
#include <vector>
using Item = Presonus::MappingTable::Item;
using Control = Presonus::Panel::Control;
using LED = Presonus::Panel::LEDControl;
using S = presonus::surface_panel_port::LEDStateAccess;
using L = presonus::surface_panel_port::LEDLifecycleAccess;
namespace {
bool tracing = false;
std::vector<std::string> events;
void requireAt(bool yes, int line) {
  if (!yes) {
    std::cerr << "require line " << line << "\n";
    std::abort();
  }
}
#define require(x) requireAt((x), __LINE__)
std::string hex(const char *text) {
  std::ostringstream out;
  for (auto p = reinterpret_cast<const unsigned char *>(text); *p; ++p)
    out << std::hex << std::setw(2) << std::setfill('0') << unsigned(*p);
  return out.str();
}
} // namespace
// Test-only observing overrides delegate every cast to the actual providers.
struct TrackedControl : Control {
  using Control::Control;
  void *castTo(int tag) override {
    if (tracing) {
      require(tag == 1281713219);
      events.push_back("cast");
    }
    return Control::castTo(tag);
  }
};
struct TrackedLED : LED {
  using LED::LED;
  void *castTo(int tag) override {
    if (tracing) {
      require(tag == 1281713219);
      events.push_back("cast");
    }
    return LED::castTo(tag);
  }
};
extern "C" void
__real__ZN8Presonus5Panel10LEDControl12setBlinkModeENS1_9BlinkModeE(
    LED *, LED::BlinkMode);
extern "C" void
__wrap__ZN8Presonus5Panel10LEDControl12setBlinkModeENS1_9BlinkModeE(
    LED *p, LED::BlinkMode mode) {
  if (tracing)
    events.push_back("blink:" + std::to_string(int(mode)));
  __real__ZN8Presonus5Panel10LEDControl12setBlinkModeENS1_9BlinkModeE(p, mode);
}
extern "C" void __real__ZN8Presonus5Panel10LEDControl14setInverseModeEb(LED *,
                                                                        bool);
extern "C" void
__wrap__ZN8Presonus5Panel10LEDControl14setInverseModeEb(LED *p, bool value) {
  if (tracing)
    events.push_back("inverse:" + std::to_string(value));
  __real__ZN8Presonus5Panel10LEDControl14setInverseModeEb(p, value);
}
extern "C" void ctor1(Item *, const char *, Core::Portable::AliasParam *) asm(
    "_ZN8Presonus12MappingTable4ItemC1EPKcPN4Core8Portable10AliasParamE");
extern "C" void ctor2(Item *, const char *, Core::Portable::AliasParam *) asm(
    "_ZN8Presonus12MappingTable4ItemC2EPKcPN4Core8Portable10AliasParamE");
int main() {
  std::string op, text, expectedTrace;
  int nullText, control, arg, dispatch, initial;
  unsigned cases = 0;
  while (std::cin >> op >> nullText >> std::quoted(text) >> control >> arg >>
         dispatch >> initial >> std::quoted(expectedTrace)) {
    const char *input = nullText ? nullptr : text.c_str();
    Core::Portable::ParamInfo info{};
    Core::Portable::AliasParam alias(info);
    if (op == "C1" || op == "C2") {
      alignas(Item) unsigned char storage[sizeof(Item)];
      auto *item = reinterpret_cast<Item *>(storage);
      (op == "C1" ? ctor1 : ctor2)(item, input, arg ? &alias : nullptr);
      Core::CStringBuffer<32> providerName(input), providerDefault(nullptr);
      require(hex(item->name.str()) == hex(providerName.str()));
      require(hex(item->defaultColor.str()) == hex(providerDefault.str()));
      require(item->alias == (arg ? &alias : nullptr) &&
              item->control == nullptr);
      item->~Item();
    } else {
      TrackedControl other(1);
      TrackedLED actual(1, 2, -1);
      LED expected(1, 2, -1);
      S::setState(actual, nullptr,
                  {123, 17, 0, 0, static_cast<unsigned>(initial)});
      S::setState(expected, nullptr,
                  {123, 17, 0, 0, static_cast<unsigned>(initial)});
      if (dispatch >= 0) {
        if (op == "B")
          expected.setBlinkMode(static_cast<LED::BlinkMode>(dispatch));
        else
          expected.setInverseMode(dispatch != 0);
      }
      Item item(&alias, control == 2   ? static_cast<Control *>(&actual)
                        : control == 1 ? &other
                                       : nullptr);
      events.clear();
      tracing = true;
      if (op == "B")
        item.setBlinkMode(input);
      else
        item.setInverseMode(arg != 0);
      tracing = false;
      std::string trace;
      for (auto &e : events)
        trace += e + ";";
      require(trace == expectedTrace);
      require(S::state(actual) == S::state(expected));
      require(L::on(actual) == L::on(expected) &&
              L::off(actual) == L::off(expected));
      require(item.alias == &alias);
    }
    ++cases;
  }
  require(std::cin.eof());
  std::cout << "PASS " << cases
            << " ARM-directed cases with actual Control/LED and CCL state\n";
}
