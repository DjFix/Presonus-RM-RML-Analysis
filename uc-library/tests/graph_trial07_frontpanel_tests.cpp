#include "presonus/panel/FrontPanelComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
using namespace Core::Portable;
using namespace presonus::frontpanel_port;
static std::uint32_t bits(float f) {
  std::uint32_t b;
  std::memcpy(&b, &f, 4);
  return b;
}
static float number(std::uint32_t b) {
  float f;
  std::memcpy(&f, &b, 4);
  return f;
}
static bool recording = false;
struct TracedParam : NumericParam {
  TracedParam(int tag, float v)
      : NumericParam(*new ParamInfo PARAM_FLOAT(tag, "fixture", -100, 100, v,
                                                0.01f, nullptr, nullptr, 0,
                                                PARAM_MUTABLE),
                     true) {}
  float getValue() const override {
    if (recording)
      std::cout << "@G " << getTag() << ' ' << bits(value) << '\n';
    return NumericParam::getValue();
  }
  void setMin(float v) override {
    if (recording)
      std::cout << "@N " << getTag() << ' ' << bits(v) << '\n';
    NumericParam::setMin(v);
  }
  void setMax(float v) override {
    if (recording)
      std::cout << "@M " << getTag() << ' ' << bits(v) << '\n';
    NumericParam::setMax(v);
  }
  void setValue(float v, bool edit = false) override {
    if (recording)
      std::cout << "@V " << getTag() << ' ' << bits(v) << ' ' << edit << '\n';
    NumericParam::setValue(v, edit);
  }
  float raw() const { return value; }
};
struct Settings : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct Services : Dependencies {
  bool longEnough = false, faders = false;
  std::string page;
  bool pageExists = true;
  void perform(Action a, int b = 0, int c = 0) override {
    std::cout << "@E " << static_cast<int>(a) << ' ' << b << ' ' << c << '\n';
  }
  bool timerLongEnough() const override {
    std::cout << "@T " << longEnough << '\n';
    return longEnough;
  }
  bool fadersLocked() const override {
    std::cout << "@F " << faders << '\n';
    return faders;
  }
  const char *activePageName() const override {
    std::cout << "@A " << pageExists << '\n';
    return pageExists ? page.c_str() : nullptr;
  }
  void paste(void *ch, const void *context, const char *flag) override {
    std::cout << "@X " << reinterpret_cast<std::uintptr_t>(ch) << ' '
              << (context != nullptr) << ' ' << flag << '\n';
  }
};
int main() {
  int held, active, longEnough, faders, pageExists;
  std::string page;
  int n;
  if (!(std::cin >> held >> active >> longEnough >> faders >> pageExists >>
        page >> n))
    return 2;
  Settings settings;
  std::vector<TracedParam *> params;
  for (int i = 0; i < n; ++i) {
    int tag;
    std::uint32_t b;
    std::cin >> tag >> b;
    auto *p = new TracedParam(tag, number(b));
    settings.add(p);
    params.push_back(p);
  }
  State state(settings);
  state.heldButton = held;
  state.copyActive = active;
  state.copyContext = &state;
  std::vector<std::unique_ptr<TracedParam>> selections;
  std::cin >> n;
  for (int i = 0; i < n; ++i) {
    std::uint32_t b;
    std::cin >> b;
    auto p = std::make_unique<TracedParam>(100 + i, number(b));
    state.pasteSelections.add(p.get());
    selections.push_back(std::move(p));
  }
  std::cin >> n;
  for (int i = 0; i < n; ++i) {
    int present;
    std::cin >> present;
    state.channels.add(
        present ? reinterpret_cast<void *>(static_cast<std::uintptr_t>(i + 1))
                : nullptr);
  }
  Services services;
  services.longEnough = longEnough;
  services.faders = faders;
  services.pageExists = pageExists;
  services.page = page;
  Presonus::Panel::FrontPanelComponent panel(state, services);
  recording = true;
  std::cin >> n;
  for (int i = 0; i < n; ++i) {
    int op, a, b;
    std::cin >> op >> a >> b;
    switch (op) {
    case 1:
      panel.handlePaste();
      break;
    case 2:
      panel.enterPassCodeDigit(a);
      break;
    case 3:
      panel.updateMixerLocks();
      break;
    case 4: {
      bool result = panel.mastersLocked();
      std::cout << "@R " << result << '\n';
    } break;
    case 5:
      panel.buttonReleased(a, b);
      break;
    case 6:
      panel.checkPassCodeEntry(a);
      break;
    case 7:
      panel.lockFaders(a);
      break;
    case 8:
      panel.activateAll();
      break;
    case 9: {
      bool result = panel.mixerLocked();
      std::cout << "@R " << result << '\n';
    } break;
    case 10:
      panel.lockStateChanged();
      break;
    default:
      return 3;
    }
  }
  recording = false;
  std::cout << "@H " << state.heldButton << '\n';
  for (auto *p : params)
    std::cout << "@P " << p->getTag() << ' ' << bits(p->raw()) << ' '
              << bits(p->getMin()) << ' ' << bits(p->getMax()) << '\n';
}
