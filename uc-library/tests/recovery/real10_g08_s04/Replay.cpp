#include "presonus/panel/FrontPanelComponent.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace Core::Portable;
struct Unused final : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
static float f(const char *p) {
  auto bits = static_cast<std::uint32_t>(std::strtoul(p, nullptr, 16));
  float v;
  std::memcpy(&v, &bits, 4);
  return v;
}
int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  const ParamInfo infos[] = {
      PARAM_FLOAT(36, "lock", -100, 100, 0, 1, "", nullptr, 0, 0),
      PARAM_FLOAT(38, "fader", -100, 100, 0, 1, "", nullptr, 0, 0)};
  Component settings("first"), other("second");
  const bool has36 = std::atoi(argv[1]), has38 = std::atoi(argv[2]);
  if (has36)
    settings.addParameters(infos, 1);
  if (has38)
    settings.addParameters(infos + 1, 1);
  other.addParameters(infos, 2);
  auto value = [&](int tag, float v) {
    if (auto *p = NumericParam::cast(settings.getParameterByTag(tag)))
      p->setValueFast(v);
  };
  value(36, f(argv[3]));
  value(38, f(argv[4]));
  Unused deps;
  presonus::frontpanel_port::State s(settings), t(other);
  Presonus::Panel::FrontPanelComponent first(s, deps), second(t, deps);
  bool a = first.fadersLocked();
  value(36, f(argv[5]));
  value(38, f(argv[6]));
  bool b = second.fadersLocked();
  std::printf("[%s,%s]\n", a ? "true" : "false", b ? "true" : "false");
}
